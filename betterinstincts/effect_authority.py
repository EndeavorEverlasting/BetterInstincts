"""Human-first effect admission; policy is not an OS sandbox or live permit.

This is one semantic owner for distinguishing passive local work from effects
that can contend with a player. Actual game/UI adapters must also pass their
independent scene, save, queue, lock and per-action idle checkpoints.
"""
from __future__ import annotations

from enum import Enum

from betterinstincts.control_handoff import DEFAULT_IDLE_MS, decide
from betterinstincts.player_presence import PresenceProbe


class EffectClass(str, Enum):
    PASSIVE_OBSERVATION = "PASSIVE_OBSERVATION"
    BACKGROUND_REASONING = "BACKGROUND_REASONING"
    SCREEN_EFFECT = "SCREEN_EFFECT"
    GAME_MUTATION = "GAME_MUTATION"
    OS_CONFIGURATION = "OS_CONFIGURATION"


BACKGROUND_CLASSES = frozenset({
    EffectClass.PASSIVE_OBSERVATION, EffectClass.BACKGROUND_REASONING,
})
HUMAN_GATED_CLASSES = frozenset({
    EffectClass.SCREEN_EFFECT, EffectClass.GAME_MUTATION,
})


def assess_effect(
    effect_class: str | EffectClass,
    *,
    session_active: bool,
    probe: PresenceProbe | None = None,
    idle_ms: int = DEFAULT_IDLE_MS,
) -> dict:
    """Decide *policy* only. Unknown and host-OS mutations deny by default.

    Only explicitly trusted, read-only callbacks can take a background lane.
    The predicate does not prove a callback is pure, authorize mutation, or
    intercept a separately running/unadopted agent.
    """
    try:
        kind = EffectClass(effect_class)
    except (ValueError, TypeError):
        return {"state": "DENIED", "reason": "UNCLASSIFIED_EFFECT", "execute_allowed": False, "needs_screen": True}
    if kind is EffectClass.OS_CONFIGURATION:
        return {"state": "DENIED", "reason": "HOST_OS_SETTINGS_NOT_GAME_AUTHORITY",
                "execute_allowed": False, "needs_screen": False}
    if not session_active:
        return {"state": "PAUSED", "reason": "SESSION_INACTIVE",
                "execute_allowed": False, "needs_screen": kind in HUMAN_GATED_CLASSES}
    if kind in BACKGROUND_CLASSES:
        return {"state": "BACKGROUND_ALLOWED", "reason": "READ_ONLY_NO_INPUT",
                "execute_allowed": True, "needs_screen": False}
    handoff = decide(
        probe if isinstance(probe, PresenceProbe)
        else PresenceProbe(False, False, probe_ok=False),
        session_active=True, idle_ms=idle_ms,
    )
    return {
        "state": "SCREEN_CANDIDATE" if handoff["screen_control_allowed"] else "PAUSED",
        "reason": handoff["reason"],
        "execute_allowed": handoff["screen_control_allowed"],
        "needs_screen": True,
        "note": "Candidate only: must still acquire lock, revalidate target and double-check before every effect.",
    }
