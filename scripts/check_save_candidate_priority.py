"""P00/P01 harness completeness and fail-closed oldest-first policy canary."""
from __future__ import annotations

import json
from pathlib import Path

from betterinstincts.save_policy import load_policy
from scripts.save_candidate_priority import rank_lab_candidates

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md",
    "docs/SAVE_CANDIDATE_PRIORITY.md",
    "contracts/save-policy.v1.json",
    "scripts/save_candidate_priority.py",
    "tests/test_save_candidate_priority.py",
)


def check() -> str:
    if any(not (ROOT / file).is_file() for file in REQUIRED):
        raise ValueError("SAVE_PRIORITY_HARNESS_SURFACE_MISSING")
    policy = load_policy()
    rule = policy.get("lab_disposable_trial_priority")
    if not isinstance(rule, dict) or any((
        rule.get("scope") != "LAB_DISPOSABLE_ONLY_AFTER_EXISTING_SAVE_GUARD",
        rule.get("sort") != "OLDEST_ATTESTED_CREATION_UTC_FIRST",
        rule.get("selection") != "READ_ONLY_ADVISORY_NO_AUTO_SELECT",
        rule.get("missing_or_ambiguous_age") != "ABSTAIN_NO_RANKING",
        rule.get("timestamp_never_proves_disposability") is not True,
    )):
        raise ValueError("OLDEST_FIRST_CONTRACT_MISSING_OR_DOWNGRADED")
    entries = []
    for index, day in enumerate((12, 10)):
        entries.append({
            "save_id": f"slot:lab-{index:03d}",
            "alias": f"BI_TMP_TEST_{index:03d}",
            "classification": "LAB_DISPOSABLE",
            "origin": "LAB_CREATED",
            "lab_origin_confirmed": True,
            "creation_run_id": "lab-birth",
            "authorized_run_id": "lab-review",
            "capture_ref": f"capture:lab-{index:03d}",
            "game_version": "1.121.361.1020",
            "operator_confirmed": True,
            "lab_created_at_utc": f"2026-11-{day:02d}T12:00:00Z",
            "lab_creation_time_confirmed": True,
        })
    result = rank_lab_candidates(
        {"schema": "betterinstincts.save-register/v1", "entries": entries},
        run_id="lab-review", game_version="1.121.361.1020"
    )
    if (result["state"] != "PRIORITY_ADVISORY_ONLY"
            or [row["save_id"] for row in result["ranked_candidates"]]
            != ["slot:lab-001", "slot:lab-000"]
            or result["selected_save_id"] is not None
            or result["automatic_input"]):
        raise ValueError("SAVE_PRIORITY_OLDEST_FIRST_CANARY_FAILED")
    return "SAVE_PRIORITY_P00_P01_HARNESS_PASS_ADVISORY_ONLY"


if __name__ == "__main__":
    try:
        print(check())
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("SAVE_PRIORITY_HARNESS_FAIL:" + str(exc))
        raise SystemExit(1)
