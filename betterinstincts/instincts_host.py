"""Host-side six-need instincts planner: offline plan from observed motives.

Never queues Sims interactions, never deletes/overwrites user saves, and never
treats a BI_* filename alone as disposal authority. Plans are suggestions for the
local game-host lane; live proof requires PrintWindow/observation separately.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple

from betterinstincts.horizon import SIX_NEEDS, Context, Choice, choose, PolicyError

ROOT = Path(__file__).resolve().parents[1]
NEEDS_CONTRACT = ROOT / "contracts" / "needs.v1.json"
LAB_ALIAS_RE = re.compile(r"^BI_(TMP|CONT)_[A-Z0-9_]{4,48}$")
CONT_ALIAS_RE = re.compile(r"^BI_CONT_[A-Z0-9_]{4,48}$")

# Objects the empty-lot lab must provide before a need remedy is considered available.
NEED_OBJECTS = {
    "hunger": ("fridge", "stove", "microwave", "grill"),
    "bladder": ("toilet", "privy_bush"),
    "energy": ("bed", "cot", "tent"),
    "hygiene": ("shower", "bathtub", "sink"),
    "fun": (
        "tv",
        "computer",
        "book",
        "stereo",
        "chess",
        "workout",
        "phone",
        "tablet",
        "earbuds",
        "console",
        "guitar",
        "piano",
        "easel",
        "bathtub",
    ),
    "social": ("phone", "computer", "neighbor", "visitor"),
}

ACTION_FOR_NEED = {
    "hunger": "eat",
    "bladder": "use_toilet",
    "energy": "sleep",
    "hygiene": "wash",
    "fun": "have_fun",
    "social": "socialize",
}


class InstinctsHostError(ValueError):
    """Invalid host instincts input; never treated as a live gameplay success."""


@dataclass(frozen=True)
class NeedSnapshot:
    """Normalized adult motives in [0, 1]. Unknown/missing sets are rejected."""

    needs: Mapping[str, float]
    available_objects: Tuple[str, ...] = ()
    player_directed: bool = False
    already_busy: bool = False
    sim_absent: bool = False  # rabbit-hole / school / work off-lot
    capture_ref: str = "capture:unspecified"


@dataclass(frozen=True)
class RecoveryStep:
    need: str
    action: str
    level: float
    urgency: str  # critical | low | watch | ok
    required_objects: Tuple[str, ...]
    objects_present: bool
    reason: str


@dataclass(frozen=True)
class InstinctsPlan:
    state: str
    domain: str
    steps: Tuple[RecoveryStep, ...]
    next_action: Optional[str]
    next_need: Optional[str]
    all_needs_green: bool
    save_recommendation: dict
    choice: Optional[Choice]
    proof_ceiling: str


def load_needs_contract(path: Path = NEEDS_CONTRACT) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.needs/v1":
        raise InstinctsHostError("BAD_NEED_SCHEMA")
    return cfg


def _urgency(level: float, urgent: float, preemptive: float) -> str:
    if level < urgent:
        return "critical"
    if level < preemptive:
        return "low"
    if level < 0.75:
        return "watch"
    return "ok"


def _objects_for(need: str, available: Sequence[str]) -> Tuple[Tuple[str, ...], bool]:
    required = NEED_OBJECTS[need]
    have = {x.lower() for x in available}
    present = any(obj in have for obj in required)
    return required, present


def classify_levels(snap: NeedSnapshot, cfg: dict | None = None) -> Tuple[RecoveryStep, ...]:
    cfg = cfg or load_needs_contract()
    urgent = float(cfg["urgency_threshold"])
    preempt = float(cfg["preemptive_threshold"])
    if set(snap.needs) != SIX_NEEDS:
        raise InstinctsHostError("SIX_NEEDS_REQUIRED")
    steps = []
    for need in ("bladder", "hunger", "energy", "hygiene", "fun", "social"):
        level = snap.needs[need]
        if not isinstance(level, (int, float)) or isinstance(level, bool) or not isfinite(level) or not 0 <= level <= 1:
            raise InstinctsHostError("INVALID_NEED_VALUE")
        required, present = _objects_for(need, snap.available_objects)
        tag = _urgency(level, urgent, preempt)
        reason = f"{tag}_{need}"
        if tag in {"critical", "low"} and not present:
            reason += "_object_missing"
        steps.append(RecoveryStep(
            need=need,
            action=ACTION_FOR_NEED[need],
            level=float(level),
            urgency=tag,
            required_objects=required,
            objects_present=present,
            reason=reason,
        ))
    # Critical/low first by ascending level, then watch, then ok.
    order = {"critical": 0, "low": 1, "watch": 2, "ok": 3}
    return tuple(sorted(steps, key=lambda s: (order[s.urgency], s.level, s.need)))


def all_green(snap: NeedSnapshot, green_floor: float = 0.75) -> bool:
    if set(snap.needs) != SIX_NEEDS:
        return False
    return all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) and v >= green_floor
        for v in snap.needs.values()
    )


def recommend_lab_save(*, all_needs_green: bool, alias: str = "BI_CONT_NEEDS_GREEN_01") -> dict:
    """Only recommend Save As under BI_CONT_ when motives are green.

    Never authorizes DELETE/OVERWRITE/RESUME. Names alone never make a user save
    disposable; registry + operator attestation remain mandatory downstream.
    """
    if not CONT_ALIAS_RE.fullmatch(alias):
        raise InstinctsHostError("LAB_CONTINUATION_ALIAS_REQUIRED")
    if not all_needs_green:
        return {
            "state": "HOLD_SAVE",
            "alias": None,
            "intent": None,
            "reason": "NEEDS_NOT_ALL_GREEN",
            "forbidden": ["DELETE", "OVERWRITE", "RESUME", "TOUCH_USER_NAMED_SAVE"],
        }
    return {
        "state": "SAVE_AS_LAB_CONTINUATION_ONLY",
        "alias": alias,
        "intent": "SAVE_AS_NEW_LAB_SLOT",
        "classification_hint": "LAB_CONTINUATION",
        "reason": "ALL_SIX_NEEDS_GREEN",
        "forbidden": ["DELETE", "OVERWRITE", "RESUME", "TOUCH_USER_NAMED_SAVE"],
        "note": "Register alias with origin=LAB_CREATED before any future SELECT_FOR_PLAY.",
    }


def plan(snap: NeedSnapshot, cfg: dict | None = None, *, green_floor: float = 0.75,
         continuation_alias: str = "BI_CONT_NEEDS_GREEN_01") -> InstinctsPlan:
    """Build a recovery plan from an observed (or operator-attested) need snapshot."""
    cfg = cfg or load_needs_contract()
    steps = classify_levels(snap, cfg)
    green = all_green(snap, green_floor)
    save = recommend_lab_save(all_needs_green=green, alias=continuation_alias)
    if green and (snap.sim_absent or snap.player_directed or snap.already_busy):
        save = {**save, "state": "HOLD_SAVE", "alias": None, "intent": None,
                "reason": "SIM_ABSENT_BUSY_OR_PLAYER_DIRECTED"}

    if snap.sim_absent:
        return InstinctsPlan(
            state="SIM_ABSENT_PLAN_ONLY",
            domain="host_prep",
            steps=steps,
            next_action=None,
            next_need=None,
            all_needs_green=green,
            save_recommendation=save,
            choice=None,
            proof_ceiling="OFFLINE_PLAN_WHILE_SIM_ABSENT_NOT_LIVE_QUEUE",
        )

    available_actions = []
    for step in steps:
        if step.objects_present or step.urgency == "ok":
            available_actions.append(step.action)
        # Missing objects: withhold that remedy so horizon cannot pick an impossible action.
    # Always allow leisure as a safe filler once needs are satisfied.
    available_actions.extend(["earn_income", "practice_skill", "enjoy_leisure"])
    available = tuple(dict.fromkeys(available_actions))

    try:
        choice = choose(
            Context(
                needs=dict(snap.needs),
                available_actions=available,
                player_directed=snap.player_directed,
                already_busy=snap.already_busy,
                autonomy_enabled=True,
                supported_life_stage=True,
                needs_game_certified=False,  # refuse income/skills until live-certified
            ),
            cfg,
        )
    except PolicyError as exc:
        raise InstinctsHostError(str(exc)) from exc

    # Block only for the selected remedy's missing objects, or when urgent needs
    # remain with no eligible remedy (horizon abstained because actions unavailable).
    if choice is not None and choice.domain == "needs":
        selected = next((s for s in steps if s.action == choice.action), None)
        if selected is not None and not selected.objects_present:
            return InstinctsPlan(
                state="BLOCKED_MISSING_OBJECTS",
                domain="needs",
                steps=steps,
                next_action=None,
                next_need=selected.need,
                all_needs_green=green,
                save_recommendation=save,
                choice=choice,
                proof_ceiling="HOST_PLAN_OBJECT_GAP_NOT_GAME_QUEUE",
            )
    gaps = [s for s in steps if s.urgency in {"critical", "low"} and not s.objects_present]
    if choice is None and gaps:
        first = gaps[0]
        return InstinctsPlan(
            state="BLOCKED_MISSING_OBJECTS",
            domain="needs",
            steps=steps,
            next_action=None,
            next_need=first.need,
            all_needs_green=green,
            save_recommendation=save,
            choice=None,
            proof_ceiling="HOST_PLAN_OBJECT_GAP_NOT_GAME_QUEUE",
        )

    return InstinctsPlan(
        state="PLAN_READY" if choice else "ABSTAIN",
        domain=(choice.domain if choice else "none"),
        steps=steps,
        next_action=(choice.action if choice else None),
        next_need=next((s.need for s in steps if s.action == (choice.action if choice else "")), None),
        all_needs_green=green,
        save_recommendation=save,
        choice=choice,
        proof_ceiling="HOST_PLAN_ONLY_NOT_LIVE_INTERACTION_PROOF",
    )


def plan_to_dict(result: InstinctsPlan) -> dict:
    return {
        "state": result.state,
        "domain": result.domain,
        "next_action": result.next_action,
        "next_need": result.next_need,
        "all_needs_green": result.all_needs_green,
        "save_recommendation": result.save_recommendation,
        "proof_ceiling": result.proof_ceiling,
        "choice": None if result.choice is None else {
            "action": result.choice.action,
            "reason": result.choice.reason,
            "domain": result.choice.domain,
        },
        "steps": [
            {
                "need": s.need,
                "action": s.action,
                "level": s.level,
                "urgency": s.urgency,
                "required_objects": list(s.required_objects),
                "objects_present": s.objects_present,
                "reason": s.reason,
            }
            for s in result.steps
        ],
    }


def is_lab_alias(alias: str) -> bool:
    return bool(LAB_ALIAS_RE.fullmatch(alias))
