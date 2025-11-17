"""
Samsung device-specific support
Beyond Odin's basic flashing capabilities

Author: SamFWTool Team
License: MIT
"""
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "SamsungDevice",
    "SamsungFirmwareParser",
]


class SamsungDevice:
    """
    Samsung device-specific functionality

    Handles Samsung-specific firmware formats and features
    """

    # Common Samsung partition names
    SAMSUNG_PARTITIONS = {
        'BL': 'bootloader',
        'AP': 'system',
        'CP': 'modem',
        'CSC': 'customer_software_customization',
        'HOME_CSC': 'home_csc',
        'USERDATA': 'userdata',
    }

    # Samsung device models
    DEVICE_MODELS = {
        'SM-G': 'Galaxy S Series',
        'SM-N': 'Galaxy Note Series',
        'SM-A': 'Galaxy A Series',
        'SM-M': 'Galaxy M Series',
        'SM-F': 'Galaxy Fold Series',
        'SM-Z': 'Galaxy Z Series',
    }

    def __init__(self, model: str):
        self.model = model
        self.series = self._detect_series()

    def _detect_series(self) -> str:
        """Detect device series from model number"""
        for prefix, series in self.DEVICE_MODELS.items():
            if self.model.startswith(prefix):
                return series
        return "Unknown Series"

    def get_partition_info(self, partition_name: str) -> Dict:
        """Get Samsung-specific partition information"""
        full_name = self.SAMSUNG_PARTITIONS.get(partition_name, partition_name)

        return {
            'short_name': partition_name,
            'full_name': full_name,
            'critical': partition_name in ['BL', 'AP'],
            'description': self._get_partition_description(partition_name)
        }

    def _get_partition_description(self, partition_name: str) -> str:
        """Get partition description"""
        descriptions = {
            'BL': 'Bootloader - Contains device bootloader and firmware',
            'AP': 'Application Processor - Contains Android system, kernel, and recovery',
            'CP': 'Communication Processor - Contains modem firmware for cellular connectivity',
            'CSC': 'Consumer Software Customization - Contains region-specific settings and apps',
            'HOME_CSC': 'Home CSC - CSC without user data wipe',
            'USERDATA': 'User data partition',
        }
        return descriptions.get(partition_name, 'Unknown partition')

    def validate_firmware_structure(self, firmware_files: List[str]) -> Dict:
        """
        Validate Samsung firmware structure

        Returns validation result with warnings/errors
        """
        required_partitions = ['BL', 'AP', 'CP', 'CSC']
        found_partitions = []
        warnings = []
        errors = []

        for filename in firmware_files:
            for partition in required_partitions:
                if partition.lower() in filename.lower():
                    found_partitions.append(partition)
                    break

        # Check for missing critical partitions
        missing = set(required_partitions) - set(found_partitions)
        if missing:
            errors.append(f"Missing critical partitions: {', '.join(missing)}")

        # Check for HOME_CSC vs CSC
        has_csc = any('CSC' in f for f in firmware_files)
        has_home_csc = any('HOME_CSC' in f for f in firmware_files)

        if has_csc and not has_home_csc:
            warnings.append("Using CSC will wipe user data. Consider HOME_CSC to preserve data.")

        return {
            'valid': len(errors) == 0,
            'found_partitions': found_partitions,
            'warnings': warnings,
            'errors': errors
        }

    def get_recommended_flash_order(self) -> List[str]:
        """Get recommended order for flashing partitions"""
        return ['BL', 'AP', 'CP', 'CSC']

    @staticmethod
    def parse_firmware_filename(filename: str) -> Dict:
        """
        Parse Samsung firmware filename

        Format: SM-G991B_1_20230101120000_abcdefg_fac.tar.md5
        """
        parts = filename.replace('.tar.md5', '').replace('.tar', '').split('_')

        info = {
            'model': parts[0] if len(parts) > 0 else 'unknown',
            'region': parts[1] if len(parts) > 1 else 'unknown',
            'build_date': parts[2] if len(parts) > 2 else 'unknown',
            'changelist': parts[3] if len(parts) > 3 else 'unknown',
            'type': parts[4] if len(parts) > 4 else 'unknown',
        }

        return info
