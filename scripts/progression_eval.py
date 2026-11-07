"""Offline progression / CI honesty evaluator runner (P67 + P62)."""
import argparse
import json
import sys
from pathlib import Path

from betterinstincts.progression_eval import (
    ROOT,
    ProgressionEvalError,
    evaluate_repo,
    evaluate_suite,
    read_cases,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cases", type=Path, help="Fixture suite path; default runs suite + repo floor")
    p.add_argument("--repo-only", action="store_true", help="Score live repository floor only")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        if args.repo_only:
            result = evaluate_repo()
            exit_code = 0 if result["verdict"] != "BLOCKED" else 1
        else:
            result = evaluate_suite(read_cases(args.cases) if args.cases else read_cases())
            # Always attach live repo floor summary for CI dashboards.
            result["repo_floor"] = evaluate_repo()
            exit_code = 1 if result["mismatches"] else 0
        if args.out:
            destination = args.out.resolve()
            permitted = (ROOT / "dist" / "progression-eval").resolve()
            if not destination.is_relative_to(permitted) or destination.suffix != ".json" or destination.is_symlink():
                raise ProgressionEvalError("RECEIPT_OUTSIDE_IGNORED_PROGRESSION_EVAL_ROOT")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return exit_code
    except (ProgressionEvalError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "PROGRESSION_EVAL_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
