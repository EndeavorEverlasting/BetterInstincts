"""Fail closed if North Star → Continuity opener contract drifts."""
import json
import sys

from betterinstincts.horizon_continuity import ContinuityError, validate


def main():
    try:
        print(json.dumps(validate(), sort_keys=True))
        return 0
    except ContinuityError as exc:
        print(json.dumps({"state": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
