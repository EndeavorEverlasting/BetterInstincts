"""Reject game/agent source that attempts Windows peripheral or input control.

Read-only discovery and passive Sims observation remain possible. This CI check
is a source regression barrier, not a security sandbox or proof that the
operator's Windows machine has loaded project hooks.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("betterinstincts", "scripts")
SELF = Path("scripts/check_peripheral_boundary.py")
# Inspect *every* future executable code surface, not only the two historically
# known package roots. Test fixtures contain intentionally hostile examples.
EXCLUDED_DIRS = frozenset({
    ".git", ".venv", "venv", "__pycache__", "node_modules", "dist",
    "build", "artifacts", "tests",
})
EXECUTABLE_SUFFIXES = frozenset({
    ".py", ".pyw", ".ps1", ".psm1", ".psd1", ".cmd", ".bat", ".vbs", ".wsf", ".sh", ".js", ".jsx", ".ts", ".tsx",
    ".cjs", ".mjs", ".yml", ".yaml",
})
DANGEROUS = {
    "OS_SERVICE_CONTROL": re.compile(
        r"\b(?:Start|Stop|Restart|Set)-Service\b|\bsc(?:\.exe)?\s+(?:start|stop|config|delete)\b|"
        r"\bBluetoothUserService_[A-Za-z0-9]+\b", re.IGNORECASE,
    ),
    "OS_PNP_MUTATION": re.compile(
        r"\b(?:pnputil(?:\.exe)?|Disable-PnpDevice|Enable-PnpDevice|Remove-PnpDevice)\b",
        re.IGNORECASE,
    ),
    "OS_BLUETOOTH_PAIRING": re.compile(
        r"\b(?:PairAsync|UnpairAsync|DeviceInformationPairing|CustomPairing|"
        r"BluetoothAuthenticateDevice(?:Ex)?|BluetoothRemoveDevice|BluetoothSetServiceState)\b",
        re.IGNORECASE,
    ),
    "OS_PERIPHERAL_PREFERENCE": re.compile(
        r"\b(?:PrintScreenKeyForSnippingEnabled|BlockInput|ClipCursor)\b",
        re.IGNORECASE,
    ),
    "OS_KEYBOARD_REMAP_OR_ACCESSIBILITY": re.compile(
        r"\b(?:Scancode\s+Map|SetKeyboardState|SystemParametersInfo[AW]?|"
        r"FilterKeys|StickyKeys|ToggleKeys|Keyboard\s+Layout\\+Scancode)\b",
        re.IGNORECASE,
    ),
    "OS_GLOBAL_INPUT_INTERCEPTION": re.compile(
        r"\b(?:SetWindowsHookEx[AW]?|RegisterHotKey|UnregisterHotKey)\b",
        re.IGNORECASE,
    ),
    "OS_REGISTRY_MUTATION": re.compile(
        r"\b(?:reg(?:\.exe)?\s+(?:add|delete|import)|"
        r"(?:Set|New|Remove)-ItemProperty|winreg\.(?:SetValue(?:Ex)?|DeleteValue|CreateKey(?:Ex)?))\b",
        re.IGNORECASE,
    ),
    "OS_INPUT_FAILSAFE_DISABLED": re.compile(
        r"\b(?:[A-Za-z_]\w*\.)?FAILSAFE\s*=\s*(?:False|0)\b|"
        r"\bsetattr\s*\(\s*[A-Za-z_]\w*\s*,\s*['\"]FAILSAFE['\"]\s*,\s*(?:False|0)\s*\)",
        re.IGNORECASE,
    ),
}


def inspect_source(source: str) -> tuple[str, ...]:
    """Conservative literal sentinel; obfuscation and external tools need review."""
    return tuple(name for name, pattern in DANGEROUS.items() if pattern.search(source))


def inspect_repository(root: Path = ROOT) -> list[tuple[str, str]]:
    for top in SOURCE_ROOTS:
        if not (root / top).is_dir():
            raise ValueError("SOURCE_ROOT_MISSING:" + top)
    findings: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if rel == SELF or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        if path.is_symlink():
            findings.append((rel.as_posix(), "UNREVIEWED_EXECUTABLE_SYMLINK"))
            continue
        if not path.is_file():
            continue
        for reason in inspect_source(path.read_text(encoding="utf-8-sig")):
            findings.append((rel.as_posix(), reason))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        violations = inspect_repository(args.root)
    except (OSError, ValueError, UnicodeError) as exc:
        print("PERIPHERAL_BOUNDARY_FAIL " + str(exc))
        return 1
    if violations:
        for path, reason in violations:
            print(f"PERIPHERAL_BOUNDARY_FAIL {path}: {reason}")
        return 1
    print("PERIPHERAL_BOUNDARY_PASS all repository executable surfaces preserve Windows device/input authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
