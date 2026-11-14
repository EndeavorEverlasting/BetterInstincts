"""Pure local-gameplay session continuity triage.

A paused Sims game, a completed report, and a finished Codex turn are not
evidence that the BetterInstincts parent objective is complete. This module
does not actuate the game, run a background agent or grant a host permit.
MoonWake remains the owner of generic execution-boundary governance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "betterinstincts.agent-session-continuity/v1"
GAME_STATES = frozenset({"PAUSED", "RUNNING", "NOT_VISIBLE", "UNKNOWN"})
SCENES = frozenset({"LIVE", "OTHER", "UNKNOWN"})
SAVE_SCOPES = frozenset({"DISPOSABLE_VERIFIED", "PROTECTED", "UNKNOWN"})
PRESENCE = frozenset({"INACTIVE", "ACTIVE", "UNKNOWN"})
ACCESS = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})


class SessionEvidenceError(ValueError):
    """Invalid or unsupported admission snapshot."""


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SessionEvidenceError(field + " must be an object")
    return value


def _choice(value: Any, field: str, choices: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise SessionEvidenceError(field + " has unsupported value")
    return value


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SessionEvidenceError(field + " must be a boolean")
    return value


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(v, str) or not v.strip() for v in value
    ):
        raise SessionEvidenceError("evidence_refs must be a list of nonempty strings")
    if len(value) > 32 or len(set(value)) != len(value):
        raise SessionEvidenceError("evidence_refs must be unique and bounded")
    return list(value)


def assess_session(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Select one next gate; never infer a host effect permit or gameplay proof."""
    item = _object(payload, "session")
    if item.get("schema") != SCHEMA:
        raise SessionEvidenceError("session schema mismatch")
    parent = item.get("parent_objective")
    if not isinstance(parent, str) or not parent.strip() or len(parent) > 8192:
        raise SessionEvidenceError("parent_objective must be meaningful and bounded")
    completion = _object(item.get("completion"), "completion")
    accepted = _boolean(completion.get("accepted"), "completion.accepted")
    completion_refs = _refs(completion.get("evidence_refs"))
    if accepted and not completion_refs:
        raise SessionEvidenceError("COMPLETION_REQUIRES_EVIDENCE")

    game = _object(item.get("game"), "game")
    game_state = _choice(game.get("state"), "game.state", GAME_STATES)
    scene = _choice(game.get("scene"), "game.scene", SCENES)
    save = _choice(game.get("save_scope"), "game.save_scope", SAVE_SCOPES)
    player = _choice(item.get("player_presence"), "player_presence", PRESENCE)
    permitted = _boolean(item.get("operator_gameplay_permission"), "operator_gameplay_permission")
    offline = _object(item.get("offline_work"), "offline_work")
    offline_ready = _boolean(offline.get("ready"), "offline_work.ready")
    offline_action = offline.get("action")
    if not isinstance(offline_action, str):
        raise SessionEvidenceError("offline_work.action must be a string")
    if offline_ready and not offline_action.strip():
        raise SessionEvidenceError("ready offline work requires an explicit action")
    host = _object(item.get("host_access"), "host_access")
    host_state = _choice(host.get("state"), "host_access.state", ACCESS)
    host_refs = _refs(host.get("evidence_refs"))

    def result(decision: str, reason: str, *, stop: bool = False,
               action: str = "", resume: str = "") -> dict[str, Any]:
        return {
            "schema": "betterinstincts.agent-session-continuity-result/v1",
            "decision": decision,
            "terminal_stop_valid": stop,
            "parent_complete": decision == "COMPLETE_PROVEN",
            "next_action": action,
            "resume_condition": resume,
            "reason": reason,
            "proof_ceiling": "OFFLINE_SESSION_TRIAGE_NOT_GAME_EFFECT_OR_LIVE_CERT",
        }

    if accepted:
        return result(
            "COMPLETE_PROVEN",
            "Explicit acceptance has supporting evidence; do not infer what the receipts prove.",
            stop=True, action="Verify each required parent acceptance gate separately",
        )

    # Human sovereignty always outranks automation. Independent source work
    # can continue without touching the user's active or uncertain desktop.
    if player != "INACTIVE":
        if offline_ready:
            return result(
                "CONTINUE_OFFLINE", "Player input is active or uncertain; no game effects.",
                action=offline_action.strip(),
            )
        return result(
            "YIELD_TO_PLAYER", "No safe game effect while player activity is active or unknown.",
            stop=True, action="Preserve parent checkpoint without touching input",
            resume="Fresh independently observed player inactivity and host admission",
        )

    # The observed lack of a game host blocks game effects, not all Sixth Gear
    # engineering. A claimed unavailability without evidence is not a blocker.
    if host_state == "UNAVAILABLE":
        if offline_ready:
            return result(
                "CONTINUE_OFFLINE", "Host access unavailable; independent source work remains.",
                action=offline_action.strip(),
            )
        if host_refs:
            return result(
                "BLOCKED_EXACT", "Evidenced game-host unavailability; no declared safe independent work.",
                stop=True, action="Retain parent as BLOCKED_LOCAL_GAME_ACCESS",
                resume="Host becomes available; recheck exact build, save, scene and human activity",
            )
        return result(
            "REOBSERVE_HOST", "Host unavailability was asserted without evidence.",
            action="Probe the actual local game/PID and known safe read-only work",
        )

    if host_state == "AVAILABLE" and game_state in {"PAUSED", "RUNNING"}:
        if scene == "LIVE" and save == "DISPOSABLE_VERIFIED" and permitted:
            if game_state == "PAUSED":
                return result(
                    "PREPARE_GAME_EFFECT_ADMISSION",
                    "Pause is a game state, not mission completion; authorization does not replace fresh per-effect admission.",
                    action="Refresh PID, save, scene, target, dual player-idle probes and screen_admit before one reversible unpause",
                )
            return result(
                "OBSERVE_GAME", "Active Live Mode supports bounded passive progress observation.",
                action="Observe one goal/queue/need outcome and update the real run ledger",
            )
        if offline_ready:
            return result(
                "CONTINUE_OFFLINE",
                "Scene, protected save, or gameplay scope does not authorize a screen effect.",
                action=offline_action.strip(),
            )
        if save == "PROTECTED":
            return result(
                "BLOCKED_EXACT", "Protected save cannot be commandeered for the experiment.",
                stop=True, action="Do not touch the save or gameplay input",
                resume="Operator selects a verified disposable test save",
            )
        return result(
            "REOBSERVE_HOST", "Live scene/save or operator gameplay authority is not sufficiently verified.",
            action="Safely reobserve scene/save/permission without game input",
        )

    if offline_ready:
        return result(
            "CONTINUE_OFFLINE", "Independent bounded engineering remains available.",
            action=offline_action.strip(),
        )
    return result(
        "INVESTIGATE_NEXT_GATE", "No proven terminal blocker and no parent completion evidence.",
        action="Recover current scene, host tool capability, safe source work and next proof gate",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path,
                        help="Operator-approved local JSON snapshot; read-only, no writes")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = assess_session(data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc), "terminal_stop_valid": False}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["terminal_stop_valid"] else 20


if __name__ == "__main__":
    raise SystemExit(main())
