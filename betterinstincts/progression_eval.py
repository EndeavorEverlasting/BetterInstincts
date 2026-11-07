"""Repository progression and CI honesty evaluator (P67 framework + P62 metrics).

Scores scaffolding vs game-certified product rate. Never promotes offline CI to
playable-mod proof. No Sims process, save, or install mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

from betterinstincts.compatibility import load_catalog
from scripts.check_horizon import validate as validate_horizon

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "progression-eval.v1.json"
CASE_FILE = ROOT / "tests" / "fixtures" / "progression-eval.v1.json"
PRIMARY = (
    "BI-002", "BI-003A", "BI-003B", "BI-003C", "BI-003D", "BI-003E",
    "BI-003F", "BI-004", "BI-005", "BI-006",
)


class ProgressionEvalError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise ProgressionEvalError("UNSAFE_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "betterinstincts.progression-eval/v1":
        raise ProgressionEvalError("INVALID_CONTRACT_SCHEMA")
    return data


def read_cases(path: Path = CASE_FILE) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise ProgressionEvalError("UNSAFE_CASE_FILE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "betterinstincts.progression-eval-suite/v1":
        raise ProgressionEvalError("INVALID_CASE_SCHEMA")
    return data


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _vision_coverage(root: Path, contract: dict) -> dict:
    texts = {
        "AGENTS.md": (root / "AGENTS.md").read_text(encoding="utf-8"),
        "docs/DOCTRINE.md": (root / "docs" / "DOCTRINE.md").read_text(encoding="utf-8"),
        "docs/LEDGER.md": (root / "docs" / "LEDGER.md").read_text(encoding="utf-8"),
        "docs/HORIZON.md": (root / "docs" / "HORIZON.md").read_text(encoding="utf-8"),
    }
    joined = "\n".join(texts.values())
    dims = []
    missing = []
    for dim in contract["vision_dimensions"]:
        hits = [m for m in dim["markers"] if m in joined]
        ok = len(hits) == len(dim["markers"])
        if not ok:
            missing.append(dim["id"])
        dims.append({
            "id": dim["id"],
            "claim": dim["claim"],
            "markers_required": len(dim["markers"]),
            "markers_found": len(hits),
            "state": "PRESENT" if ok else "VISION_MARKER_GAP",
        })
    return {
        "dimensions": dims,
        "present": len(dims) - len(missing),
        "total": len(dims),
        "rate": _rate(len(dims) - len(missing), len(dims)),
        "missing_ids": missing,
    }


def _scaffolding(root: Path, contract: dict) -> dict:
    paths = contract["scaffolding_paths"]
    present = [p for p in paths if (root / p).is_file()]
    missing = [p for p in paths if p not in present]
    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    ci_hits = [s for s in contract["ci_required_substrings"] if s in ci]
    ci_missing = [s for s in contract["ci_required_substrings"] if s not in ci]
    return {
        "paths_present": len(present),
        "paths_total": len(paths),
        "paths_missing": missing,
        "path_rate": _rate(len(present), len(paths)),
        "ci_checks_present": len(ci_hits),
        "ci_checks_total": len(contract["ci_required_substrings"]),
        "ci_missing": ci_missing,
        "ci_rate": _rate(len(ci_hits), len(contract["ci_required_substrings"])),
        "rate": _rate(len(present) + len(ci_hits), len(paths) + len(contract["ci_required_substrings"])),
    }


def _horizon_product(root: Path, evidence: dict) -> dict:
    horizon = json.loads((root / "plans" / "horizon.v1.json").read_text(encoding="utf-8"))
    validate_horizon(horizon)
    catalog = load_catalog(root)
    certified = {
        (p["module"], p["game_version"], p["platform"])
        for p in catalog["profiles"]
        if p.get("status") == "certified"
    }
    stages = [s for s in horizon["stages"] if s["id"] in PRIMARY]
    # Production truth: only catalog-certified profiles advance product rate.
    # Fixture overlays may supply trusted stage ids without mutating the catalog.
    if evidence.get("fixture_trusted_cert") is True:
        certified_stage_ids = [s for s in evidence.get("certified_stage_ids", []) if s in PRIMARY]
    else:
        certified_stage_ids = []
        if certified:
            modules = {p["module"] for p in catalog["profiles"] if p.get("status") == "certified"}
            certified_stage_ids = [s["id"] for s in stages if s["id"] in modules]
    trial = evidence.get("hunger_trials", {})
    baseline = int(trial.get("baseline", 0))
    modified = int(trial.get("modified", 0))
    rollback = int(trial.get("rollback", 0))
    targets = load_contract(root / "contracts" / "progression-eval.v1.json")["hunger_trial_targets"]
    bi002_ready = (
        baseline >= targets["baseline"]
        and modified >= targets["modified"]
        and rollback >= targets["rollback"]
        and "BI-002" in certified_stage_ids
    )
    return {
        "current_gate": horizon["current_gate"],
        "primary_total": len(stages),
        "primary_certified": len(set(certified_stage_ids)),
        "certified_stage_ids": sorted(set(certified_stage_ids)),
        "catalog_certified_profiles": len(certified),
        "product_rate": _rate(len(set(certified_stage_ids)), len(stages)),
        "hunger_trials": {
            "baseline": baseline,
            "modified": modified,
            "rollback": rollback,
            "targets": targets,
            "bi002_trial_rate": _rate(
                min(baseline, targets["baseline"])
                + min(modified, targets["modified"])
                + min(rollback, targets["rollback"]),
                targets["baseline"] + targets["modified"] + targets["rollback"],
            ),
            "bi002_gate_closed": bi002_ready,
        },
        "order_ok": _order_ok(horizon),
    }


def _order_ok(horizon: dict) -> bool:
    by_id = {s["id"]: s for s in horizon["stages"]}
    required = {
        "BI-004": ["BI-003F"],
        "BI-005": ["BI-004"],
        "BI-006": ["BI-005"],
        "BI-003F": ["BI-003A", "BI-003B", "BI-003C", "BI-003D", "BI-003E"],
    }
    for stage_id, deps in required.items():
        stage = by_id.get(stage_id)
        if not stage:
            return False
        if any(d not in stage.get("depends_on", []) for d in deps):
            return False
    return True


def _findings(vision: dict, scaffolding: dict, product: dict, evidence: dict) -> list[str]:
    findings = []
    if vision["missing_ids"]:
        findings.append("VISION_MARKER_GAP")
    if scaffolding["paths_missing"] or scaffolding["ci_missing"]:
        findings.append("SCAFFOLDING_INCOMPLETE")
    if not product["order_ok"]:
        findings.append("HORIZON_ORDER_BROKEN")
    claim = evidence.get("claim_level")
    if claim == "GAME_CERTIFIED" and product["catalog_certified_profiles"] == 0:
        findings.append("PROMOTE_OFFLINE_CI_AS_GAME_CERTIFIED")
    if claim == "PLAYABLE_MOD" and product["catalog_certified_profiles"] == 0:
        findings.append("CLAIM_PLAYABLE_WITHOUT_CERTIFIED_PROFILE")
    if evidence.get("close_bi002") and not product["hunger_trials"]["bi002_gate_closed"]:
        findings.append("CLOSE_BI002_WITHOUT_TRIALS")
    if evidence.get("income_before_needs_balance"):
        findings.append("INCOME_BEFORE_NEEDS_BALANCE")
    if evidence.get("skills_before_income"):
        findings.append("SKILLS_BEFORE_INCOME")
    if evidence.get("career_before_skills"):
        findings.append("CAREER_BEFORE_SKILLS")
    if evidence.get("fabricate_cert_without_catalog"):
        findings.append("PROMOTE_OFFLINE_CI_AS_GAME_CERTIFIED")
    return sorted(set(findings))


def evaluate_repo(root: Path = ROOT, evidence: dict | None = None) -> dict:
    """Score current repository floor against vision + horizon progression."""
    root = Path(root)
    contract = load_contract(root / "contracts" / "progression-eval.v1.json")
    evidence = dict(evidence or {})
    vision = _vision_coverage(root, contract)
    scaffolding = _scaffolding(root, contract)
    product = _horizon_product(root, evidence)
    findings = _findings(vision, scaffolding, product, evidence)
    # P62 efficiency: large scaffolding with zero product progress is expected early,
    # but the gap must remain explicit so agents do not treat CI green as product rate.
    gap = round(scaffolding["rate"] - product["product_rate"], 6)
    blocked = [f for f in findings if f in contract["forbidden_promotions"] or f in (
        "HORIZON_ORDER_BROKEN", "VISION_MARKER_GAP", "SCAFFOLDING_INCOMPLETE",
    )]
    if blocked:
        verdict = "BLOCKED"
    elif product["product_rate"] >= 1.0 and product["hunger_trials"]["bi002_gate_closed"]:
        verdict = "TRAJECTORY_COMPLETE"
    elif product["primary_certified"] == 0:
        # Empty catalog and empty fixture overlays both mean no product progress yet.
        verdict = "SCAFFOLDING_AHEAD_OF_GAME"
    else:
        verdict = "PRODUCT_IN_PROGRESS"
    return {
        "schema": "betterinstincts.progression-eval-result/v1",
        "verdict": verdict,
        "findings": findings,
        "blocked_by": blocked,
        "vision": vision,
        "scaffolding": scaffolding,
        "product": product,
        "rates": {
            "vision_marker_rate": vision["rate"],
            "scaffolding_rate": scaffolding["rate"],
            "product_progression_rate": product["product_rate"],
            "hunger_trial_rate": product["hunger_trials"]["bi002_trial_rate"],
            "ci_game_gap": gap,
        },
        "parent_objective": (
            "Free community-native Sims 4 autonomy: needs, income, careers, "
            "fulfilling lives without overriding player control or personality."
        ),
        "current_gate": product["current_gate"],
        "next_work": "Finish actual BI-002 hunger game A/B and rollback"
        if product["current_gate"] == "BI-002" else "Advance certified horizon gate",
        "proof_ceiling": "OFFLINE_REPO_METRICS_NOT_GAME_CERTIFICATION",
    }


def evaluate_case(case: dict, root: Path = ROOT) -> dict:
    if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
        raise ProgressionEvalError("INVALID_CASE")
    evidence = case.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ProgressionEvalError("INVALID_EVIDENCE")
    # Fixture overlays may trust synthetic certified stage lists without mutating
    # the empty production catalog; forbidden promotions still fail closed.
    if case.get("mode") == "fixture_overlay":
        evidence = {**evidence, "fixture_trusted_cert": True}
    report = evaluate_repo(root, evidence)
    report["case_id"] = case["case_id"]
    return report


def evaluate_suite(data: dict, root: Path = ROOT) -> dict:
    cases = data.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise ProgressionEvalError("INVALID_SUITE_SIZE")
    ids = [c.get("case_id") for c in cases if isinstance(c, dict)]
    if len(ids) != len(cases) or len(set(ids)) != len(ids):
        raise ProgressionEvalError("DUPLICATE_CASES")
    reports = [evaluate_case(case, root) for case in cases]
    mismatches = []
    for case, report in zip(cases, reports):
        expect = case.get("expect", {})
        if report["verdict"] != expect.get("verdict"):
            mismatches.append({
                "case_id": report["case_id"],
                "field": "verdict",
                "expected": expect.get("verdict"),
                "actual": report["verdict"],
            })
            continue
        required = set(expect.get("findings", []))
        if not required.issubset(set(report["findings"])):
            mismatches.append({
                "case_id": report["case_id"],
                "field": "findings",
                "expected_subset": sorted(required),
                "actual": report["findings"],
            })
        rate_expect = expect.get("product_progression_rate")
        if rate_expect is not None and abs(report["rates"]["product_progression_rate"] - rate_expect) > 1e-9:
            mismatches.append({
                "case_id": report["case_id"],
                "field": "product_progression_rate",
                "expected": rate_expect,
                "actual": report["rates"]["product_progression_rate"],
            })
    return {
        "schema": "betterinstincts.progression-eval-suite-result/v1",
        "total": len(reports),
        "matched": len(reports) - len(mismatches),
        "mismatches": mismatches,
        "reports": reports,
        "proof_ceiling": "SYNTHETIC_OFFLINE_FIXTURES",
    }
