"""Offline, deterministic host journey regression suite."""
import argparse
import json
import sys
from pathlib import Path

from betterinstincts.host_eval import ROOT, HostEvalError, evaluate_suite, read_cases


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        result = evaluate_suite(read_cases(args.cases) if args.cases else read_cases())
        if args.out:
            destination = args.out.resolve()
            permitted = (ROOT / "dist" / "host-eval").resolve()
            if not destination.is_relative_to(permitted) or destination.suffix != ".json" or destination.is_symlink():
                raise HostEvalError("RECEIPT_OUTSIDE_IGNORED_HOST_EVAL_ROOT")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 1 if result["mismatches"] else 0
    except (HostEvalError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "HOST_EVAL_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
