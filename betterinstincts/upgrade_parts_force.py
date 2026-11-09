"""Upgrade-parts spam-buy planner (Robot Salvage Parts and siblings).

P95 stack UPGRADE_PARTS_FORCE:
  computer — Live Order → Purchase Upgrade Parts → named part × quantity
  spawn    — testingcheats → Shift+click robotics workstation → Spawn Crafting Supplies

Library plans only; scripts/upgrade_parts_force.py is the CLI owner.
Never invents gsi_create_obj hex. Never authorizes BI-002 closure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "upgrade-parts-force.v1.json"
MAX_BYTES = 64_000


class UpgradePartsForceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise UpgradePartsForceError("UPGRADE_PARTS_FORCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.upgrade-parts-force/v1":
        raise UpgradePartsForceError("BAD_UPGRADE_PARTS_FORCE_SCHEMA")
    if (cfg.get("architecture") or {}).get("selected") != "UPGRADE_PARTS_FORCE":
        raise UpgradePartsForceError("UPGRADE_PARTS_ARCHITECTURE_DRIFT")
    catalog = cfg.get("part_catalog")
    if not isinstance(catalog, list) or not catalog:
        raise UpgradePartsForceError("PART_CATALOG_REQUIRED")
    paths = cfg.get("paths") or {}
    if "computer" not in paths or "spawn" not in paths:
        raise UpgradePartsForceError("COMPUTER_AND_SPAWN_PATHS_REQUIRED")
    qty = cfg.get("quantity") or {}
    if int(qty.get("min") or 0) < 1 or int(qty.get("max") or 0) < int(qty.get("min") or 0):
        raise UpgradePartsForceError("QUANTITY_BOUNDS_INVALID")
    forbidden = set(cfg.get("forbidden") or [])
    for needle in ("gsi_create_obj", "objects.gsi_create_obj", "hallucinated_instance_hex"):
        if needle not in forbidden:
            raise UpgradePartsForceError("FORBIDDEN_LIST_INCOMPLETE:" + needle)
    how = (cfg.get("how_to_buy") or {}).get("robot_salvage_parts") or {}
    if "Purchase Upgrade Parts" not in " ".join(how.get("steps") or []):
        raise UpgradePartsForceError("HOW_TO_BUY_MUST_NAME_PURCHASE_UPGRADE_PARTS")
    return cfg


def _normalize_alias(text: object) -> str:
    return " ".join(str(text or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _part_index(cfg: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in cfg["part_catalog"]:
        if not isinstance(row, Mapping):
            continue
        pid = str(row.get("id") or "").strip()
        if pid:
            out[pid] = dict(row)
    return out


def resolve_part(part_id: str, *, cfg: Optional[dict] = None) -> dict:
    """Resolve a catalog row by id or synonym (e.g. gardener bot parts)."""
    cfg = cfg or load_contract()
    index = _part_index(cfg)
    raw = str(part_id or "").strip()
    if not raw:
        raise UpgradePartsForceError("PART_ID_REQUIRED")
    if raw in index:
        out = dict(index[raw])
        out["resolved_via"] = "part_id"
        return out
    needle = _normalize_alias(raw)
    for pid, row in index.items():
        aliases = [_normalize_alias(pid), _normalize_alias(row.get("display_name") or "")]
        aliases.extend(_normalize_alias(s) for s in (row.get("synonyms") or []))
        if needle in aliases:
            out = dict(row)
            out["resolved_via"] = "synonym"
            out["query"] = raw
            return out
    raise UpgradePartsForceError("UNKNOWN_UPGRADE_PART:" + raw)


def catalog_snapshot(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    return {
        "schema": "betterinstincts.upgrade-parts-force.catalog/v1",
        "architecture": cfg["architecture"]["selected"],
        "parts": list(cfg["part_catalog"]),
        "paths": {
            key: {
                "id": val.get("id"),
                "display_name": val.get("display_name"),
                "required_mode": val.get("required_mode"),
                "requires_testingcheats": val.get("requires_testingcheats"),
                "destination": val.get("destination"),
            }
            for key, val in (cfg.get("paths") or {}).items()
        },
        "quantity": dict(cfg["quantity"]),
        "forbidden": list(cfg.get("forbidden") or []),
        "proof_ceiling": cfg["proof_ceiling"],
        "execute_allowed": False,
    }


def how_to_buy(part_id: str = "robot_salvage_parts", *, cfg: Optional[dict] = None) -> dict:
    """Operator-facing buy reminder (the forgotten Computer → Order path)."""
    cfg = cfg or load_contract()
    part = resolve_part(part_id, cfg=cfg)
    guide = (cfg.get("how_to_buy") or {}).get(part["id"])
    if not isinstance(guide, dict):
        guide = {
            "summary": (
                "Any computer → Order → Purchase Upgrade Parts → "
                + str(part.get("display_name") or part["id"])
            ),
            "steps": [
                "Select the Sim who needs the parts.",
                "Click any household computer.",
                "Choose Order → Purchase Upgrade Parts.",
                "Select " + str(part.get("display_name") or part["id"]) + " and confirm.",
                "Repeat to spam-buy additional units into pocket inventory.",
            ],
            "lab_bulk_alternative": (
                "testingcheats enabled true → Shift+click robotics workstation → "
                "Spawn Crafting Supplies"
            ),
            "not_this": list(cfg.get("forbidden") or [])[:6],
        }
    return {
        "schema": "betterinstincts.upgrade-parts-force.how-to-buy/v1",
        "part_id": part["id"],
        "display_name": part.get("display_name"),
        "summary": guide.get("summary"),
        "steps": list(guide.get("steps") or []),
        "lab_bulk_alternative": guide.get("lab_bulk_alternative"),
        "not_this": list(guide.get("not_this") or []),
        "tune_up_units_observed": part.get("tune_up_units_observed"),
        "default_spam_quantity": int(cfg["quantity"]["default"]),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def _clamp_quantity(quantity: Optional[int], cfg: dict) -> int:
    bounds = cfg["quantity"]
    if quantity is None:
        return int(bounds["default"])
    try:
        q = int(quantity)
    except (TypeError, ValueError) as exc:
        raise UpgradePartsForceError("INVALID_PARTS_QUANTITY") from exc
    if q < int(bounds["min"]) or q > int(bounds["max"]):
        raise UpgradePartsForceError("INVALID_PARTS_QUANTITY")
    return q


def plan_parts_force(
    *,
    part_id: str = "robot_salvage_parts",
    quantity: Optional[int] = None,
    path: Optional[str] = None,
    game_mode: str = "live",
    player_directed: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Build an evaluate-only spam-buy or spawn plan for a named upgrade part."""
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "schema": "betterinstincts.upgrade-parts-force.plan/v1",
            "state": "YIELD_TO_PLAYER",
            "steps": [],
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "reason": "PLAYER_DIRECTED",
        }

    part = resolve_part(part_id, cfg=cfg)
    path_key = (path or part.get("default_path") or "computer").strip().lower()
    allowed = {str(p).lower() for p in (part.get("allowed_paths") or [])}
    if path_key not in allowed:
        raise UpgradePartsForceError("PATH_NOT_ALLOWED_FOR_PART:" + path_key)
    path_cfg = (cfg.get("paths") or {}).get(path_key)
    if not isinstance(path_cfg, dict):
        raise UpgradePartsForceError("UNKNOWN_PARTS_PATH:" + path_key)

    qty = _clamp_quantity(quantity, cfg)
    mode = str(game_mode or "live").strip().upper()
    required = str(path_cfg.get("required_mode") or "LIVE").upper()
    if mode != required:
        fail = "COMPUTER_PURCHASE_REQUIRES_LIVE" if path_key == "computer" else "SPAWN_REQUIRES_LIVE"
        raise UpgradePartsForceError(fail)

    steps: list[dict] = []
    for raw in path_cfg.get("steps_template") or []:
        step = dict(raw)
        if step.get("op") == "SELECT_PART":
            step["part_id"] = part["id"]
            step["display_name"] = part.get("display_name")
            step["text"] = part.get("display_name")
        if step.get("op") == "TYPE_COMMAND":
            cmd = str(step.get("command") or "")
            if path_cfg.get("requires_testingcheats") and "testingcheats" not in cmd:
                raise UpgradePartsForceError("TESTINGCHEATS_REQUIRED_BEFORE_SPAWN")
        if step.get("op") == "REPEAT_PURCHASE":
            remaining = max(0, qty - 1)
            step["times"] = remaining
            step["note"] = "Re-open Purchase Upgrade Parts and buy again × " + str(remaining)
            if remaining == 0:
                continue
        steps.append(step)

    if path_cfg.get("requires_testingcheats"):
        cmds = [s.get("command") for s in steps if s.get("op") == "TYPE_COMMAND"]
        if not cmds or "testingcheats enabled true" not in cmds:
            raise UpgradePartsForceError("TESTINGCHEATS_REQUIRED_BEFORE_SPAWN")

    purchase_units = qty if path_key == "computer" else int(cfg["quantity"].get("spawn_bulk_hint") or 50)

    return {
        "schema": "betterinstincts.upgrade-parts-force.plan/v1",
        "state": "UPGRADE_PARTS_FORCE_PLAN_READY",
        "path": path_key,
        "path_id": path_cfg.get("id"),
        "part_id": part["id"],
        "display_name": part.get("display_name"),
        "quantity": qty,
        "purchase_units_planned": purchase_units,
        "game_mode": mode,
        "destination": path_cfg.get("destination"),
        "mutating_action": path_cfg.get("mutating_action"),
        "requires_testingcheats": bool(path_cfg.get("requires_testingcheats")),
        "forbidden": list(cfg.get("forbidden") or []),
        "steps": steps,
        "how_to_buy_summary": how_to_buy(part["id"], cfg=cfg).get("summary"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "interop": "screen_admit_only_no_computer_use_fallback",
        "not_bi002": True,
    }


def steps_to_operator_checklist(plan: Mapping) -> list[str]:
    """Flatten plan steps into a short human checklist (not SendInput)."""
    if plan.get("state") == "YIELD_TO_PLAYER":
        return ["Yield to player — no parts purchase while directed."]
    lines: list[str] = []
    for step in plan.get("steps") or []:
        op = step.get("op")
        if op == "REQUIRE_MODE":
            lines.append("Ensure game mode is " + str(step.get("mode") or "LIVE"))
        elif op == "REQUIRE_ACTIVE_SIM_SELECTION":
            lines.append("Select the Sim who needs the parts")
        elif op == "OBSERVE":
            lines.append("Observe cue: " + str(step.get("cue")))
        elif op == "CLICK_OBJECT":
            lines.append("Click " + str(step.get("target")))
        elif op == "SHIFT_CLICK_OBJECT":
            lines.append("Shift+click " + str(step.get("target")))
        elif op == "PIE_MENU":
            lines.append("Pie menu: " + str(step.get("choice")))
        elif op == "SELECT_PART":
            lines.append("Select part: " + str(step.get("display_name") or step.get("part_id")))
        elif op == "CONFIRM_PURCHASE":
            lines.append("Confirm purchase")
        elif op == "REPEAT_PURCHASE":
            lines.append("Repeat purchase × " + str(step.get("times") or 0))
        elif op == "OPEN_CONSOLE":
            lines.append("Open cheat console (Ctrl+Shift+C)")
        elif op == "TYPE_COMMAND":
            lines.append("Type: " + str(step.get("command")))
        elif op == "OPTIONAL_CLOSE_CONSOLE":
            lines.append("Optional: close console (Esc)")
        else:
            lines.append(str(op))
    return lines
