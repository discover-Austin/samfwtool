"""
Device flashing implementation

THIS IS THE KILLER FEATURE - Actual device flashing to replace Odin

Author: SamFWTool Team
License: MIT
"""
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List, Callable
from enum import Enum

from samfwtool.flash.device import Device, DeviceMode, DeviceVendor

__all__ = [
    "FlashResult",
    "DeviceFlasher",
]

logger = logging.getLogger(__name__)


class FlashResult(Enum):
    """Flash operation results"""
    SUCCESS = "success"
    FAILED = "failed"
    DEVICE_NOT_FOUND = "device_not_found"
    BOOTLOADER_LOCKED = "bootloader_locked"
    INVALID_IMAGE = "invalid_image"
    USER_CANCELLED = "user_cancelled"


class DeviceFlasher:
    """
    Universal device flasher

    CRITICAL FEATURE: This is what Odin does, but cross-platform and multi-vendor
    """

    def __init__(self, device: Device, safety_checks: bool = True,
                 confirm_callback: Optional[Callable[[str], bool]] = None):
        """
        Initialize device flasher

        Args:
            device: Device to flash
            safety_checks: Enable safety confirmations
            confirm_callback: Callback function for user confirmations (msg) -> bool
                            If None and safety_checks=True, operations will fail
        """
        self.device = device
        self.safety_checks = safety_checks
        self.confirm_callback = confirm_callback
        self.progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates"""
        self.progress_callback = callback

    def flash_partition(self, partition_name: str, image_path: Path) -> FlashResult:
        """
        Flash a single partition

        Args:
            partition_name: Name of partition (boot, system, vendor, etc.)
            image_path: Path to partition image

        Returns:
            Flash result
        """
        if not image_path.exists():
            logger.error(f"Image not found: {image_path}")
            return FlashResult.INVALID_IMAGE

        if self.safety_checks and self.device.bootloader_locked:
            logger.error("Bootloader is LOCKED. Unlock bootloader before flashing.")
            return FlashResult.BOOTLOADER_LOCKED

        logger.info(f"Flashing {partition_name} partition...")
        logger.info(f"Device: {self.device.model} ({self.device.serial})")
        logger.info(f"Image: {image_path}")
        logger.info(f"Size: {image_path.stat().st_size:,} bytes")

        if self.safety_checks:
            if self.confirm_callback is None:
                logger.error("Safety checks enabled but no confirmation callback provided")
                return FlashResult.USER_CANCELLED

            if not self.confirm_callback(f"Continue flashing {partition_name}?"):
                logger.info("Cancelled by user")
                return FlashResult.USER_CANCELLED

        # Flash based on device mode
        if self.device.mode == DeviceMode.FASTBOOT:
            return self._flash_fastboot(partition_name, image_path)
        elif self.device.mode == DeviceMode.ADB:
            # Need to reboot to bootloader first
            print("📱 Rebooting to bootloader...")
            self._adb_reboot_bootloader()
            time.sleep(5)  # Wait for reboot
            return self._flash_fastboot(partition_name, image_path)
        elif self.device.mode == DeviceMode.DOWNLOAD:
            return self._flash_samsung_download(partition_name, image_path)
        else:
            print(f"❌ Cannot flash in {self.device.mode.value} mode")
            return FlashResult.FAILED

    def flash_full_firmware(self, firmware_path: Path) -> FlashResult:
        """
        Flash complete firmware

        This is the Odin equivalent - flash full TAR.MD5 firmware

        Args:
            firmware_path: Path to firmware file

        Returns:
            Flash result
        """
        logger.warning("FULL FIRMWARE FLASH")
        logger.info(f"Device: {self.device.model}")
        logger.info(f"Firmware: {firmware_path}")

        if self.safety_checks:
            logger.warning("WARNING: This will completely reflash your device!")
            logger.warning("All data will be lost!")

            if self.confirm_callback is None:
                logger.error("Safety checks enabled but no confirmation callback provided")
                return FlashResult.USER_CANCELLED

            if not self.confirm_callback("Type 'I UNDERSTAND' to continue (exact text required)"):
                logger.info("Cancelled")
                return FlashResult.USER_CANCELLED

        # Extract and flash based on vendor
        if self.device.vendor == DeviceVendor.SAMSUNG:
            return self._flash_samsung_firmware(firmware_path)
        else:
            return self._flash_generic_firmware(firmware_path)

    def backup_partition(self, partition_name: str, output_path: Path) -> bool:
        """
        Backup a partition from device

        Args:
            partition_name: Partition to backup
            output_path: Where to save backup

        Returns:
            True if successful
        """
        print(f"\n💾 Backing up {partition_name} partition...")

        if self.device.mode == DeviceMode.ADB:
            return self._backup_adb(partition_name, output_path)
        else:
            print(f"❌ Backup not supported in {self.device.mode.value} mode")
            return False

    def _flash_fastboot(self, partition: str, image: Path) -> FlashResult:
        """Flash via fastboot"""
        try:
            cmd = ['fastboot', '-s', self.device.serial, 'flash', partition, str(image)]
            print(f"   Executing: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"✅ Successfully flashed {partition}")
                return FlashResult.SUCCESS
            else:
                print(f"❌ Flash failed: {result.stderr}")
                return FlashResult.FAILED

        except subprocess.TimeoutExpired:
            print("❌ Flash operation timed out")
            return FlashResult.FAILED
        except Exception as e:
            print(f"❌ Error: {e}")
            return FlashResult.FAILED

    def _flash_samsung_download(self, partition: str, image: Path) -> FlashResult:
        """
        Flash Samsung device in Download mode using Heimdall

        This replicates Odin functionality on Linux/Mac
        """
        try:
            # Heimdall partition name mapping
            partition_map = {
                'boot': 'BOOT',
                'recovery': 'RECOVERY',
                'system': 'SYSTEM',
                'cache': 'CACHE',
                'userdata': 'USERDATA',
                'modem': 'MODEM',
                'bootloader': 'BOOTLOADER',
            }

            heimdall_partition = partition_map.get(partition, partition.upper())

            cmd = ['heimdall', 'flash', f'--{heimdall_partition}', str(image)]
            print(f"   Executing: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"✅ Successfully flashed {partition}")
                return FlashResult.SUCCESS
            else:
                print(f"❌ Flash failed: {result.stderr}")
                return FlashResult.FAILED

        except FileNotFoundError:
            print("❌ Heimdall not found. Install heimdall for Samsung flashing.")
            return FlashResult.FAILED
        except Exception as e:
            print(f"❌ Error: {e}")
            return FlashResult.FAILED

    def _flash_samsung_firmware(self, firmware_path: Path) -> FlashResult:
        """
        Flash complete Samsung firmware (TAR.MD5)

        This is the FULL Odin replacement
        """
        print("   Using Heimdall to flash Samsung firmware...")

        try:
            # For full firmware, heimdall can flash the entire TAR
            cmd = ['heimdall', 'flash', '--pit', 'auto', '--TAR', str(firmware_path)]
            print(f"   Executing: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print(f"✅ Firmware flash complete!")
                return FlashResult.SUCCESS
            else:
                print(f"❌ Flash failed: {result.stderr}")
                return FlashResult.FAILED

        except FileNotFoundError:
            print("❌ Heimdall required for Samsung firmware flashing")
            print("   Install: https://github.com/Benjamin-Dobell/Heimdall")
            return FlashResult.FAILED
        except Exception as e:
            print(f"❌ Error: {e}")
            return FlashResult.FAILED

    def _flash_generic_firmware(self, firmware_path: Path) -> FlashResult:
        """Flash generic firmware (ZIP format typically)"""
        print("   Flashing generic firmware via fastboot...")

        # This would extract ZIP and flash individual partitions
        # Implementation depends on firmware format
        print("   Generic firmware flashing not yet implemented")
        return FlashResult.FAILED

    def _backup_adb(self, partition: str, output: Path) -> bool:
        """Backup partition via ADB"""
        try:
            # Find partition path
            cmd = ['adb', '-s', self.device.serial, 'shell',
                  f'find /dev/block -name {partition}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0 or not result.stdout.strip():
                print(f"❌ Partition {partition} not found")
                return False

            partition_path = result.stdout.strip().split('\n')[0]
            print(f"   Found: {partition_path}")

            # Pull partition
            cmd = ['adb', '-s', self.device.serial, 'pull', partition_path, str(output)]
            print(f"   Pulling partition...")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print(f"✅ Backup saved: {output}")
                return True
            else:
                print(f"❌ Backup failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def _adb_reboot_bootloader(self):
        """Reboot device to bootloader via ADB"""
        subprocess.run(['adb', '-s', self.device.serial, 'reboot', 'bootloader'],
                      capture_output=True, timeout=10)

    def get_safety_warnings(self, partition: str) -> List[str]:
        """Get safety warnings for flashing a partition"""
        warnings = []

        critical_partitions = ['bootloader', 'aboot', 'sbl1', 'rpm', 'tz']
        if partition.lower() in critical_partitions:
            warnings.append(f"⚠️  {partition} is CRITICAL - brick risk if corrupted!")

        if self.device.bootloader_locked:
            warnings.append("⚠️  Bootloader is LOCKED - flashing will fail!")

        return warnings
