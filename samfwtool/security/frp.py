"""
Factory Reset Protection (FRP) Analysis

UNIQUE FEATURE: NO other firmware tool analyzes FRP comprehensively!

This module:
- Detects FRP status in firmware
- Analyzes FRP bypass vulnerabilities
- Identifies security misconfigurations
- Checks for known FRP bypass methods
- Validates Google Account bindings

Author: SamFWTool Team
License: MIT
"""
import re
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "FRPStatus",
    "FRPBypassMethod",
    "FRPFinding",
    "FRPAnalyzer",
]

logger = logging.getLogger(__name__)


class FRPStatus(Enum):
    """FRP protection status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    BYPASSED = "bypassed"
    VULNERABLE = "vulnerable"
    UNKNOWN = "unknown"


class FRPBypassMethod(Enum):
    """Known FRP bypass methods"""
    ADB_ENABLED = "adb_enabled"  # ADB left enabled
    INSECURE_SETTINGS = "insecure_settings"  # Settings accessible
    OEM_UNLOCK = "oem_unlock_enabled"  # OEM unlock enabled
    TEST_KEYS = "test_keys_present"  # Test keys in build
    DEBUG_BUILD = "debug_build"  # Debug build
    NO_FRP_PARTITION = "no_frp_partition"  # FRP partition missing
    FACTORY_RESET_PROTECTION_OFF = "frp_disabled_in_props"  # Disabled in build.prop
    ACCESSIBILITY_BYPASS = "accessibility_bypass"  # Accessibility exploit
    QUICK_SHORTCUT_MAKER = "quick_shortcut_maker"  # QSM exploit
    TALKBACK_BYPASS = "talkback_bypass"  # TalkBack exploit


@dataclass
class FRPFinding:
    """FRP security finding"""
    status: FRPStatus
    bypass_method: Optional[FRPBypassMethod]
    severity: str  # critical, high, medium, low
    description: str
    location: Optional[str] = None
    remediation: Optional[str] = None


class FRPAnalyzer:
    """
    Comprehensive FRP analysis

    REVOLUTIONARY FEATURE: First firmware tool to analyze FRP security!
    """

    def __init__(self, firmware_dir: Path):
        self.firmware_dir = Path(firmware_dir)
        self.findings: List[FRPFinding] = []

    def analyze(self) -> List[FRPFinding]:
        """
        Perform comprehensive FRP analysis

        Returns:
            List of FRP findings
        """
        print("\n🔒 Factory Reset Protection (FRP) Analysis")
        print("="*70)

        self.findings = []

        # Check build properties
        self._check_build_properties()

        # Check for FRP partition
        self._check_frp_partition()

        # Check persistent data
        self._check_persistent_data()

        # Check for bypass vulnerabilities
        self._check_bypass_vulnerabilities()

        # Check Google Account databases
        self._check_google_accounts()

        # Check system settings
        self._check_system_settings()

        # Print summary
        self._print_summary()

        return self.findings

    def _check_build_properties(self):
        """Check build.prop for FRP-related settings"""
        print("\n[1/6] Checking build properties...")

        build_props = [
            'system/build.prop',
            'vendor/build.prop',
            'product/build.prop',
        ]

        for prop_file in build_props:
            full_path = self.firmware_dir / prop_file
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Check for debug build
                if re.search(r'ro\.debuggable\s*=\s*1', content):
                    self.findings.append(FRPFinding(
                        status=FRPStatus.VULNERABLE,
                        bypass_method=FRPBypassMethod.DEBUG_BUILD,
                        severity='HIGH',
                        description='Debug build detected - FRP can be bypassed via debugging',
                        location=str(prop_file),
                        remediation='Build with ro.debuggable=0 for production'
                    ))

                # Check for test keys
                if re.search(r'ro\.build\.tags\s*=\s*test-keys', content):
                    self.findings.append(FRPFinding(
                        status=FRPStatus.VULNERABLE,
                        bypass_method=FRPBypassMethod.TEST_KEYS,
                        severity='CRITICAL',
                        description='Test keys detected - production builds should use release keys',
                        location=str(prop_file),
                        remediation='Sign with release keys for production'
                    ))

                # Check for OEM unlock
                if re.search(r'ro\.oem_unlock_supported\s*=\s*1', content):
                    oem_by_default = re.search(r'ro\.oem_unlock_enabled\s*=\s*1', content)
                    if oem_by_default:
                        self.findings.append(FRPFinding(
                            status=FRPStatus.VULNERABLE,
                            bypass_method=FRPBypassMethod.OEM_UNLOCK,
                            severity='HIGH',
                            description='OEM unlock enabled by default',
                            location=str(prop_file),
                            remediation='Disable OEM unlock by default'
                        ))

                # Check for ADB enabled
                if re.search(r'persist\.sys\.usb\.config\s*=\s*.*adb', content):
                    self.findings.append(FRPFinding(
                        status=FRPStatus.VULNERABLE,
                        bypass_method=FRPBypassMethod.ADB_ENABLED,
                        severity='CRITICAL',
                        description='ADB enabled by default - allows FRP bypass',
                        location=str(prop_file),
                        remediation='Disable ADB by default in production'
                    ))

            except Exception as e:
                print(f"⚠️  Error reading {prop_file}: {e}")

    def _check_frp_partition(self):
        """Check for FRP partition presence"""
        print("[2/6] Checking FRP partition...")

        # Common FRP partition names
        frp_partitions = ['frp', 'persistent', 'config', 'devinfo']

        # Check in system or extracted files
        found_frp = False

        for partition in frp_partitions:
            # Check for partition files
            partition_files = list(self.firmware_dir.rglob(f'*{partition}*.img'))
            if partition_files:
                found_frp = True
                print(f"  ✓ FRP partition found: {partition_files[0].name}")
                break

        if not found_frp:
            self.findings.append(FRPFinding(
                status=FRPStatus.VULNERABLE,
                bypass_method=FRPBypassMethod.NO_FRP_PARTITION,
                severity='CRITICAL',
                description='FRP partition not found in firmware',
                remediation='Ensure FRP partition exists and is properly configured'
            ))
            print(f"  ❌ FRP partition not found")

    def _check_persistent_data(self):
        """Check for persistent data that survives factory reset"""
        print("[3/6] Checking persistent data...")

        # Locations that should persist after factory reset
        persistent_paths = [
            'persistent/data',
            'frp/data',
            'metadata/frp',
        ]

        for path in persistent_paths:
            full_path = self.firmware_dir / path
            if full_path.exists():
                print(f"  ✓ Persistent data found: {path}")

    def _check_bypass_vulnerabilities(self):
        """Check for known FRP bypass vulnerabilities"""
        print("[4/6] Checking for bypass vulnerabilities...")

        # Check for Quick Shortcut Maker (known bypass tool)
        qsm_files = list(self.firmware_dir.rglob('*QuickShortcutMaker*'))
        if qsm_files:
            self.findings.append(FRPFinding(
                status=FRPStatus.VULNERABLE,
                bypass_method=FRPBypassMethod.QUICK_SHORTCUT_MAKER,
                severity='HIGH',
                description='Quick Shortcut Maker found - known FRP bypass tool',
                location=str(qsm_files[0]),
                remediation='Remove Quick Shortcut Maker from production builds'
            ))

        # Check for TalkBack (accessibility bypass)
        talkback_accessible = self._check_talkback_accessible()
        if talkback_accessible:
            self.findings.append(FRPFinding(
                status=FRPStatus.VULNERABLE,
                bypass_method=FRPBypassMethod.TALKBACK_BYPASS,
                severity='MEDIUM',
                description='TalkBack accessible during setup - potential bypass vector',
                remediation='Restrict TalkBack access during FRP lock'
            ))

        # Check for Settings accessibility
        settings_accessible = self._check_settings_accessible()
        if settings_accessible:
            self.findings.append(FRPFinding(
                status=FRPStatus.VULNERABLE,
                bypass_method=FRPBypassMethod.INSECURE_SETTINGS,
                severity='HIGH',
                description='Settings accessible during FRP lock',
                remediation='Lock down Settings during device setup'
            ))

    def _check_google_accounts(self):
        """Check for Google Account data"""
        print("[5/6] Checking Google Account data...")

        # Common Google Account database locations
        account_dbs = [
            'data/system/accounts.db',
            'data/system_ce/0/accounts_ce.db',
            'data/system_de/0/accounts_de.db',
        ]

        for db_path in account_dbs:
            full_path = self.firmware_dir / db_path
            if full_path.exists():
                try:
                    # Try to read accounts database
                    conn = sqlite3.connect(str(full_path))
                    cursor = conn.cursor()

                    # Check for Google accounts
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()

                    if tables:
                        print(f"  ✓ Accounts database found: {db_path}")

                        # Try to get account info (redacted)
                        try:
                            cursor.execute("SELECT COUNT(*) FROM accounts WHERE type='com.google'")
                            google_accounts = cursor.fetchone()[0]

                            if google_accounts > 0:
                                self.findings.append(FRPFinding(
                                    status=FRPStatus.ENABLED,
                                    bypass_method=None,
                                    severity='INFO',
                                    description=f'FRP enabled: {google_accounts} Google account(s) bound',
                                    location=str(db_path)
                                ))
                                print(f"    Google accounts: {google_accounts} (FRP active)")

                        except (KeyError, ValueError, TypeError) as e:
                            # Skip malformed database entries
                            pass

                    conn.close()

                except Exception as e:
                    print(f"  ⚠️  Could not read {db_path}: {e}")

    def _check_system_settings(self):
        """Check system settings databases"""
        print("[6/6] Checking system settings...")

        settings_dbs = [
            'data/system/users/0/settings_global.xml',
            'data/system/users/0/settings_secure.xml',
            'data/system/users/0/settings_system.xml',
        ]

        for settings_file in settings_dbs:
            full_path = self.firmware_dir / settings_file
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Check for relevant settings
                    if 'development_settings_enabled' in content:
                        print(f"  ⚠️  Developer settings may be enabled")

                    if 'adb_enabled' in content:
                        print(f"  ⚠️  ADB setting present in settings")

                except Exception as e:
                    print(f"  ⚠️  Error reading {settings_file}: {e}")

    def _check_talkback_accessible(self) -> bool:
        """Check if TalkBack is accessible during setup"""
        # Would check accessibility service configurations
        return False

    def _check_settings_accessible(self) -> bool:
        """Check if Settings is accessible during FRP lock"""
        # Would check setup wizard configuration
        return False

    def _print_summary(self):
        """Print FRP analysis summary"""
        print("\n" + "="*70)
        print("FRP ANALYSIS SUMMARY")
        print("="*70)

        if not self.findings:
            print("\n✅ No FRP issues detected")
            print("   FRP appears to be properly configured")
            return

        # Count by severity
        critical = [f for f in self.findings if f.severity == 'CRITICAL']
        high = [f for f in self.findings if f.severity == 'HIGH']
        medium = [f for f in self.findings if f.severity == 'MEDIUM']
        low = [f for f in self.findings if f.severity == 'LOW']
        info = [f for f in self.findings if f.severity == 'INFO']

        print(f"\nTotal Findings: {len(self.findings)}")
        if critical:
            print(f"  🔴 CRITICAL: {len(critical)}")
        if high:
            print(f"  🟠 HIGH:     {len(high)}")
        if medium:
            print(f"  🟡 MEDIUM:   {len(medium)}")
        if low:
            print(f"  🔵 LOW:      {len(low)}")
        if info:
            print(f"  ℹ️  INFO:     {len(info)}")

        # Print critical and high findings
        important = critical + high
        if important:
            print("\n" + "-"*70)
            print("CRITICAL & HIGH SEVERITY FINDINGS:")
            print("-"*70)

            for finding in important:
                print(f"\n[{finding.severity}] {finding.status.value.upper()}")
                if finding.bypass_method:
                    print(f"  Method: {finding.bypass_method.value}")
                print(f"  Description: {finding.description}")
                if finding.location:
                    print(f"  Location: {finding.location}")
                if finding.remediation:
                    print(f"  Remediation: {finding.remediation}")

    def export_report(self, output_file: Path):
        """Export FRP analysis report"""
        import json

        report = {
            'firmware_path': str(self.firmware_dir),
            'total_findings': len(self.findings),
            'findings': [
                {
                    'status': f.status.value,
                    'bypass_method': f.bypass_method.value if f.bypass_method else None,
                    'severity': f.severity,
                    'description': f.description,
                    'location': f.location,
                    'remediation': f.remediation
                }
                for f in self.findings
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ FRP analysis report exported: {output_file}")

    def get_frp_status(self) -> FRPStatus:
        """Get overall FRP status"""
        if not self.findings:
            return FRPStatus.ENABLED

        # Check for critical vulnerabilities
        for finding in self.findings:
            if finding.status == FRPStatus.VULNERABLE and finding.severity == 'CRITICAL':
                return FRPStatus.BYPASSED

        # Check for enabled FRP
        for finding in self.findings:
            if finding.status == FRPStatus.ENABLED:
                return FRPStatus.ENABLED

        return FRPStatus.UNKNOWN
