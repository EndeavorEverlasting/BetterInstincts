"""Host UI chrome maps — named click targets, hotkeys, catalog→inventory recipes.

Peer to ui_mode (mode classification) and household_object_force (useful-item
plans). Normalized client fractions only; never SendInput; execute_allowed=false.

Plans prefer catalogued hotkeys/KEY chords over mouse CLICK_TARGET whenever an
equivalent exists (HOTKEY_FIRST_WHEN_EQUIVALENT) for cooperative interop.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "ui-chrome.v1.json"
MAX_BYTES = 96_000
ALLOWED_MODES = frozenset({"LIVE", "BUY", "BUILD"})
INPUT_PREFERENCE = "HOTKEY_FIRST_WHEN_EQUIVALENT"


class UIChromeError(ValueError):
    pass


def _normalize_alias(text: str) -> str:
    return " ".join(str(text).strip().lower().replace("_", " ").replace("-", " ").split())


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise UIChromeError("UI_CHROME_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.ui-chrome/v1":
        raise UIChromeError("BAD_UI_CHROME_SCHEMA")
    if cfg.get("coordinate_space", {}).get("kind") != "NORMALIZED_CLIENT_FRACTION":
        raise UIChromeError("COORDINATE_SPACE_MUST_BE_NORMALIZED")
    if cfg.get("architecture", {}).get("selected") != "UI_CHROME_PEER_MAP":
        raise UIChromeError("UI_CHROME_ARCHITECTURE_DRIFT")
    pref = cfg.get("input_preference") or {}
    if pref.get("selected") != INPUT_PREFERENCE:
        raise UIChromeError("INPUT_PREFERENCE_MUST_BE_HOTKEY_FIRST")
    order = list(pref.get("order") or [])
    if order[:2] != ["HOTKEY", "KEY"]:
        raise UIChromeError("INPUT_PREFERENCE_ORDER_DRIFT")
    recipes = cfg.get("recipes") or {}
    deposit = recipes.get("catalog_to_household_inventory") or {}
    if deposit.get("execute_allowed_default") is not False:
        raise UIChromeError("CATALOG_DEPOSIT_MUST_DEFAULT_EXECUTE_FALSE")
    if "LOT_PLACEMENT" not in set(deposit.get("forbidden") or []):
        raise UIChromeError("CATALOG_DEPOSIT_MUST_FORBID_LOT_PLACEMENT")
    item = (cfg.get("catalog_items") or {}).get("a_ok_bloomer") or {}
    if item.get("search_term") != "A-OK":
        raise UIChromeError("AOK_SEARCH_TERM_REQUIRED")
    synonyms = {_normalize_alias(s) for s in (item.get("synonyms") or [])}
    if "wall shelf" not in synonyms:
        raise UIChromeError("AOK_WALL_SHELF_SYNONYM_REQUIRED")
    return cfg


def list_modes(cfg: Optional[dict] = None) -> list[str]:
    cfg = cfg or load_contract()
    return sorted(cfg["modes"])


def hotkeys_for_mode(mode: str, *, cfg: Optional[dict] = None) -> list[dict]:
    cfg = cfg or load_contract()
    if mode not in ALLOWED_MODES:
        raise UIChromeError("UNKNOWN_MODE")
    return [dict(row) for row in cfg["modes"][mode]["hotkeys"]]


def panels_for_mode(mode: str, *, cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    if mode not in ALLOWED_MODES:
        raise UIChromeError("UNKNOWN_MODE")
    return {k: dict(v) for k, v in cfg["modes"][mode]["panels"].items()}


def _resolve_shared(target_ref: str, cfg: dict) -> dict:
    shared = cfg.get("shared_targets") or {}
    if target_ref not in shared:
        raise UIChromeError("UNKNOWN_SHARED_TARGET:" + target_ref)
    return shared[target_ref]


def _hotkey_row(mode: str, hotkey_id: str, *, cfg: dict) -> dict:
    for row in cfg["modes"][mode]["hotkeys"]:
        if row.get("id") == hotkey_id:
            return dict(row)
    raise UIChromeError("UNKNOWN_HOTKEY_ID:" + hotkey_id)


def prefer_hotkey_step(step: Mapping, *, mode: str, cfg: Optional[dict] = None) -> dict:
    """Annotate or rewrite one plan step under HOTKEY_FIRST_WHEN_EQUIVALENT.

    KEY steps with a catalogued hotkey_id become channel HOTKEY. CLICK_TARGET
    steps with a preferred_hotkey rewrite to KEY. Otherwise clicks stay
    MOUSE_FALLBACK with an explicit reason — never silently dropped.
    """
    cfg = cfg or load_contract()
    if mode not in ALLOWED_MODES:
        raise UIChromeError("UNKNOWN_MODE")
    out = dict(step)
    op = out.get("op")
    if op == "KEY":
        hotkey_id = out.get("hotkey_id")
        if hotkey_id:
            row = _hotkey_row(mode, str(hotkey_id), cfg=cfg)
            out["chord"] = list(row.get("chord") or out.get("chord") or [])
            out["channel"] = "HOTKEY"
            out["hotkey_id"] = hotkey_id
        else:
            out["channel"] = "KEY"
        return out
    if op == "TYPE_TEXT":
        out["channel"] = "TYPE_TEXT"
        return out
    if op == "CLICK_TARGET":
        target_id = out.get("target")
        mode_targets = (cfg["modes"][mode].get("targets") or {})
        meta = mode_targets.get(str(target_id)) or {}
        preferred_hotkey = out.get("preferred_hotkey") or meta.get("preferred_hotkey")
        if preferred_hotkey:
            row = _hotkey_row(mode, str(preferred_hotkey), cfg=cfg)
            return {
                "op": "KEY",
                "chord": list(row.get("chord") or []),
                "hotkey_id": preferred_hotkey,
                "channel": "HOTKEY",
                "rewritten_from": "CLICK_TARGET",
                "target": target_id,
                "note": out.get("note") or "Hotkey preferred over mouse click",
            }
        out["channel"] = "MOUSE_FALLBACK"
        out["mouse_fallback_reason"] = (
            out.get("mouse_fallback_reason")
            or meta.get("mouse_fallback_reason")
            or "NO_CATALOGUED_HOTKEY_EQUIVALENT"
        )
        return out
    out["channel"] = out.get("channel") or "CONTROL"
    return out


def prefer_hotkey_steps(
    steps: Sequence[Mapping],
    *,
    mode: str,
    cfg: Optional[dict] = None,
) -> list[dict]:
    """Apply hotkey-first preference across a recipe step list for one mode."""
    cfg = cfg or load_contract()
    preferred: list[dict] = []
    for raw in steps:
        step = dict(raw)
        when_mode = step.get("when_mode")
        if when_mode is not None and when_mode != mode:
            continue
        preferred.append(prefer_hotkey_step(step, mode=mode, cfg=cfg))
    return preferred


def resolve_target(
    target_id: str,
    *,
    mode: str,
    profile: Optional[str] = None,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Resolve a named chrome target to normalized + optional absolute pixels."""
    cfg = cfg or load_contract()
    if mode not in ALLOWED_MODES:
        raise UIChromeError("UNKNOWN_MODE")
    profile = profile or cfg["default_profile"]
    if profile not in cfg["resolution_profiles"]:
        raise UIChromeError("UNKNOWN_RESOLUTION_PROFILE")
    mode_targets = cfg["modes"][mode].get("targets") or {}
    if target_id not in mode_targets:
        raise UIChromeError("TARGET_NOT_IN_MODE:" + target_id)
    ref = mode_targets[target_id]["ref"]
    shared = _resolve_shared(ref, cfg)
    if mode not in set(shared.get("modes") or []):
        raise UIChromeError("TARGET_MODE_FORBIDDEN")
    if shared.get("status") == "UNCALIBRATED_STUB":
        raise UIChromeError("TARGET_UNCALIBRATED")
    point = (shared.get("profiles") or {}).get(profile)
    if not isinstance(point, dict) or point.get("kind") != "point":
        raise UIChromeError("TARGET_PROFILE_MISSING")
    nx = float(point["nx"])
    ny = float(point["ny"])
    if not (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
        raise UIChromeError("NORMALIZED_OUT_OF_RANGE")
    out = {
        "schema": "betterinstincts.ui-chrome.target/v1",
        "target_id": target_id,
        "shared_ref": ref,
        "mode": mode,
        "profile": profile,
        "nx": nx,
        "ny": ny,
        "label": shared.get("label"),
        "status": shared.get("status"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }
    if client_width is not None or client_height is not None:
        if not isinstance(client_width, int) or not isinstance(client_height, int):
            raise UIChromeError("CLIENT_SIZE_REQUIRED_TOGETHER")
        if client_width < 320 or client_height < 240:
            raise UIChromeError("CLIENT_SIZE_TOO_SMALL")
        out["x"] = int(round(nx * client_width))
        out["y"] = int(round(ny * client_height))
        out["client_width"] = client_width
        out["client_height"] = client_height
    return out


def resolve_catalog_item(query: str, *, cfg: Optional[dict] = None) -> dict:
    """Resolve an item id or operator synonym to a catalog_items row.

    Operator correction: phrases like 'wall shelf' mean a_ok_bloomer — never a
    newly invented wall-shelf product outside the coveted-item list.
    """
    cfg = cfg or load_contract()
    items = cfg.get("catalog_items") or {}
    raw = str(query or "").strip()
    if not raw:
        raise UIChromeError("EMPTY_CATALOG_QUERY")
    if raw in items:
        row = dict(items[raw])
        row["item_id"] = raw
        row["resolved_via"] = "item_id"
        return row
    needle = _normalize_alias(raw)
    for item_id, row in items.items():
        aliases = [_normalize_alias(item_id), _normalize_alias(row.get("display_name") or "")]
        aliases.extend(_normalize_alias(s) for s in (row.get("synonyms") or []))
        aliases.append(_normalize_alias(row.get("search_term") or ""))
        if needle in aliases:
            out = dict(row)
            out["item_id"] = item_id
            out["resolved_via"] = "synonym" if needle != _normalize_alias(item_id) else "item_id"
            out["query"] = raw
            return out
    raise UIChromeError("UNKNOWN_CATALOG_ITEM_OR_SYNONYM")


def plan_catalog_to_inventory(
    item_id: str,
    *,
    mode: str,
    profile: Optional[str] = None,
    client_width: Optional[int] = None,
    client_height: Optional[int] = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Build an evaluate-only catalog→Household Inventory plan for a known item."""
    cfg = cfg or load_contract()
    if mode not in {"BUY", "BUILD"}:
        raise UIChromeError("CATALOG_DEPOSIT_REQUIRES_BUY_OR_BUILD")
    resolved = resolve_catalog_item(item_id, cfg=cfg)
    item_id = resolved["item_id"]
    item = resolved
    recipe_id = item.get("recipe")
    recipe = (cfg.get("recipes") or {}).get(recipe_id)
    if not isinstance(recipe, dict):
        raise UIChromeError("UNKNOWN_RECIPE")
    if mode not in set(recipe.get("required_modes") or []):
        raise UIChromeError("RECIPE_MODE_FORBIDDEN")
    if item.get("search_term") != "A-OK" and item_id == "a_ok_bloomer":
        raise UIChromeError("AOK_SEARCH_TERM_REQUIRED")
    profile = profile or cfg["default_profile"]
    steps_out: list[dict] = []
    for step in prefer_hotkey_steps(recipe["steps"], mode=mode, cfg=cfg):
        if step.get("op") == "TYPE_TEXT" and step.get("from_recipe_field") == "search_term":
            step["text"] = item["search_term"]
        if step.get("op") == "CLICK_TARGET":
            resolved = resolve_target(
                step["target"],
                mode=mode,
                profile=profile,
                client_width=client_width,
                client_height=client_height,
                cfg=cfg,
            )
            step["resolved"] = {
                "nx": resolved["nx"],
                "ny": resolved["ny"],
                "x": resolved.get("x"),
                "y": resolved.get("y"),
                "shared_ref": resolved["shared_ref"],
            }
        steps_out.append(step)
    return {
        "schema": "betterinstincts.ui-chrome.plan/v1",
        "recipe_id": recipe_id,
        "item_id": item_id,
        "display_name": item.get("display_name"),
        "search_term": item["search_term"],
        "mode": mode,
        "profile": profile,
        "destination": recipe.get("destination"),
        "forbidden": list(recipe.get("forbidden") or []),
        "mutating_action": recipe.get("mutating_action"),
        "funds_delta_simoleons": item.get("funds_delta_simoleons"),
        "input_preference": INPUT_PREFERENCE,
        "steps": steps_out,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def glossary_snapshot(cfg: Optional[dict] = None) -> dict:
    """Compact hotkey + panel glossary for docs/CLI."""
    cfg = cfg or load_contract()
    modes = {}
    for mode in list_modes(cfg):
        modes[mode] = {
            "shortcut_intent": cfg["modes"][mode]["shortcut_intent"],
            "hotkeys": hotkeys_for_mode(mode, cfg=cfg),
            "panels": panels_for_mode(mode, cfg=cfg),
            "targets": sorted((cfg["modes"][mode].get("targets") or {}).keys()),
        }
    return {
        "schema": "betterinstincts.ui-chrome.glossary/v1",
        "coordinate_space": cfg["coordinate_space"],
        "default_profile": cfg["default_profile"],
        "input_preference": cfg.get("input_preference"),
        "modes": modes,
        "catalog_items": {
            k: {
                "display_name": v.get("display_name"),
                "search_term": v.get("search_term"),
                "recipe": v.get("recipe"),
            }
            for k, v in (cfg.get("catalog_items") or {}).items()
        },
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }
