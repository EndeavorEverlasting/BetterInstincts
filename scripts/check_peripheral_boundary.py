"""Fail-closed source boundary: game-side code cannot repair OS peripherals.

This repository owns Sims/game capture and cooperative input, not Windows
Bluetooth services, PnP drivers, pairing databases or input preferences.
Legitimate host repair belongs to SysAdminSuite. This scan is a preventive
CI/agent guard, not a kernel sandbox for external tools or agents.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("betterinstincts", "scripts")
SELF = Path("scripts/check_peripheral_boundary.py")
DANGEROUS = {
    "OS_SERVICE_CONTROL": re.compile(
        r"\b(?:Start|Stop|Restart|Set)-Service\b|\bsc(?:\.exe)?\s+(?:start|stop|config|delete)\b|"
        r"\bBluetoothUserService_[A-Za-z0-9]+\b",
        re.IGNORECASE,
    ),
    "OS_PNP_MUTATION": re.compile(
        r"\b(?:pnputil(?:\.exe)?|Disable-PnpDevice|Enable-PnpDevice|Remove-PnpDevice)\b",
        re.IGNORECASE,
    ),
    "OS_PERIPHERAL_PREFERENCE": re.compile(
        r"\b(?:PrintScreenKeyForSnippingEnabled|BlockInput|ClipCursor)\b",
        re.IGNORECASE,
    ),
    "OS_KEYBOARD_REMAP_OR_ACCESSIBILITY": re.compile(
        r"\b(?:Scancode\s+Map|SetKeyboardState|SystemParametersInfo[AW]?|"
        r"FilterKeys|StickyKeys|ToggleKeys|Keyboard\s+Layout\\Scancode)\b",
        re.IGNORECASE,
    ),
    "OS_GLOBAL_INPUT_INTERCEPTION": re.compile(
        r"\b(?:SetWindowsHookEx[AW]?|RegisterHotKey|UnregisterHotKey)\b",
        re.IGNORECASE,
    ),
    "OS_REGISTRY_MUTATION": re.compile(
        r"\b(?:reg(?:\.exe)?\s+(?:add|delete|import)|"
        r"(?:Set|New|Remove)-ItemProperty|winreg\.(?:SetValue|DeleteValue|CreateKey))\b",
        re.IGNORECASE,
    ),
}


def inspect_source(source: str) -> tuple[str, ...]:
    """Conservative textual sentinel for privileged operations, including shell strings.

    A deliberate string-construction bypass cannot be ruled out by static
    inspection; human/repository review and external execution authority remain
    necessary. Only source files are inspected, not documentation/evidence.
    """
    return tuple(name for name, rule in DANGEROUS.items() if rule.search(source))


def inspect_repository(root: Path = ROOT) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for top in SOURCE_ROOTS:
        base = root / top
        if not base.is_dir():
            raise ValueError("SOURCE_ROOT_MISSING:" + top)
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in {".py", ".ps1", ".cmd"} or not path.is_file():
                continue
            rel = path.relative_to(root)
            if rel == SELF or any(p in {"__pycache__", ".venv"} for p in rel.parts):
                continue
            for reason in inspect_source(path.read_text(encoding="utf-8-sig")):
                violations.append((rel.as_posix(), reason))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root to inspect")
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
    print("PERIPHERAL_BOUNDARY_PASS game code contains no known Windows peripheral controls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
