"""
Device detection and management

Author: SamFWTool Team
License: MIT
"""
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DeviceMode",
    "DeviceVendor",
    "Device",
    "DeviceDetector",
]

logger = logging.getLogger(__name__)


class DeviceMode(Enum):
    """Device connection modes"""
    ADB = "adb"
    FASTBOOT = "fastboot"
    DOWNLOAD = "download"  # Samsung Odin mode
    RECOVERY = "recovery"
    EDL = "edl"  # Qualcomm Emergency Download
    UNKNOWN = "unknown"


class DeviceVendor(Enum):
    """Device manufacturers"""
    SAMSUNG = "samsung"
    GOOGLE = "google"
    XIAOMI = "xiaomi"
    ONEPLUS = "oneplus"
    MOTOROLA = "motorola"
    GENERIC = "generic"


@dataclass
class Device:
    """Represents a connected device"""
    serial: str
    vendor: DeviceVendor
    model: str
    mode: DeviceMode
    bootloader_locked: bool
    properties: Dict[str, str]


class DeviceDetector:
    """
    Device detection and identification

    THIS IS THE KEY FEATURE MISSING FROM ODIN - Cross-platform device support
    """

    @staticmethod
    def detect_adb_devices() -> List[Device]:
        """Detect devices in ADB mode"""
        devices = []

        try:
            result = subprocess.run(['adb', 'devices', '-l'],
                                  capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return devices

            for line in result.stdout.split('\n')[1:]:  # Skip header
                if not line.strip() or 'offline' in line:
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                serial = parts[0]
                mode = DeviceMode.ADB

                # Get device properties
                props = DeviceDetector._get_device_properties(serial)

                # Determine vendor
                vendor = DeviceDetector._detect_vendor(props)

                # Get model
                model = props.get('ro.product.model', 'Unknown')

                # Check bootloader status
                bootloader_locked = props.get('ro.boot.verifiedbootstate', '') != 'orange'

                device = Device(
                    serial=serial,
                    vendor=vendor,
                    model=model,
                    mode=mode,
                    bootloader_locked=bootloader_locked,
                    properties=props
                )
                devices.append(device)

        except FileNotFoundError:
            print("⚠️  ADB not found in PATH")
        except Exception as e:
            print(f"⚠️  Error detecting ADB devices: {e}")

        return devices

    @staticmethod
    def detect_fastboot_devices() -> List[Device]:
        """Detect devices in Fastboot mode"""
        devices = []

        try:
            result = subprocess.run(['fastboot', 'devices'],
                                  capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return devices

            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                serial = parts[0]

                # Get fastboot variables
                props = DeviceDetector._get_fastboot_vars(serial)

                vendor = DeviceDetector._detect_vendor(props)
                model = props.get('product', 'Unknown')
                bootloader_locked = props.get('unlocked', 'no') == 'no'

                device = Device(
                    serial=serial,
                    vendor=vendor,
                    model=model,
                    mode=DeviceMode.FASTBOOT,
                    bootloader_locked=bootloader_locked,
                    properties=props
                )
                devices.append(device)

        except FileNotFoundError:
            print("⚠️  Fastboot not found in PATH")
        except Exception as e:
            print(f"⚠️  Error detecting Fastboot devices: {e}")

        return devices

    @staticmethod
    def detect_samsung_download_mode() -> List[Device]:
        """
        Detect Samsung devices in Download mode (Odin mode)

        This would use heimdall or custom USB protocol implementation
        """
        devices = []

        try:
            # Try using heimdall
            result = subprocess.run(['heimdall', 'detect'],
                                  capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and 'Device detected' in result.stdout:
                # Samsung device in download mode detected
                device = Device(
                    serial='heimdall-device',
                    vendor=DeviceVendor.SAMSUNG,
                    model='Unknown Samsung',
                    mode=DeviceMode.DOWNLOAD,
                    bootloader_locked=True,  # Assume locked
                    properties={}
                )
                devices.append(device)

        except FileNotFoundError:
            print("ℹ️  Heimdall not found (Samsung Download mode support)")
        except Exception as e:
            print(f"⚠️  Error detecting Samsung Download mode: {e}")

        return devices

    @staticmethod
    def detect_all() -> List[Device]:
        """Detect all connected devices in any mode"""
        all_devices = []

        all_devices.extend(DeviceDetector.detect_adb_devices())
        all_devices.extend(DeviceDetector.detect_fastboot_devices())
        all_devices.extend(DeviceDetector.detect_samsung_download_mode())

        return all_devices

    @staticmethod
    def _get_device_properties(serial: str) -> Dict[str, str]:
        """Get device properties via ADB"""
        props = {}

        try:
            result = subprocess.run(['adb', '-s', serial, 'shell', 'getprop'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ']:' in line:
                        parts = line.split(']:')
                        if len(parts) == 2:
                            key = parts[0].strip('[').strip()
                            value = parts[1].strip().strip('[]')
                            props[key] = value

        except Exception:
            pass

        return props

    @staticmethod
    def _get_fastboot_vars(serial: str) -> Dict[str, str]:
        """Get fastboot variables"""
        vars = {}

        try:
            result = subprocess.run(['fastboot', '-s', serial, 'getvar', 'all'],
                                  capture_output=True, text=True, timeout=10,
                                  stderr=subprocess.STDOUT)  # fastboot outputs to stderr

            for line in result.stdout.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        vars[key] = value

        except Exception:
            pass

        return vars

    @staticmethod
    def _detect_vendor(props: Dict[str, str]) -> DeviceVendor:
        """Detect device vendor from properties"""
        manufacturer = props.get('ro.product.manufacturer', '').lower()
        brand = props.get('ro.product.brand', '').lower()
        product = props.get('product', '').lower()

        if 'samsung' in manufacturer or 'samsung' in brand:
            return DeviceVendor.SAMSUNG
        elif 'google' in manufacturer or 'google' in brand:
            return DeviceVendor.GOOGLE
        elif 'xiaomi' in manufacturer or 'xiaomi' in brand or 'redmi' in brand:
            return DeviceVendor.XIAOMI
        elif 'oneplus' in manufacturer or 'oneplus' in brand:
            return DeviceVendor.ONEPLUS
        elif 'motorola' in manufacturer or 'motorola' in brand:
            return DeviceVendor.MOTOROLA
        else:
            return DeviceVendor.GENERIC

    @staticmethod
    def print_device_info(device: Device):
        """Print detailed device information"""
        print("\n" + "="*70)
        print("DEVICE INFORMATION")
        print("="*70)
        print(f"Serial: {device.serial}")
        print(f"Vendor: {device.vendor.value}")
        print(f"Model: {device.model}")
        print(f"Mode: {device.mode.value}")
        print(f"Bootloader: {'LOCKED' if device.bootloader_locked else 'UNLOCKED'}")

        if device.properties:
            print(f"\nProperties:")
            for key, value in sorted(device.properties.items())[:10]:
                print(f"  {key}: {value}")
            if len(device.properties) > 10:
                print(f"  ... and {len(device.properties) - 10} more")
