"""Read-only oldest-first advisory for *already authorized* lab trial save identities.

No Sims save enumeration, game input, persistence, or selection occurs here.
A date sorts operator-attested LAB_DISPOSABLE records; it never grants authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from betterinstincts.installation_profiles import HOUSEHOLD_ID
from betterinstincts.save_policy import (
    MANIFEST_SCHEMA,
    PATCH_RE,
    RUN_ID_RE,
    SavePolicyError,
    decide,
    load_registry,
)

UTC_SECONDS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
ADVISORY = "OLDEST_ELIGIBLE_LAB_DISPOSABLE_FIRST_ADVISORY_ONLY"


def _lab_creation_time(record: dict) -> datetime | None:
    value = record.get("lab_created_at_utc")
    if (not isinstance(value, str) or not UTC_SECONDS.fullmatch(value)
            or record.get("lab_creation_time_confirmed") is not True):
        return None
    try:
        result = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return result if result.strftime("%Y-%m-%dT%H:%M:%SZ") == value else None


def rank_lab_candidates(
    registry: dict, *, run_id: str, game_version: str, household_id: str | None = None,
    current_run_only: bool = False,
) -> dict:
    """Rank, never select. Missing age or failed guard for ANY lab candidate abstains.

    The canonical decide() guard is evaluated for every proposed lab-disposable
    entry with its exact current-run/capture bindings. Older user or continuation
    saves never participate, even when their recorded creation dates are older.
    """
    if (not isinstance(registry, dict) or registry.get("schema") != MANIFEST_SCHEMA
            or not isinstance(registry.get("entries"), list)
            or len(registry["entries"]) > 150):
        raise SavePolicyError("INVALID_SAVE_REGISTRY_SCHEMA")
    if (not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id)
            or not isinstance(game_version, str) or not PATCH_RE.fullmatch(game_version)):
        raise SavePolicyError("INVALID_CURRENT_RUN_OR_GAME_VERSION")

    if household_id is not None and (not isinstance(household_id, str)
                                     or not HOUSEHOLD_ID.fullmatch(household_id)):
        raise SavePolicyError("INVALID_HOUSEHOLD_ID")

    candidates: list[tuple[datetime, dict]] = []
    excluded = 0
    unrankable = 0
    outside_scope = 0
    for record in registry["entries"]:
        if not isinstance(record, dict):
            raise SavePolicyError("INVALID_SAVE_REGISTRY_ENTRY")
        if record.get("classification") != "LAB_DISPOSABLE":
            excluded += 1
            continue

        if (current_run_only or household_id is not None) and record.get("authorized_run_id") != run_id:
            outside_scope += 1
            continue
        if household_id is not None:
            bound_household = record.get("household_id")
            if (not isinstance(bound_household, str) or not HOUSEHOLD_ID.fullmatch(bound_household)
                    or record.get("household_binding_confirmed") is not True):
                unrankable += 1
                continue
            if bound_household != household_id:
                outside_scope += 1
                continue

        try:
            decision = decide(
                registry,
                save_id=record.get("save_id"),
                run_id=run_id,
                alias=record.get("alias"),
                game_version=game_version,
                capture_ref=record.get("capture_ref"),
                intent="SELECT_FOR_PLAY",
            )
        except (SavePolicyError, TypeError, ValueError):
            unrankable += 1
            continue
        stamp = _lab_creation_time(record)
        if decision["state"] != "OPERATOR_ATTESTED_SELECTION_ONLY" or stamp is None:
            unrankable += 1
            continue
        candidates.append((stamp, record))

    base = {
        "ranking_rule": ADVISORY,
        "protected_or_continuation_excluded": excluded,
        **({"outside_household_or_run_excluded": outside_scope}
           if current_run_only or household_id is not None else {}),
        "unrankable_lab_candidates": unrankable,
        "ranked_candidates": [],
        "selected_save_id": None,
        "control_permit": None,
        "automatic_input": False,
        "save_file_access": False,
        "proof_ceiling": "OPERATOR_ATTESTED_LAB_AGE_NOT_GAME_OR_SAVE_FILE_PROOF",
    }
    if unrankable:
        return {
            **base,
            "state": "ABSTAIN_UNRANKABLE_LAB_CANDIDATE",
            "reason": "MISSING_OR_CONFLICTING_LAB_ORIGIN_BINDING_OR_CREATION_TIME",
        }
    if not candidates:
        return {**base, "state": "NO_ELIGIBLE_LAB_DISPOSABLE_CANDIDATE"}
    candidates.sort(key=lambda item: item[0])
    if any(a[0] == b[0] for a, b in zip(candidates, candidates[1:])):
        return {**base, "state": "ABSTAIN_AMBIGUOUS_CREATION_ORDER"}
    return {
        **base,
        "state": "PRIORITY_ADVISORY_ONLY",
        "ranked_candidates": [
            {
                "save_id": record["save_id"],
                "alias": record["alias"],
                "lab_created_at_utc": record["lab_created_at_utc"],
                "priority": index,
                "selection_authorized_by_ranking": False,
            }
            for index, (_, record) in enumerate(candidates, start=1)
        ],
        "next_gate": "OPERATOR_CHOOSES_SLOT_AND_GAME_HOST_INDEPENDENTLY_REVALIDATES",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True, help="Explicit lab registry JSON; never Sims save files")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--game-version", required=True)
    args = parser.parse_args(argv)
    try:
        result = rank_lab_candidates(
            load_registry(args.registry), run_id=args.run_id, game_version=args.game_version
        )
    except (SavePolicyError, ValueError, OSError, TypeError) as exc:
        result = {"state": "BLOCKED", "reason": str(exc), "selected_save_id": None}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] == "PRIORITY_ADVISORY_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
