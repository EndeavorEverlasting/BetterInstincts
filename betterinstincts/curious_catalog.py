"""Curious Catalog — opt-in rare/money gardening Buy shelves.

Never autoruns. Never plans slash-joined console lines. Never touches game speed.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "curious-catalog.v1.json"
SESSION_ROOT = ROOT / "dist" / "curious-catalog"
MAX_BYTES = 128_000
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class CuriousCatalogError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise CuriousCatalogError("CURIOUS_CATALOG_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.curious-catalog/v1":
        raise CuriousCatalogError("BAD_CURIOUS_CATALOG_SCHEMA")
    act = cfg.get("activation") or {}
    if act.get("require_explicit_activate") is not True:
        raise CuriousCatalogError("REQUIRE_EXPLICIT_ACTIVATE_REQUIRED")
    if act.get("never_on_startup") is not True:
        raise CuriousCatalogError("NEVER_ON_STARTUP_REQUIRED")
    if act.get("never_touch_game_speed") is not True:
        raise CuriousCatalogError("NEVER_TOUCH_GAME_SPEED_REQUIRED")
    notice = cfg.get("notice") or {}
    if notice.get("default_option_id") != "not_today":
        raise CuriousCatalogError("DEFAULT_NOT_TODAY_REQUIRED")
    seq = cfg.get("reveal_sequence") or {}
    if seq.get("show_hidden_objects") != "bb.showhiddenobjects":
        raise CuriousCatalogError("SHOW_HIDDEN_OBJECTS_REQUIRED")
    if seq.get("one_command_per_line") is not True:
        raise CuriousCatalogError("ONE_COMMAND_PER_LINE_REQUIRED")
    if seq.get("never_touch_game_speed") is not True:
        raise CuriousCatalogError("REVEAL_NEVER_TOUCH_SPEED_REQUIRED")
    forbidden = set(seq.get("forbidden_typable_forms") or [])
    if "buydebug" not in forbidden or "bb.showhiddenobjects / buydebug" not in forbidden:
        raise CuriousCatalogError("SLASH_JOIN_AND_BUYDEBUG_MUST_BE_FORBIDDEN")
    if list(seq.get("player_lines") or []) != [
        "testingcheats enabled true",
        "bb.showhiddenobjects",
    ]:
        raise CuriousCatalogError("PLAYER_LINES_REQUIRED")
    shop = cfg.get("money_garden_shop_list")
    if not isinstance(shop, list) or len(shop) < 8:
        raise CuriousCatalogError("MONEY_GARDEN_SHOP_LIST_REQUIRED")
    return cfg


def _norm(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
        raise CuriousCatalogError("INVALID_SESSION_ID")
    return session_id


def _session_dir(session_id: str) -> Path:
    return SESSION_ROOT / _validate_session_id(session_id)


def _session_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if len(raw.encode("utf-8")) > 64_000:
        raise CuriousCatalogError("SESSION_PAYLOAD_TOO_LARGE")
    path.write_text(raw, encoding="utf-8")


def reject_if_slash_joined(raw: str) -> None:
    text = (raw or "").strip().lower()
    if not text:
        return
    if "/" in text:
        raise CuriousCatalogError("SLASH_JOINED_CONSOLE_LINE_FORBIDDEN")
    if text == "buydebug" or "buydebug" in text.split():
        raise CuriousCatalogError("BUYDEBUG_NICKNAME_NOT_A_COMMAND")


def activate(session_id: str, *, note: str | None = None) -> dict:
    cfg = load_contract()
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if meta_path.is_file():
        existing = json.loads(meta_path.read_text(encoding="utf-8"))
        if existing.get("state") == "ACTIVE":
            return {"state": "ALREADY_ACTIVE", "session_id": session_id, "path": _session_rel(path)}
    payload = {
        "schema": "betterinstincts.curious-catalog.session/v1",
        "session_id": session_id,
        "state": "ACTIVE",
        "activated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": note,
        "reveals": 0,
        "never_touch_game_speed": True,
        "proof_ceiling": cfg["proof_ceiling"],
        "contract": "contracts/curious-catalog.v1.json",
    }
    _write_json(meta_path, payload)
    return {
        "state": "ACTIVATED",
        "session_id": session_id,
        "path": _session_rel(path),
        "player_lines": list(cfg["reveal_sequence"]["player_lines"]),
        "shop_hint": "python -m scripts.curious_catalog shop-list",
    }


def deactivate(session_id: str) -> dict:
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if not meta_path.is_file():
        raise CuriousCatalogError("SESSION_NOT_FOUND")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["state"] = "INACTIVE"
    meta["deactivated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_json(meta_path, meta)
    return {"state": "DEACTIVATED", "session_id": session_id}


def status(session_id: str) -> dict:
    path = _session_dir(session_id)
    meta_path = path / "session.json"
    if not meta_path.is_file():
        return {"state": "INACTIVE", "session_id": session_id, "reason": "NO_SESSION", "autorun": False}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "state": meta.get("state", "UNKNOWN"),
        "session_id": session_id,
        "reveals": meta.get("reveals", 0),
        "path": _session_rel(path),
        "autorun": False,
        "never_touch_game_speed": True,
    }


def is_active(session_id: str) -> bool:
    return status(session_id).get("state") == "ACTIVE"


def shelf_peek_prompt(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    notice = cfg["notice"]
    return {
        "prompt_id": notice["prompt_id"],
        "title": notice["title"],
        "body": notice["body"],
        "options": [
            {"option_id": notice["option_yes"]["option_id"], "label": notice["option_yes"]["label"]},
            {"option_id": notice["option_no"]["option_id"], "label": notice["option_no"]["label"]},
        ],
        "default_option_id": notice["default_option_id"],
        "style": notice.get("style") or "sims_chance_card",
        "player_lines": list(cfg["reveal_sequence"]["player_lines"]),
        "proof_ceiling": cfg["proof_ceiling"],
    }


def money_garden_shop_list(
    *,
    tier: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> list[dict]:
    cfg = cfg or load_contract()
    rows = list(cfg.get("money_garden_shop_list") or [])
    if tier:
        want = tier.strip().upper()
        rows = [r for r in rows if str(r.get("money_tier", "")).upper() == want]
    return rows


def plan_reveal(
    *,
    game_mode: str = "buy",
    include_live_edit: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    cfg = cfg or load_contract()
    seq = cfg["reveal_sequence"]
    mode = (game_mode or "unknown").strip().lower()
    if mode not in set(seq.get("allowed_modes") or []):
        raise CuriousCatalogError("INVALID_GAME_MODE")
    commands = list(seq["player_lines"])
    for cmd in commands:
        reject_if_slash_joined(cmd)
    if include_live_edit:
        commands.append(seq["optional_live_edit"])
        reject_if_slash_joined(commands[-1])
    steps = [
        {"step": "KEEP_PAUSED_OR_OPERATOR_PACE", "note": "Never click 1/2/3 speed or `", "required": True},
        {"step": "PRESERVE_OPERATOR_MODE", "required": True},
        {
            "step": "OPEN_CHEAT_CONSOLE",
            "chord": list(seq["open_console_chord"]),
            "chord_label": seq["open_console_chord_label"],
            "required": True,
        },
        {"step": "ACTIVATE_TESTING_CHEATS", "command": commands[0], "required": True},
        {
            "step": "SHOW_HIDDEN_OBJECTS",
            "command": commands[1],
            "diegetic_label": "Peek behind the shelves",
            "required": True,
        },
        {
            "step": "BUY_SEARCH",
            "searches": list(seq.get("buy_search_terms") or ["debug", "seed"]),
            "required": False,
        },
    ]
    if include_live_edit:
        steps.insert(
            -1,
            {"step": "OPTIONAL_LIVE_EDIT_OBJECTS", "command": commands[-1], "required": False},
        )
    return {
        "state": "CURIOUS_CATALOG_REVEAL_PLANNED",
        "next_gate": "CURIOUS_CATALOG_REVEAL",
        "game_mode": mode,
        "steps": steps,
        "commands": [c for c in commands if c.startswith("testing") or c.startswith("bb.")],
        "one_command_per_line": True,
        "never_touch_game_speed": True,
        "shop_list": money_garden_shop_list(cfg=cfg),
        "diegetic_title": cfg["notice"]["title"],
        "proof_ceiling": cfg["proof_ceiling"],
    }


def steps_to_commands(plan: dict) -> list[str]:
    out = []
    for step in plan.get("steps") or []:
        cmd = step.get("command")
        if isinstance(cmd, str) and cmd:
            reject_if_slash_joined(cmd)
            out.append(cmd)
    return out


def evaluate_advisory(
    *,
    session_active: bool = False,
    whims: Sequence[str] = (),
    player_requested: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    cfg = cfg or load_contract()
    aliases = {"gardening", "garden", "tend_garden", "rare_plants", "green_thumb", "alien_fruit"}
    hay = {_norm(x) for x in whims if isinstance(x, str)}
    gardening_cue = bool(hay & aliases) or any(any(a in h for a in aliases) for h in hay)
    if not session_active and not player_requested:
        return {
            "state": "CURIOUS_CATALOG_IDLE",
            "gate": "CURIOUS_CATALOG_IDLE",
            "autorun": False,
            "gardening_cue": gardening_cue,
            "notice": None,
            "player_lines": list(cfg["reveal_sequence"]["player_lines"]),
            "shop_preview": [r["id"] for r in money_garden_shop_list(cfg=cfg)[:5]],
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if not session_active and player_requested:
        return {
            "state": "CURIOUS_CATALOG_ACTIVATE_FIRST",
            "gate": "CURIOUS_CATALOG_ACTIVATE_FIRST",
            "autorun": False,
            "cli": cfg["activation"]["cli"]["activate"],
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "state": "CURIOUS_CATALOG_ADVISORY",
        "gate": "CURIOUS_CATALOG_ADVISORY",
        "autorun": False,
        "gardening_cue": gardening_cue,
        "notice": shelf_peek_prompt(cfg),
        "shop_list": money_garden_shop_list(cfg=cfg),
        "proof_ceiling": cfg["proof_ceiling"],
    }
