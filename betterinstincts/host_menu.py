"""Deterministic Sims host-menu reboot journey with scene-keyed resume.

Contract: contracts/host-menu.v1.json

Codified substeps (not agentic rediscovery):
  splash wait → Memory Boost X → LOAD GAME → Play LabLab save
  → pick LabLab domicile/estate on map → lot Play
  → SELECT A SIM TO PLAY profile → Play into Live

Resume from any known scene via plan_from_scene / --from-scene.
Never Resume. Never Delete. Never touch Richardson/user saves.
SendInput belongs to scripts/host_menu.py — this module plans only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "host-menu.v1.json"
MAX_BYTES = 32_000

REQUIRED_REBOOT_JOURNEY = (
    "boot_to_main_menu",
    "dismiss_memory_boost",
    "open_load_game",
    "play_lablab_slot",
    "select_lablab_domicile",
    "confirm_play_lablab_lot",
    "select_charlee_profile",
    "confirm_play_after_sim",
)

# Catalog / colloquial aliases → host-menu scene keys.
SCENE_ALIASES = {
    "splash": "splash_or_loading",
    "loading": "splash_or_loading",
    "splash_or_loading": "splash_or_loading",
    "memory_boost_modal": "memory_boost_modal",
    "memory_boost": "memory_boost_modal",
    "main_menu": "main_menu",
    "load_game_picker": "load_game_picker",
    "load_game": "load_game_picker",
    "manage_worlds_or_map": "manage_worlds_or_map",
    "manage_worlds": "manage_worlds_or_map",
    "neighborhood_map": "manage_worlds_or_map",
    "map": "manage_worlds_or_map",
    "lablab_lot_selected": "lablab_lot_selected",
    "lot_details": "lablab_lot_selected",
    "select_sim_to_play": "select_sim_to_play",
    "select_sim": "select_sim_to_play",
    "household_profile": "select_sim_to_play",
    "live_mode": "live_mode",
    "live": "live_mode",
}


class HostMenuError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise HostMenuError("HOST_MENU_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.host-menu/v1":
        raise HostMenuError("BAD_HOST_MENU_SCHEMA")
    if "RESUME" not in set(cfg.get("forbidden_always", [])):
        raise HostMenuError("RESUME_MUST_STAY_FORBIDDEN")
    if not isinstance(cfg.get("transitions"), list) or not cfg["transitions"]:
        raise HostMenuError("HOST_MENU_TRANSITIONS_REQUIRED")
    if tuple(cfg.get("reboot_journey") or ()) != REQUIRED_REBOOT_JOURNEY:
        raise HostMenuError("REBOOT_JOURNEY_DRIFT")
    scenes = cfg.get("scenes")
    if not isinstance(scenes, dict) or not scenes:
        raise HostMenuError("HOST_MENU_SCENES_REQUIRED")
    for sid, scene in scenes.items():
        if not isinstance(scene, dict):
            raise HostMenuError("INVALID_SCENE:" + sid)
        if "substeps" not in scene or not isinstance(scene["substeps"], list):
            raise HostMenuError("SCENE_SUBSTEPS_REQUIRED:" + sid)
        if sid != "live_mode" and not scene.get("next_transition"):
            raise HostMenuError("SCENE_NEXT_TRANSITION_REQUIRED:" + sid)
    return cfg


def resolve_scene(scene_id: str, cfg: dict | None = None) -> str:
    """Map catalog / colloquial scene ids onto host-menu scene keys."""
    cfg = cfg or load_contract()
    key = SCENE_ALIASES.get(scene_id, scene_id)
    contract_aliases = cfg.get("scene_aliases") or {}
    if isinstance(contract_aliases, dict) and scene_id in contract_aliases:
        key = str(contract_aliases[scene_id])
    if key not in cfg["scenes"]:
        raise HostMenuError("UNKNOWN_SCENE:" + scene_id)
    return key


def _build_steps(cfg: dict, ordered_ids: Sequence[str]) -> list[dict]:
    by_id = {row["id"]: row for row in cfg["transitions"] if isinstance(row, dict)}
    steps = []
    for tid in ordered_ids:
        row = by_id.get(tid)
        if row is None:
            raise HostMenuError("MISSING_TRANSITION:" + tid)
        if row.get("execution") == "HOST_SENDINPUT":
            click = row.get("click")
            if not (isinstance(click, list) and len(click) == 2
                    and all(isinstance(v, int) and 0 <= v <= 4000 for v in click)):
                raise HostMenuError("INVALID_CLICK:" + tid)
        steps.append({
            "id": tid,
            "from": row["from"],
            "to": row["to"],
            "gate": row["gate"],
            "execution": row["execution"],
            "click": row.get("click"),
            "substep": row.get("substep"),
            "scene_id": row.get("from"),
            "forbidden": list(row.get("forbidden", cfg["forbidden_always"])),
            "note": row.get("note"),
        })
    return steps


def plan_journey(
    journey: str = "reboot",
    *,
    from_step: str | None = None,
    from_scene: str | None = None,
) -> dict:
    if from_step and from_scene:
        raise HostMenuError("FROM_STEP_AND_FROM_SCENE_MUTEX")
    cfg = load_contract()
    if journey != "reboot":
        raise HostMenuError("UNKNOWN_JOURNEY:" + journey)
    ordered_ids: Sequence[str] = list(cfg["reboot_journey"])
    resume_scene = None
    if from_scene:
        resume_scene = resolve_scene(from_scene, cfg)
        scene = cfg["scenes"][resume_scene]
        if resume_scene == "live_mode" or scene.get("next_transition") is None:
            return {
                "state": "HOST_MENU_ALREADY_AT_TERMINAL",
                "journey": journey,
                "from_scene": resume_scene,
                "steps": [],
                "scene": scene,
                "forbidden_always": list(cfg["forbidden_always"]),
                "game_version": cfg.get("game_version"),
                "proof_ceiling": cfg.get("proof_ceiling"),
                "commands": cfg.get("host_commands"),
                "next": "Use viewport_recover / instincts_host — menu journey complete",
            }
        start = scene["next_transition"]
        if start not in ordered_ids:
            raise HostMenuError("SCENE_TRANSITION_NOT_IN_JOURNEY:" + start)
        ordered_ids = ordered_ids[list(ordered_ids).index(start):]
    elif from_step:
        # Legacy alias: enter_live_from_map_lablab → select_lablab_domicile
        if from_step == "enter_live_from_map_lablab":
            from_step = "select_lablab_domicile"
        if from_step not in ordered_ids:
            raise HostMenuError("UNKNOWN_FROM_STEP:" + from_step)
        ordered_ids = ordered_ids[list(ordered_ids).index(from_step):]
    steps = _build_steps(cfg, ordered_ids)
    out = {
        "state": "HOST_MENU_JOURNEY_PLANNED",
        "journey": journey,
        "steps": steps,
        "forbidden_always": list(cfg["forbidden_always"]),
        "game_version": cfg.get("game_version"),
        "proof_ceiling": cfg.get("proof_ceiling"),
        "commands": cfg.get("host_commands"),
    }
    if resume_scene is not None:
        out["from_scene"] = resume_scene
        out["scene"] = cfg["scenes"][resume_scene]
        out["remaining_substeps"] = [
            s.get("substep") or s["id"] for s in steps if s["execution"] == "HOST_SENDINPUT"
        ]
    return out


def plan_from_scene(scene_id: str, journey: str = "reboot") -> dict:
    """Resume the reboot journey at the substeps for an observed scene."""
    return plan_journey(journey, from_scene=scene_id)
