"""Deterministic Sims main-menu reboot journey (Memory Boost → Load → Lab Play).

Contract: contracts/host-menu.v1.json
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
    if cfg.get("reboot_journey") != [
        "boot_to_main_menu",
        "dismiss_memory_boost",
        "open_load_game",
        "play_lablab_slot",
        "enter_live_from_map_lablab",
    ]:
        raise HostMenuError("REBOOT_JOURNEY_DRIFT")
    return cfg


def plan_journey(journey: str = "reboot", *, from_step: str | None = None) -> dict:
    cfg = load_contract()
    if journey != "reboot":
        raise HostMenuError("UNKNOWN_JOURNEY:" + journey)
    by_id = {row["id"]: row for row in cfg["transitions"] if isinstance(row, dict)}
    ordered_ids: Sequence[str] = cfg["reboot_journey"]
    if from_step:
        if from_step not in ordered_ids:
            raise HostMenuError("UNKNOWN_FROM_STEP:" + from_step)
        ordered_ids = ordered_ids[list(ordered_ids).index(from_step):]
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
            "forbidden": list(row.get("forbidden", cfg["forbidden_always"])),
            "note": row.get("note"),
        })
    return {
        "state": "HOST_MENU_JOURNEY_PLANNED",
        "journey": journey,
        "steps": steps,
        "forbidden_always": list(cfg["forbidden_always"]),
        "game_version": cfg.get("game_version"),
        "proof_ceiling": cfg.get("proof_ceiling"),
        "commands": cfg.get("host_commands"),
    }
