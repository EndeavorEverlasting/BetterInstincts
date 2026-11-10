"""P67/P62 executable, offline spatial-perception regression evaluator.

Supplied bounding boxes and contacts are *synthetic fixtures*, NOT evidence
that the host recognizes real Sims pixels or that a click is safe.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

from betterinstincts.scenes import load_catalog
from betterinstincts.spatial_perception import (
    SCHEMA, SpatialPerceptionError, assess_frame,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "contracts" / "evals" / "spatial-perception-cases.v1.json"


def _expected(result: dict, exp: dict) -> list[str]:
    failures = []
    for key in ("state", "camera_side", "object_count", "conflict"):
        if key not in exp:
            continue
        if key == "object_count":
            actual = len(result.get("objects", []))
        elif key == "conflict":
            actual = [x["reason"] for x in result.get("conflicts", [])]
            if exp[key] in actual:
                continue
        else:
            actual = result.get(key)
        if actual != exp[key]:
            failures.append(f"{key}: expected {exp[key]!r}, got {actual!r}")
    for item in exp.get("zones", []):
        obj = next((x for x in result["objects"] if x["id"] == item[0]), None)
        if obj is None or obj["zone"] != item[1]:
            failures.append(f"zone {item[0]} != {item[1]}")
    if "zone" in exp:
        item = exp["zone"]
        obj = next((x for x in result["objects"] if x["id"] == item[0]), None)
        if obj is None or obj["zone"] != item[1]:
            failures.append(f"zone {item[0]} != {item[1]}")
    if "relation" in exp:
        child, parent, kind, status = exp["relation"]
        if not any(
            x["from"] == child and x["to"] == parent and
            x["type"] == kind and x["status"] == status
            for x in result["relations"]
        ):
            failures.append(f"relation missing: {exp['relation']!r}")
    if result.get("execute_allowed") is not False:
        failures.append("execute_allowed must always be false")
    if result.get("control_permit") is not None:
        failures.append("control_permit must be None")
    return failures


def evaluate(path: Path = CASES) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 160_000:
        raise ValueError("EVAL_FIXTURES_UNSAFE")
    config = json.loads(path.read_text(encoding="utf-8"))
    cases = config.get("cases")
    if (config.get("schema") != "betterinstincts.spatial-perception.evals/v1"
            or not isinstance(cases, list) or not 12 <= len(cases) <= 64
            or len({x.get("id") for x in cases if isinstance(x, dict)}) != len(cases)):
        raise ValueError("EVAL_FIXTURES_INVALID")
    catalog = load_catalog()
    live = next(x for x in catalog["scenes"] if x["id"] == "live_mode")
    results = []
    for case in cases:
        start = time.perf_counter()
        frame = copy.deepcopy(config["frame_defaults"])
        frame.update({
            "schema": SCHEMA, "game_version": catalog["game_version"],
            "scene_cues": copy.deepcopy(live["required_cues"]),
            "objects": copy.deepcopy(case.get("objects", [])),
            "contacts": copy.deepcopy(case.get("contacts", [])),
        })
        frame.update(copy.deepcopy(case.get("overrides", {})))
        errors = []
        try:
            report = assess_frame(frame)
            if case.get("expect_error"):
                errors = [f"expected rejection {case['expect_error']}, got a report"]
            else:
                errors = _expected(report, case.get("expect") or {})
        except SpatialPerceptionError as exc:
            if str(exc) != case.get("expect_error"):
                errors = [f"unexpected rejection: {str(exc)}"]
        except Exception as exc:
            errors = [f"unexpected {type(exc).__name__}: {exc}"]
        results.append({
            "id": case["id"], "weakness_class": case["weakness"],
            "passed": not errors, "failures": errors,
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 3),
        })
    times = sorted(x["elapsed_ms"] for x in results)
    passed = sum(x["passed"] for x in results)
    return {
        "schema": "betterinstincts.spatial-perception.eval-report/v1",
        "state": "PASS" if passed == len(results) else "FAIL",
        "total": len(results), "passed": passed, "failed": len(results) - passed,
        "precision_recall": "NOT_MEASURED_NO_REAL_IMAGE_GROUND_TRUTH",
        "p95_case_ms": times[min(len(times)-1, int(len(times)*0.95))],
        "model_calls": 0, "external_tool_calls": 0,
        "baseline": "NO_PRIOR_SPATIAL_RELATION_EVAL_NOT_COMPARABLE",
        "cases": results, "game_certified": False,
        "proof_ceiling": config["proof_level"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = evaluate()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        if args.out.is_symlink():
            raise ValueError("EVAL_REPORT_DESTINATION_SYMLINK")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["state"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
