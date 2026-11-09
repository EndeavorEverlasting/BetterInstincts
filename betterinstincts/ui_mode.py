"""Read-only F1/F2/F3 mode context from the canonical scene classifier.

Declared visual+operator cues are *candidate* evidence, not calibrated screen
recognition. Shortcuts are intent hints only. Never grant host input authority.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from betterinstincts.scenes import SceneError, classify, load_catalog

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "ui-mode.v1.json"
MAX_CONTRACT = 20_000


class UIModeError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONTRACT:
        raise UIModeError("UI_MODE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.ui-mode/v1":
        raise UIModeError("BAD_UI_MODE_SCHEMA")
    if cfg.get("scene_to_mode") != {
        "live_mode": "LIVE", "buy_mode": "BUY", "build_mode": "BUILD"
    } or cfg.get("shortcuts_are") != "INTENT_ONLY_NEVER_MODE_PROOF":
        raise UIModeError("UI_MODE_SAFETY_CONTRACT_INVALID")
    return cfg


def evaluate_mode(
    *, game_version: str, mode_observations: list[dict],
    panel_observations: list[dict] | None = None,
    shortcut_hint: str | None = None,
    catalog: dict | None = None, cfg: dict | None = None,
) -> dict:
    """One fresh evaluate-only mode context, with optional panel classification.

    No cache, keyboard polling, screenshot inference, or fallback-to-last-mode.
    """
    cfg = cfg or load_contract()
    if shortcut_hint is not None and shortcut_hint not in cfg["shortcuts"]:
        raise UIModeError("INVALID_SHORTCUT_HINT")
    if not isinstance(game_version, str) or not game_version:
        raise UIModeError("EXACT_GAME_VERSION_REQUIRED")
    if not isinstance(mode_observations, list):
        raise UIModeError("MODE_OBSERVATIONS_MUST_BE_LIST")
    try:
        catalog = catalog or load_catalog()
        scene = classify(catalog, game_version, mode_observations)
    except SceneError as exc:
        raise UIModeError(str(exc)) from exc
    mode = (
        cfg["scene_to_mode"].get(scene["scene_id"], "UNKNOWN")
        if scene["state"] == "CANDIDATE_UNVERIFIED" else "UNKNOWN"
    )
    state = "MODE_CANDIDATE" if mode != "UNKNOWN" else "MODE_UNVERIFIED"
    if scene["state"] == "UNKNOWN_PATCH":
        state = "UNKNOWN_PATCH"
    panels = cfg["modes"].get(mode, {}).get("panels", {})
    active_panel = "unknown"
    if panel_observations is not None:
        if not isinstance(panel_observations, list) or len(panel_observations) > 32:
            raise UIModeError("INVALID_PANEL_OBSERVATIONS")
        keys: set[tuple[str, str]] = set()
        for cue in panel_observations:
            if (
                not isinstance(cue, dict)
                or set(cue) != {"source", "token"}
                or cue["source"] not in {"visual", "operator"}
                or not isinstance(cue["token"], str)
                or not 1 <= len(cue["token"]) <= 80
            ):
                raise UIModeError("UNTRUSTED_PANEL_CUE")
            keys.add((cue["source"], cue["token"]))
        matches = [
            name for name, required in panels.items()
            if ("visual", required["visual"]) in keys
            and ("operator", required["operator"]) in keys
        ]
        if len(matches) == 1:
            active_panel = matches[0]
    return {
        "schema": "betterinstincts.ui-mode.context/v1",
        "state": state,
        "mode": mode,
        "scene_id": scene["scene_id"],
        "scene_state": scene["state"],
        "scene_candidates": scene.get("candidates", []),
        "game_version": game_version,
        "shortcut_hint": shortcut_hint,
        "shortcut_is_evidence": False,
        "available_panels": list(panels),
        "active_panel": active_panel,
        "mode_autonomy_allowed": mode == "LIVE" and state == "MODE_CANDIDATE",
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }
