"""Fail-closed task judgment for one fixed household skill-round-robin assignment.

Planning only. This module neither detects the actual game roster nor grants
SendInput control. Host adapters must independently observe portrait identities,
check screen admission before each input, and never treat typed cheats as proof.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts/household-judgment.v1.json"


class HouseholdJudgmentError(ValueError):
    """Unsafe or ambiguous scope cannot proceed."""


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    target = Path(path)
    if target.is_symlink() or not target.is_file() or target.stat().st_size > 16384:
        raise HouseholdJudgmentError("HOUSEHOLD_JUDGMENT_CONTRACT_UNSAFE")
    cfg = json.loads(target.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.household-judgment/v1":
        raise HouseholdJudgmentError("HOUSEHOLD_JUDGMENT_SCHEMA_INVALID")
    if cfg.get("execution", {}).get("detached_worker") is not False:
        raise HouseholdJudgmentError("DETACHED_SKILL_EXECUTION_MUST_BE_DISABLED")
    if cfg.get("roster", {}).get("changes") != "STOP_AND_RECONCILE":
        raise HouseholdJudgmentError("ROSTER_CHANGE_MUST_BLOCK")
    required_online = {"CONNECT", "CONNECT_ONLINE", "EA_CONNECT", "OPEN_GALLERY", "FORCE_SIMS_ONLINE"}
    required_expansion = {"ADD_SIM", "CREATE_SIM", "ADD_SERVO", "CREATE_SERVO", "MOVE_IN_SIM"}
    if not required_online.issubset(cfg.get("forbidden_online_actions", [])):
        raise HouseholdJudgmentError("OFFLINE_FORBIDDEN_LIST_INCOMPLETE")
    if not required_expansion.issubset(cfg.get("forbidden_skill_task_actions", [])):
        raise HouseholdJudgmentError("HOUSEHOLD_EXPANSION_FORBIDDEN_LIST_INCOMPLETE")
    return cfg


def require_fixed_roster(
    original: Sequence[str] | None,
    observed: Sequence[str] | None,
    *,
    cfg: Mapping | None = None,
) -> tuple[str, ...]:
    """Compare exact, ordered, locally attested portrait IDs; never infer N."""
    policy = cfg or load_contract()
    if not isinstance(original, (list, tuple)) or not isinstance(observed, (list, tuple)):
        raise HouseholdJudgmentError("OBSERVED_HOUSEHOLD_ROSTER_REQUIRED")
    original_keys = tuple(str(k).strip() for k in original)
    observed_keys = tuple(str(k).strip() for k in observed)
    bounds = policy["roster"]
    if not bounds["min"] <= len(original_keys) <= bounds["sanity_max"]:
        raise HouseholdJudgmentError("INVALID_HOUSEHOLD_ROSTER_SIZE")
    if not all(original_keys) or len(set(original_keys)) != len(original_keys):
        raise HouseholdJudgmentError("HOUSEHOLD_ROSTER_IDS_INVALID")
    if original_keys != observed_keys:
        raise HouseholdJudgmentError("HOUSEHOLD_ROSTER_CHANGED_STOP_RECONCILE")
    return original_keys


def judge_action(
    action: str,
    *,
    task: str = "HOUSEHOLD_SKILL_ROUND_ROBIN",
    original_roster: Sequence[str] | None = None,
    observed_roster: Sequence[str] | None = None,
    detached: bool = False,
    connection_dialog_observed: bool = False,
    cfg: Mapping | None = None,
) -> dict:
    """Advisory scope result, never a game-input permit."""
    policy = dict(cfg or load_contract())
    normalized = str(action or "").strip().upper().replace(" ", "_").replace("-", "_")
    online = set(policy["forbidden_online_actions"])
    blocked = set(policy["forbidden_skill_task_actions"])
    permitted = set(policy["allowed_skill_task_actions"])
    reason = None
    if not normalized:
        reason = "ACTION_REQUIRED"
    elif normalized in online:
        reason = "OFFLINE_ONLY_ONLINE_ACTION_FORBIDDEN"
    elif task == policy["active_task"]:
        if detached:
            reason = "DETACHED_HOUSEHOLD_UI_UNSAFE"
        elif normalized in blocked or normalized not in permitted:
            reason = "SKILL_TASK_SCOPE_FORBIDS_ACTION"
        elif normalized == "STAY_OFFLINE" and not connection_dialog_observed:
            reason = "CONNECTION_DIALOG_OBSERVATION_REQUIRED"
        else:
            try:
                require_fixed_roster(original_roster, observed_roster, cfg=policy)
            except HouseholdJudgmentError as exc:
                reason = str(exc)
    elif normalized == "STAY_OFFLINE" and connection_dialog_observed:
        pass
    elif normalized in blocked:
        # Outside a skill task these actions need their own explicit policy;
        # this module does not authorize them.
        reason = "ACTION_REQUIRES_SEPARATE_GOAL_AND_MUTATION_PERMIT"

    return {
        "state": "BLOCKED" if reason else "ACTION_IN_SCOPE",
        "reason": reason,
        "action": normalized,
        "task": task,
        "execute_allowed": False,
        "proof_ceiling": policy["proof_ceiling"],
    }


def require_skill_action(
    action: str,
    *,
    original_roster: Sequence[str],
    observed_roster: Sequence[str],
    detached: bool = False,
    cfg: Mapping | None = None,
) -> None:
    result = judge_action(
        action,
        original_roster=original_roster,
        observed_roster=observed_roster,
        detached=detached,
        cfg=cfg,
    )
    if result["state"] != "ACTION_IN_SCOPE":
        raise HouseholdJudgmentError(result["reason"])
