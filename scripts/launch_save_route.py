"""Read-only certification-first save routing for the Sims 4 launcher.

The local memo is explicit, bounded, ignored by Git, and NOT an EA save.
This module never interacts with Sims, chooses a save, or grants game input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from betterinstincts.installation_profiles import HOUSEHOLD_ID, InstallationProfileError, view
from betterinstincts.save_policy import (
    PATCH_RE, RUN_ID_RE, SavePolicyError, decide, load_registry,
)
from scripts.save_candidate_priority import rank_lab_candidates

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONTEXT = ROOT / "dist" / "game-host" / "active-certification.v1.json"
CONTEXT_SCHEMA = "betterinstincts.launch-certification-session/v1"
CERTIFICATION_ID = "BI-VIDEO-GAMING-PREFERENCE-265965"
CAPTURE = re.compile(r"^capture:[A-Za-z0-9_.:-]{3,100}$")
MAX_CONTEXT_BYTES = 16_384


def _held(state: str, reason: str, **extra: object) -> dict:
    return {
        "state": state,
        "reason": reason,
        "selected_save_id": None,
        "control_permit": None,
        "automatic_input": False,
        "save_file_access": False,
        "game_effect": False,
        "proof_ceiling": "LOCAL_OPERATOR_MEMO_NOT_LIVE_GAME_CERTIFICATION",
        **extra,
    }


def load_context(path: Path) -> dict:
    """Read only the *chosen* local JSON memo; never inspect a Sims save."""
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_CONTEXT_BYTES):
        raise SavePolicyError("CERTIFICATION_MEMO_MISSING_OR_UNSAFE")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise SavePolicyError("CERTIFICATION_MEMO_INVALID_JSON") from exc
    if not isinstance(record, dict):
        raise SavePolicyError("CERTIFICATION_MEMO_NOT_OBJECT")
    return record


def _valid_ref(value: object) -> bool:
    return type(value) is str and CAPTURE.fullmatch(value) is not None


def _completion_reviewed(context: dict) -> bool:
    """Check a bounded *claim*, not independently authenticate Sims evidence."""
    review = context.get("completion_review")
    if not isinstance(review, dict) or review.get("reviewer_verified") is not True:
        return False
    if review.get("game_version") != context.get("game_version"):
        return False
    fields = ("current_offer_outcome_ref", "native_effect_ref",
              "rollback_ref", "review_ref")
    values = [review.get(key) for key in fields]
    return all(_valid_ref(value) for value in values) and len(set(values)) == len(values)


def household_handoff(available: tuple[str, ...], preference: str | None) -> dict:
    """Resolve a freshly observed set supplied by the host, without input."""
    if len(available) > 150 or any(
        not isinstance(value, str) or not HOUSEHOLD_ID.fullmatch(value) for value in available
    ) or len(set(available)) != len(available):
        return _held("HOLD_HOUSEHOLD_OBSERVATION", "INVALID_HOUSEHOLD_IDENTITIES")
    if not available:
        return _held("HOLD_HOUSEHOLD_OBSERVATION", "NO_HOUSEHOLD_OBSERVED")
    if preference is not None and preference not in available:
        return _held("HOUSEHOLD_CHOICE_REQUIRED", "SAVED_HOUSEHOLD_UNAVAILABLE")
    if preference is None and len(available) != 1:
        return _held("HOUSEHOLD_CHOICE_REQUIRED", "MULTIPLE_HOUSEHOLDS_WITHOUT_PREFERENCE")
    return _held("HOUSEHOLD_RESOLVED", "LOCAL_PROFILE_OR_SINGLE_OBSERVED_HOUSEHOLD",
                 household_id=preference or available[0])


def route_launch(
    context: dict, *,
    game_running_observed: bool = False,
    lab_registry: dict | None = None,
    observed_game_version: str | None = None,
    available_households: tuple[str, ...] | None = None,
    preferred_household: str | None = None,
    successor_run_id: str | None = None,
) -> dict:
    """Prioritize the active certification until an independently reviewed exit.

    game_running_observed is a *fresh* caller process observation, not a
    trusted scene/dialog identity. A memo never makes an old capture fresh.
    """
    if not isinstance(context, dict) or context.get("schema") != CONTEXT_SCHEMA:
        return _held("HOLD_CERTIFICATION_CONTEXT", "CONTEXT_SCHEMA_UNVERIFIED")
    if context.get("certification_id") != CERTIFICATION_ID:
        return _held("HOLD_CERTIFICATION_CONTEXT", "UNKNOWN_CERTIFICATION_ID")
    version, run = context.get("game_version"), context.get("run_id")
    if (not isinstance(version, str) or not PATCH_RE.fullmatch(version)
            or not isinstance(run, str) or not RUN_ID_RE.fullmatch(run)):
        return _held("HOLD_CERTIFICATION_CONTEXT", "GAME_BUILD_OR_RUN_UNVERIFIED")
    if observed_game_version is not None and observed_game_version != version:
        return _held("HOLD_CERTIFICATION_CONTEXT", "GAME_BUILD_CHANGED_RECHECK_CERTIFICATION")
    if type(game_running_observed) is not bool:
        return _held("HOLD_CERTIFICATION_CONTEXT", "PROCESS_OBSERVATION_INVALID")

    stage = context.get("status")
    if stage == "PENDING":
        if game_running_observed:
            return _held(
                "PRESERVE_RUNNING_CERTIFICATION_SESSION",
                "PRIORITIZE_CURRENT_VIDEO_GAMING_DIALOG_OVER_OLDEST_LAB_SAVE",
                priority="VIDEO_GAMING_LIVE_CERTIFICATION_FIRST",
                next_gate="INSPECT_FRESH_SCENE_AND_CURRENT_OFFER_BEFORE_ANY_PLAYER_FIRST_EFFECT",
            )
        pinned = context.get("pinned_save")
        if not isinstance(pinned, dict):
            return _held(
                "HOLD_CERTIFICATION_PIN",
                "NO_EXPLICITLY_BOUND_CERTIFICATION_SAVE_AND_NO_CURRENT_GAME_PROCESS",
                priority="VIDEO_GAMING_LIVE_CERTIFICATION_FIRST",
                next_gate="RECOVER_PREVIOUS_LOCAL_CERTIFICATION_SESSION_OR_PINNED_LAB_RECEIPT",
            )
        if not isinstance(lab_registry, dict):
            return _held(
                "HOLD_CERTIFICATION_PIN", "EXPLICIT_PRIVATE_LAB_REGISTRY_REQUIRED",
                priority="VIDEO_GAMING_LIVE_CERTIFICATION_FIRST",
            )
        try:
            decision = decide(
                lab_registry, save_id=pinned.get("save_id"),
                alias=pinned.get("alias"), capture_ref=pinned.get("capture_ref"),
                run_id=run, game_version=version, intent="SELECT_FOR_PLAY",
            )
        except (SavePolicyError, ValueError, TypeError):
            return _held("HOLD_CERTIFICATION_PIN", "PINNED_SAVE_BINDING_INVALID")
        if decision["state"] != "OPERATOR_ATTESTED_SELECTION_ONLY":
            return _held("HOLD_CERTIFICATION_PIN", "PINNED_SAVE_NOT_AUTHORIZED_LAB")
        return _held(
            "CERTIFICATION_PINNED_LAB_SAVE_ADVISORY",
            "CERTIFICATION_SAVE_PRECEDES_CHRONOLOGICAL_LAB_RANKING",
            priority="VIDEO_GAMING_LIVE_CERTIFICATION_FIRST",
            candidate_save_id=pinned["save_id"],
            candidate_classification=decision["classification"],
            next_gate="OPERATOR_AND_GAME_HOST_REVALIDATE_SAVE_SCENE_AND_PLAYER_PERMIT",
        )

    if stage == "REVIEWED_COMPLETE":
        if not _completion_reviewed(context):
            return _held(
                "HOLD_CERTIFICATION_REVIEW",
                "HISTORICAL_YES_NO_RECEIPTS_OR_SELF_ASSERTED_PASS_NOT_ENOUGH",
                next_gate="VERIFY_CURRENT_OFFER_NATIVE_EFFECT_ROLLBACK_AND_REVIEW_RECEIPTS",
            )
        household_id = None
        if available_households is not None:
            household = household_handoff(available_households, preferred_household)
            if household["state"] != "HOUSEHOLD_RESOLVED":
                return household
            household_id = household["household_id"]
            if (context.get("household_id") != household_id
                    or context["completion_review"].get("household_id") != household_id):
                return _held("HOLD_CERTIFICATION_HOUSEHOLD",
                             "REVIEWED_CERTIFICATION_HOUSEHOLD_DIFFERS_OR_IS_UNBOUND")
            if observed_game_version is None:
                return _held("HOLD_SUCCESSOR_RUN", "OBSERVED_GAME_BUILD_REQUIRED")
            if (not isinstance(successor_run_id, str) or not RUN_ID_RE.fullmatch(successor_run_id)
                    or successor_run_id == run):
                return _held("HOLD_SUCCESSOR_RUN", "DISTINCT_SUCCESSOR_RUN_REQUIRED")
        if not isinstance(lab_registry, dict):
            return _held(
                "HOLD_STANDARDIZED_LAB_REGISTRY",
                "EXPLICIT_PRIVATE_LAB_REGISTRY_REQUIRED_AFTER_CERTIFICATION",
                next_gate="SUPPLY_AUTHORIZED_LAB_REGISTRY_FOR_OLDEST_FIRST_ADVISORY",
            )
        try:
            ranked = rank_lab_candidates(
                lab_registry, run_id=successor_run_id if household_id else run,
                game_version=version, household_id=household_id,
            )
        except (SavePolicyError, ValueError, TypeError):
            return _held("HOLD_STANDARDIZED_LAB_RANKING", "RANKING_SOURCE_INVALID")
        if ranked["state"] != "PRIORITY_ADVISORY_ONLY":
            return _held(
                "HOLD_STANDARDIZED_LAB_RANKING",
                ranked["state"],
                lab_advisory=ranked,
            )
        return _held(
            "STANDARDIZED_OLDEST_DISPOSABLE_ADVISORY",
            "REVIEWED_VIDEO_GAMING_CERTIFICATION_EXIT_PRECEDES_OLDEST_LAB_TRIAL",
            lab_advisory=ranked,
            **({"household_id": household_id, "successor_run_id": successor_run_id,
                "candidate_save_id": ranked["ranked_candidates"][0]["save_id"]}
               if household_id else {}),
            next_gate="HOST_REVALIDATES_EXACT_SLOT_HOUSEHOLD_AND_EFFECT_PERMIT"
            if household_id else "OPERATOR_CHOOSES_CANDIDATE_AND_HOST_REVALIDATES_EFFECT_PERMIT",
        )
    return _held("HOLD_CERTIFICATION_CONTEXT", "UNKNOWN_CERTIFICATION_STATUS")


def route_local_context(
    *,
    path: Path = LOCAL_CONTEXT,
    registry_path: Path | None = None,
    game_running_observed: bool = False,
    observed_game_version: str | None = None,
    available_households: tuple[str, ...] | None = None,
    successor_run_id: str | None = None,
) -> dict:
    """One known private memo path; registry only when explicitly supplied."""
    try:
        memo = load_context(path)
        registry = load_registry(registry_path) if registry_path is not None else None
        return route_launch(
            memo, lab_registry=registry,
            game_running_observed=game_running_observed,
            observed_game_version=observed_game_version,
            available_households=available_households,
            preferred_household=view()["preferred_household_id"]
            if available_households is not None and memo.get("status") == "REVIEWED_COMPLETE" else None,
            successor_run_id=successor_run_id,
        )
    except (InstallationProfileError, SavePolicyError, ValueError, OSError, TypeError) as exc:
        return _held(
            "HOLD_CERTIFICATION_CONTEXT",
            str(exc),
            next_gate="RECOVER_EXISTING_LOCAL_CERTIFICATION_EVIDENCE_NOT_RESTART_SIMS",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, default=LOCAL_CONTEXT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--game-running-observed", action="store_true")
    parser.add_argument("--game-version", default=None)
    parser.add_argument("--household-id", action="append",
                        help="Freshly observed opaque household ID; repeat for every available household")
    parser.add_argument("--successor-run-id", help="Distinct attested successor trial run")
    args = parser.parse_args(argv)
    if (args.household_id is None) != (args.successor_run_id is None):
        parser.error("--household-id and --successor-run-id must be supplied together")
    result = route_local_context(
        path=args.context, registry_path=args.registry,
        game_running_observed=args.game_running_observed,
        observed_game_version=args.game_version,
        available_households=tuple(args.household_id) if args.household_id is not None else None,
        successor_run_id=args.successor_run_id,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in {
        "PRESERVE_RUNNING_CERTIFICATION_SESSION",
        "CERTIFICATION_PINNED_LAB_SAVE_ADVISORY",
        "STANDARDIZED_OLDEST_DISPOSABLE_ADVISORY",
    } else 2


if __name__ == "__main__":
    sys.exit(main())
