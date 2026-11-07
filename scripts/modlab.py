"""CLI entrypoint to the read-only BetterInstincts Mod Lab."""
from __future__ import annotations

import argparse
import json
import sys

from betterinstincts.modlab import MAX_FILES, ModLabError, inspect_mods_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Sims 4 mod inventory; never executes or installs mods")
    parser.add_argument("--mods-root", required=True, help="Explicit full path to YOUR Mods directory; no autodetection")
    parser.add_argument("--max-files", type=int, default=MAX_FILES, help=f"Maximum recognized files (1..{MAX_FILES})")
    args = parser.parse_args(argv)
    try:
        report = inspect_mods_root(args.mods_root, max_files=args.max_files)
    except (ModLabError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "code": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
