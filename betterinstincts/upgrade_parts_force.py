"""Household DIY parts budget + upgrade-parts spam-buy planner.

P95 stack HOUSEHOLD_DIY_PARTS_BUDGET (evolves UPGRADE_PARTS_FORCE):
  preferred — spawn: testingcheats → Shift+click robotics workstation → Spawn Crafting Supplies
  fallback  — phone or computer Order → Purchase Upgrade Parts × quantity
  household — Space-traverse every observed portrait (N) and stock pocket inventory
  certify   — machine-readable per-member × part MET/SHORT/UNKNOWN receipt

Library plans only; scripts/upgrade_parts_force.py is the CLI owner.
Never invents gsi_create_obj hex. Never authorizes BI-002 closure.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "upgrade-parts-force.v1.json"
CERT_ROOT = ROOT / "dist" / "diy-parts-budget"
MAX_BYTES = 96_000


class UpgradePartsForceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise UpgradePartsForceError("UPGRADE_PARTS_FORCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.upgrade-parts-force/v1":
        raise UpgradePartsForceError("BAD_UPGRADE_PARTS_FORCE_SCHEMA")
    if (cfg.get("architecture") or {}).get("selected") != "HOUSEHOLD_DIY_PARTS_BUDGET":
        raise UpgradePartsForceError("HOUSEHOLD_DIY_PARTS_BUDGET_REQUIRED")
    catalog = cfg.get("part_catalog")
    if not isinstance(catalog, list) or not catalog:
        raise UpgradePartsForceError("PART_CATALOG_REQUIRED")
    paths = cfg.get("paths") or {}
    for required in ("spawn", "phone", "computer"):
        if required not in paths:
            raise UpgradePartsForceError("PARTS_PATH_REQUIRED:" + required)
    qty = cfg.get("quantity") or {}
    if int(qty.get("min") or 0) < 1 or int(qty.get("max") or 0) < int(qty.get("min") or 0):
        raise UpgradePartsForceError("QUANTITY_BOUNDS_INVALID")
    budget = cfg.get("household_budget") or {}
    if budget.get("selected") != "PER_SIM_POCKET_STOCK":
        raise UpgradePartsForceError("PER_SIM_POCKET_STOCK_REQUIRED")
    if budget.get("destination") != "sim_pocket_inventory":
        raise UpgradePartsForceError("POCKET_INVENTORY_REQUIRED")
    if budget.get("forbid_household_inventory") is not True:
        raise UpgradePartsForceError("FORBID_HOUSEHOLD_INVENTORY_REQUIRED")
    preferred = list(budget.get("preferred_acquisition_order") or [])
    if preferred[:1] != ["spawn"]:
        raise UpgradePartsForceError("SPAWN_MUST_BE_PREFERRED_ACQUISITION")
    if "buy_mode_debug_catalog" in preferred:
        raise UpgradePartsForceError("BUY_MODE_NOT_PREFERRED_ACQUISITION")
    kit = list(budget.get("diy_kit_part_ids") or [])
    if not kit:
        raise UpgradePartsForceError("DIY_KIT_INCOMPLETE")
    index = {str(row.get("id")): row for row in catalog if isinstance(row, Mapping)}
    for pid in kit:
        if pid not in index:
            raise UpgradePartsForceError("DIY_KIT_UNKNOWN_PART:" + str(pid))
    forbidden = set(cfg.get("forbidden") or [])
    for needle in (
        "gsi_create_obj",
        "objects.gsi_create_obj",
        "hallucinated_instance_hex",
        "ea_online_connect",
        "CONNECT_BUTTON",
        "CONNECT_ONLINE",
        "force_sims_online",
    ):
        if needle not in forbidden:
            raise UpgradePartsForceError("FORBIDDEN_LIST_INCOMPLETE:" + needle)
    offline = cfg.get("offline_install") or {}
    if offline.get("forbid_ea_online_connect") is not True:
        raise UpgradePartsForceError("FORBID_EA_ONLINE_CONNECT_REQUIRED")
    if offline.get("connection_required_dialog") != "STAY_OFFLINE_ONLY":
        raise UpgradePartsForceError("STAY_OFFLINE_ONLY_REQUIRED")
    how = (cfg.get("how_to_buy") or {}).get("robot_salvage_parts") or {}
    if "Purchase Upgrade Parts" not in " ".join(how.get("steps") or []):
        raise UpgradePartsForceError("HOW_TO_BUY_MUST_NAME_PURCHASE_UPGRADE_PARTS")
    if int(cfg.get("version") or 0) >= 3:
        menu = cfg.get("computer_purchase_menu") or {}
        observed = menu.get("part_ids") or []
        expected = {
            "common_upgrade_parts", "electronic_upgrade_parts",
            "kitchen_upgrade_parts", "plumbing_upgrade_parts",
            "robot_salvage_parts",
        }
        if not isinstance(observed, list) or len(observed) != 5 or set(observed) != expected:
            raise UpgradePartsForceError("COMPUTER_MENU_PARTS_INCOMPLETE")
        if menu.get("session_authority") != "EXPLICIT_USER_COMMAND_THEN_COOPERATIVE_QUEUE; NO_AUTORUN":
            raise UpgradePartsForceError("COMPUTER_MENU_AUTORUN_FORBIDDEN")
        if menu.get("fixed_menu_depth") is not None:
            raise UpgradePartsForceError("COMPUTER_MENU_FIXED_DEPTH_FORBIDDEN")
        if not 1 <= int(menu.get("max_menu_pages") or 0) <= 32:
            raise UpgradePartsForceError("COMPUTER_MENU_DEPTH_BOUND_REQUIRED")
        computer_steps = (paths.get("computer") or {}).get("steps_template") or []
        if not any(step.get("op") == "DISCOVER_NESTED_MENU" for step in computer_steps):
            raise UpgradePartsForceError("COMPUTER_MENU_SEMANTIC_DISCOVERY_REQUIRED")
        if any(x not in set(menu.get("prohibited_effects") or []) for x in (
            "BLUETOOTH_SERVICE_CHANGE", "OS_SERVICE_CHANGE",
            "DRIVER_ADAPTER_CHANGE", "PAIRING_CHANGE",
            "INPUT_PREFERENCE_CHANGE", "UAC_CHANGE", "EA_CONNECT",
        )):
            raise UpgradePartsForceError("COMPUTER_MENU_OS_BOUNDARY_REQUIRED")
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


def diy_kit_parts(cfg: Optional[dict] = None) -> list[dict]:
    cfg = cfg or load_contract()
    index = _part_index(cfg)
    kit_ids = list((cfg.get("household_budget") or {}).get("diy_kit_part_ids") or [])
    return [dict(index[pid]) for pid in kit_ids]


def catalog_snapshot(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    budget = cfg["household_budget"]
    return {
        "schema": "betterinstincts.upgrade-parts-force.catalog/v1",
        "architecture": cfg["architecture"]["selected"],
        "version": cfg.get("version"),
        "parts": list(cfg["part_catalog"]),
        "diy_kit_part_ids": list(budget.get("diy_kit_part_ids") or []),
        "preferred_acquisition_order": list(budget.get("preferred_acquisition_order") or []),
        "paths": {
            key: {
                "id": val.get("id"),
                "display_name": val.get("display_name"),
                "required_mode": val.get("required_mode"),
                "requires_testingcheats": val.get("requires_testingcheats"),
                "destination": val.get("destination"),
                "scalability_rank": val.get("scalability_rank"),
            }
            for key, val in (cfg.get("paths") or {}).items()
        },
        "quantity": dict(cfg["quantity"]),
        "computer_purchase_menu": {k: v for k, v in (cfg.get("computer_purchase_menu") or {}).items() if k in ("part_ids", "target_label", "evidence_source", "max_menu_pages")},
        "forbidden": list(cfg.get("forbidden") or []),
        "proof_ceiling": cfg["proof_ceiling"],
        "execute_allowed": False,
    }


def budget_snapshot(cfg: Optional[dict] = None) -> dict:
    """Targets for always-ready DIY builds across any household size N."""
    cfg = cfg or load_contract()
    budget = cfg["household_budget"]
    target = int(budget.get("target_per_part") or cfg["quantity"].get("budget_target_default") or 20)
    rows = []
    for part in diy_kit_parts(cfg):
        rows.append(
            {
                "part_id": part["id"],
                "display_name": part.get("display_name"),
                "target": int(part.get("budget_target") or target),
                "default_path": part.get("default_path"),
                "computer_buyable": bool(part.get("computer_buyable")),
                "destination": "sim_pocket_inventory",
            }
        )
    return {
        "schema": "betterinstincts.diy-parts-budget.snapshot/v1",
        "diy_kit_id": budget.get("diy_kit_id"),
        "preferred_acquisition_order": list(budget.get("preferred_acquisition_order") or []),
        "destination": budget.get("destination"),
        "target_per_part_default": target,
        "parts": rows,
        "household_traverse": dict(budget.get("household_traverse") or {}),
        "cert_schema": (budget.get("cert") or {}).get("schema"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def how_to_buy(part_id: str = "robot_salvage_parts", *, cfg: Optional[dict] = None) -> dict:
    """Operator-facing buy reminder (phone/computer Order path)."""
    cfg = cfg or load_contract()
    part = resolve_part(part_id, cfg=cfg)
    guide = (cfg.get("how_to_buy") or {}).get(part["id"])
    if part["id"] == "eco_upgrade_parts":
        guide = {
            "summary": "Eco Lifestyle Fabricator → Fabricate → Fabricated Eco-Upgrade Part",
            "steps": [
                "Verify Eco Lifestyle and a Fabricator are present.",
                "Observe at least 15 bits and 10 pieces for each fabrication attempt.",
                "Select Fabricate then the exact observed Eco-Upgrade Part recipe.",
                "Wait for successful crafting and attest the selected Sim pocket inventory.",
            ],
            "lab_bulk_alternative": "Not a normal computer Order picker purchase",
            "not_this": ["COMPUTER_ECO_PARTS_NOT_OBSERVED", "CRAFT_NOT_INSTANT"],
        }
    if not isinstance(guide, dict):
        guide = {
            "summary": (
                "Computer interactions → discover Purchase Upgrade Parts → "
                + str(part.get("display_name") or part["id"])
            ),
            "steps": [
                "Select the Sim who needs the parts.",
                "Click an observed computer/laptop while Live Mode is paused.",
                "Discover currently visible nested menu labels until Purchase Upgrade Parts appears.",
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


def _path_live_fail(path_key: str) -> str:
    if path_key == "phone":
        return "PHONE_PURCHASE_REQUIRES_LIVE"
    if path_key == "spawn":
        return "SPAWN_REQUIRES_LIVE"
    return "COMPUTER_PURCHASE_REQUIRES_LIVE"


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
    path_key = (path or part.get("default_path") or "spawn").strip().lower()
    if path_key in {"buy", "buy_mode", "build_buy", "debug_catalog"}:
        raise UpgradePartsForceError("BUY_MODE_NOT_PREFERRED_ACQUISITION")
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
        raise UpgradePartsForceError(_path_live_fail(path_key))

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

    for step in steps:
        choice = str(step.get("choice") or "").strip().lower()
        never = {str(x).strip().lower() for x in (step.get("never") or [])}
        if choice in {"connect", "connect online"} or "connect" in never and choice == "connect":
            raise UpgradePartsForceError("EA_ONLINE_CONNECT_FORBIDDEN")
        if any(tok in {"connect", "connect_button", "connect_online"} for tok in never):
            # Stay Offline path is required; Connect tokens may only appear in never[].
            pass
        blob = json.dumps(step).lower()
        if '"choice": "connect"' in blob or '"text": "connect"' in blob:
            raise UpgradePartsForceError("EA_ONLINE_CONNECT_FORBIDDEN")

    if path_key == "spawn":
        purchase_units = int(cfg["quantity"].get("spawn_bulk_hint") or 50)
    else:
        purchase_units = qty

    return {
        "schema": "betterinstincts.upgrade-parts-force.plan/v1",
        "state": "UPGRADE_PARTS_FORCE_PLAN_READY",
        "path": path_key,
        "path_id": path_cfg.get("id"),
        "part_id": part["id"],
        "display_name": part.get("display_name"),
        "quantity": qty,
        "purchase_units_planned": purchase_units,
        "offline_install": dict(cfg.get("offline_install") or {}),
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


def plan_household_parts_budget(
    *,
    members: int,
    path: Optional[str] = None,
    quantity: Optional[int] = None,
    game_mode: str = "live",
    player_directed: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Plan DIY kit stocking for every observed household member (N).

    ``members`` is the exact Live portrait count. Preferred path defaults to
    spawn (one bulk action per Sim). Each member receives pocket stock — never
    shared Household Inventory.
    """
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "schema": "betterinstincts.diy-parts-budget.household-plan/v1",
            "state": "YIELD_TO_PLAYER",
            "steps": [],
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "reason": "PLAYER_DIRECTED",
        }

    budget = cfg["household_budget"]
    ht = budget.get("household_traverse") or {}
    min_m = int(ht.get("min_members") or 1)
    max_m = int(ht.get("sanity_max_members") or ht.get("max_members") or 100)
    if isinstance(members, bool):
        raise UpgradePartsForceError("INVALID_HOUSEHOLD_MEMBER_COUNT")
    count = int(members)
    if count < min_m or count > max_m:
        raise UpgradePartsForceError("INVALID_HOUSEHOLD_MEMBER_COUNT")

    preferred = list(budget.get("preferred_acquisition_order") or ["spawn"])
    path_key = (path or preferred[0]).strip().lower()
    if path_key in {"buy", "buy_mode", "build_buy", "debug_catalog"}:
        raise UpgradePartsForceError("BUY_MODE_NOT_PREFERRED_ACQUISITION")
    if path_key not in (cfg.get("paths") or {}):
        raise UpgradePartsForceError("UNKNOWN_PARTS_PATH:" + path_key)

    qty = _clamp_quantity(quantity if quantity is not None else budget.get("target_per_part"), cfg)
    kit = diy_kit_parts(cfg)
    member_plans: list[dict] = []
    steps: list[dict] = [
        {
            "op": "REQUIRE_MODE",
            "mode": "LIVE",
            "fail": _path_live_fail(path_key),
        },
        {
            "op": "REQUIRE_OBSERVED_HOUSEHOLD_COUNT",
            "members": count,
            "note": "N must match Live portrait strip; do not invent size",
        },
    ]

    for slot in range(count):
        member_key = "member_" + str(slot)
        acquire = plan_parts_force(
            part_id=kit[0]["id"] if path_key != "spawn" else "robot_salvage_parts",
            quantity=qty,
            path=path_key,
            game_mode=game_mode,
            cfg=cfg,
        )
        # Spawn stocks the whole DIY kit in one pie choice; Order path notes kit fill.
        member_row = {
            "member_slot": slot,
            "member_key": member_key,
            "destination": "sim_pocket_inventory",
            "path": path_key,
            "diy_kit_part_ids": [p["id"] for p in kit],
            "target_per_part": qty,
            "acquire_plan_state": acquire.get("state"),
            "acquire_steps": list(acquire.get("steps") or []),
        }
        member_plans.append(member_row)
        steps.append(
            {
                "op": "REQUIRE_ACTIVE_SIM_SELECTION",
                "member_slot": slot,
                "member_key": member_key,
            }
        )
        steps.extend(dict(s, member_slot=slot) for s in (acquire.get("steps") or []))
        steps.append(
            {
                "op": "OBSERVE_POCKET_INVENTORY_DIY_KIT",
                "member_slot": slot,
                "part_ids": [p["id"] for p in kit],
                "target_per_part": qty,
                "fail": "DIY_KIT_STOCK_UNPROVEN",
            }
        )
        if slot < count - 1:
            steps.append(
                {
                    "op": "KEY",
                    "chord": list(ht.get("next_member_chord") or ["SPACE"]),
                    "hotkey_id": "SELECT_NEXT_HOUSEHOLD_SIM",
                    "note": "Space to next portrait; stock each Sim independently",
                }
            )

    return {
        "schema": "betterinstincts.diy-parts-budget.household-plan/v1",
        "state": "HOUSEHOLD_DIY_PARTS_BUDGET_PLAN_READY",
        "architecture": "HOUSEHOLD_DIY_PARTS_BUDGET",
        "household_members": count,
        "path": path_key,
        "preferred_acquisition_order": preferred,
        "diy_kit_id": budget.get("diy_kit_id"),
        "diy_kit_part_ids": [p["id"] for p in kit],
        "target_per_part": qty,
        "destination": "sim_pocket_inventory",
        "member_plans": member_plans,
        "steps": steps,
        "forbidden": list(cfg.get("forbidden") or []),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "cert_next": (
            "python -m scripts.upgrade_parts_force certify --members "
            + str(count)
            + " --observations <attested.json>"
        ),
        "not_bi002": True,
        "interop": "screen_admit_only_no_computer_use_fallback",
    }


def score_part_stock(observed: Optional[int], target: int) -> str:
    if observed is None:
        return "UNKNOWN"
    try:
        count = int(observed)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if count < 0:
        return "UNKNOWN"
    if count >= int(target):
        return "MET"
    return "SHORT"


def evaluate_diy_parts_cert(
    *,
    members: int,
    observations: Sequence[Mapping],
    cfg: Optional[dict] = None,
) -> dict:
    """Build a machine-readable cert from attested per-member pocket counts.

    ``observations`` entries: {member_slot: int, parts: {part_id: observed_count|null}}
    Missing slots/parts stay UNKNOWN — never inferred MET.
    """
    cfg = cfg or load_contract()
    budget = cfg["household_budget"]
    ht = budget.get("household_traverse") or {}
    min_m = int(ht.get("min_members") or 1)
    max_m = int(ht.get("sanity_max_members") or 100)
    count = int(members)
    if isinstance(members, bool) or count < min_m or count > max_m:
        raise UpgradePartsForceError("INVALID_HOUSEHOLD_MEMBER_COUNT")
    if not isinstance(observations, Sequence) or not observations:
        raise UpgradePartsForceError("CERT_MEMBER_ROWS_REQUIRED")

    kit = diy_kit_parts(cfg)
    default_target = int(budget.get("target_per_part") or 20)
    by_slot: dict[int, Mapping] = {}
    for row in observations:
        if not isinstance(row, Mapping):
            continue
        try:
            slot = int(row.get("member_slot"))
        except (TypeError, ValueError) as exc:
            raise UpgradePartsForceError("CERT_MEMBER_SLOT_INVALID") from exc
        by_slot[slot] = row

    member_rows: list[dict] = []
    met_members = 0
    for slot in range(count):
        raw = by_slot.get(slot) or {}
        parts_obs = raw.get("parts") if isinstance(raw.get("parts"), Mapping) else {}
        part_rows = []
        member_met = True
        for part in kit:
            pid = part["id"]
            target = int(part.get("budget_target") or default_target)
            observed = parts_obs.get(pid)
            if observed is None and pid in parts_obs:
                observed = parts_obs[pid]
            state = score_part_stock(observed if observed is not None else None, target)
            if state != "MET":
                member_met = False
            part_rows.append(
                {
                    "part_id": pid,
                    "display_name": part.get("display_name"),
                    "target": target,
                    "observed": observed if isinstance(observed, int) else None,
                    "state": state,
                }
            )
        if member_met and part_rows:
            met_members += 1
        member_rows.append(
            {
                "member_slot": slot,
                "member_key": "member_" + str(slot),
                "destination": "sim_pocket_inventory",
                "parts": part_rows,
                "member_state": "MET" if member_met else (
                    "PARTIAL" if any(p["state"] != "UNKNOWN" for p in part_rows) else "UNKNOWN"
                ),
            }
        )

    if met_members == count and count > 0:
        aggregate = "ALL_MEMBERS_MET_REVIEW_REQUIRED"
    elif met_members > 0 or any(
        p["state"] in {"MET", "SHORT"} for m in member_rows for p in m["parts"]
    ):
        aggregate = "PARTIAL"
    else:
        aggregate = "UNPROVEN"

    cert_meta = budget.get("cert") or {}
    return {
        "schema": cert_meta.get("schema") or "betterinstincts.diy-parts-budget.cert/v1",
        "architecture": "HOUSEHOLD_DIY_PARTS_BUDGET",
        "household_members": count,
        "diy_kit_id": budget.get("diy_kit_id"),
        "diy_kit_part_ids": [p["id"] for p in kit],
        "members": member_rows,
        "members_met": met_members,
        "aggregate_state": aggregate,
        "destination": "sim_pocket_inventory",
        "execute_allowed": False,
        "certified": False,
        "proof_ceiling": cert_meta.get("proof_ceiling") or cfg["proof_ceiling"],
        "not_bi002": True,
        "note": (
            "ALL_MEMBERS_MET_REVIEW_REQUIRED still needs independent review; "
            "plans and unattested counts never auto-certify."
        ),
    }


def cert_run_dir(run_id: str, *, root: Path = CERT_ROOT) -> Path:
    rid = str(run_id or "").strip()
    if not rid or "/" in rid or "\\" in rid or ".." in rid or len(rid) > 80:
        raise UpgradePartsForceError("INVALID_CERT_RUN_ID")
    return Path(root) / rid


def record_part_observation(
    *,
    run_id: str,
    member_slot: int,
    part_id: str,
    observed_count: Optional[int],
    members: Optional[int] = None,
    root: Path = CERT_ROOT,
    cfg: Optional[dict] = None,
) -> dict:
    """Append/update one attested pocket count and refresh cert status."""
    cfg = cfg or load_contract()
    part = resolve_part(part_id, cfg=cfg)
    path = cert_run_dir(run_id, root=root)
    path.mkdir(parents=True, exist_ok=True)
    store = path / "observations.json"
    if store.is_file():
        data = json.loads(store.read_text(encoding="utf-8"))
    else:
        data = {
            "schema": "betterinstincts.diy-parts-budget.observations/v1",
            "run_id": run_id,
            "household_members": int(members) if members is not None else None,
            "members": {},
        }
    if members is not None:
        data["household_members"] = int(members)
    if data.get("household_members") is None:
        raise UpgradePartsForceError("HOUSEHOLD_MEMBERS_REQUIRED_FOR_RECORD")
    key = str(int(member_slot))
    row = data.setdefault("members", {}).setdefault(key, {"member_slot": int(member_slot), "parts": {}})
    row["parts"][part["id"]] = observed_count
    row["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    store.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    observations = []
    for slot in range(int(data["household_members"])):
        m = data["members"].get(str(slot)) or {"member_slot": slot, "parts": {}}
        observations.append({"member_slot": slot, "parts": dict(m.get("parts") or {})})
    cert = evaluate_diy_parts_cert(
        members=int(data["household_members"]),
        observations=observations,
        cfg=cfg,
    )
    cert["run_id"] = run_id
    (path / "cert.json").write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return cert


def status_cert(run_id: str, *, root: Path = CERT_ROOT) -> dict:
    path = cert_run_dir(run_id, root=root) / "cert.json"
    if not path.is_file():
        raise UpgradePartsForceError("CERT_STATUS_MISSING:" + run_id)
    return json.loads(path.read_text(encoding="utf-8"))


def steps_to_operator_checklist(plan: Mapping) -> list[str]:
    """Flatten plan steps into a short human checklist (not SendInput)."""
    if plan.get("state") == "YIELD_TO_PLAYER":
        return ["Yield to player — no parts purchase while directed."]
    lines: list[str] = []
    for step in plan.get("steps") or []:
        op = step.get("op")
        if op == "REQUIRE_MODE":
            lines.append("Ensure game mode is " + str(step.get("mode") or "LIVE"))
        elif op == "REQUIRE_OBSERVED_HOUSEHOLD_COUNT":
            lines.append("Confirm household portraits N=" + str(step.get("members")))
        elif op == "REQUIRE_ACTIVE_SIM_SELECTION":
            slot = step.get("member_slot")
            suffix = " (member " + str(slot) + ")" if slot is not None else ""
            lines.append("Select the Sim who needs the parts" + suffix)
        elif op == "OBSERVE":
            lines.append("Observe cue: " + str(step.get("cue")))
        elif op == "OBSERVE_POCKET_INVENTORY_DIY_KIT":
            lines.append(
                "Attest pocket DIY kit for member "
                + str(step.get("member_slot"))
                + " (≥"
                + str(step.get("target_per_part"))
                + " each)"
            )
        elif op == "CLICK_OBJECT":
            lines.append("Click " + str(step.get("target")))
        elif op == "SHIFT_CLICK_OBJECT":
            lines.append("Shift+click " + str(step.get("target")))
        elif op == "OPEN_PHONE":
            lines.append("Open phone")
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
        elif op == "KEY":
            lines.append("Press " + "+".join(str(k) for k in (step.get("chord") or [])))
        else:
            lines.append(str(op))
    return lines

# Canonical cross-source acquisition routing. Preserve the existing DIY-kit
# budget planner; these routines are observational decisions only.
def acquisition_source_catalog(*, cfg: Optional[dict] = None) -> dict:
    """Typed sources, action semantics, and observed-menu contract."""
    cfg = cfg or load_contract()
    route = cfg.get("acquisition_routing")
    if not isinstance(route, dict) or route.get("schema") != "betterinstincts.household-acquisition-routes/v1":
        raise UpgradePartsForceError("ACQUISITION_ROUTING_CONTRACT_MISSING")
    return {
        "schema": route["schema"],
        "route_catalog": dict(route["route_catalog"]),
        "effect_classes": dict(route["effect_classes"]),
        "menu_model": dict(route["menu_model"]),
        "source_evidence": list(route.get("source_evidence") or []),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def _normalize_menu_label(value: object) -> str:
    """Normalize punctuation differences, never use substring matching."""
    import re
    value = str(value or "").strip().casefold().replace("\u2026", "...")
    return " ".join(re.sub(r"[^\w\s]", " ", value).split())


def next_observed_menu_choice(
    *,
    visible_options: Sequence[str],
    desired_choice: str,
    visited_signatures: Sequence[str] = (),
    cfg: Optional[dict] = None,
) -> dict:
    """One pure next-choice decision; NEVER repeatedly click an unseen option.

    Call again with a *fresh observed menu* after every More Choices click.
    Signatures prevent loops and support variable page depth (including zero).
    """
    settings = acquisition_source_catalog(cfg=cfg)["menu_model"]
    limit = int(settings["max_page_explorations"])
    if not isinstance(visible_options, (list, tuple)) or not visible_options:
        return {"state": "BLOCKED", "reason": "MENU_OPTIONS_NOT_OBSERVED", "execute_allowed": False}
    if not isinstance(visited_signatures, (list, tuple)):
        raise UpgradePartsForceError("INVALID_MENU_HISTORY")
    if len(visible_options) > 64 or len(visited_signatures) > limit:
        return {"state": "BLOCKED", "reason": "MENU_BOUND_EXCEEDED", "execute_allowed": False}
    choices = [_normalize_menu_label(opt) for opt in visible_options]
    if not all(choices):
        return {"state": "BLOCKED", "reason": "EMPTY_OBSERVED_LABEL", "execute_allowed": False}
    signature = "|".join(sorted(choices))
    if signature in visited_signatures:
        return {"state": "BLOCKED", "reason": "MENU_LOOP_DETECTED", "execute_allowed": False}
    history = list(visited_signatures) + [signature]
    needle = _normalize_menu_label(desired_choice)
    if not needle:
        raise UpgradePartsForceError("MENU_GOAL_REQUIRED")
    matches = [i for i, name in enumerate(choices) if name == needle]
    if len(matches) > 1:
        return {"state": "BLOCKED", "reason": "DUPLICATE_VISIBLE_TARGET", "execute_allowed": False}
    if len(matches) == 1:
        return {
            "state": "CHOICE_OBSERVED",
            "choice": visible_options[matches[0]],
            "next_history": history,
            "page_depth": len(visited_signatures),
            "execute_allowed": False,
            "requires_fresh_effect_admission": True,
        }
    more = _normalize_menu_label(settings["candidate_pagination_label"])
    more_matches = [i for i, name in enumerate(choices) if name == more]
    if not more_matches:
        return {"state": "BLOCKED", "reason": "TARGET_NOT_IN_OBSERVED_MENU", "execute_allowed": False}
    if len(more_matches) != 1 or len(history) >= limit:
        return {"state": "BLOCKED", "reason": "MENU_PAGE_LIMIT_OR_AMBIGUITY", "execute_allowed": False}
    return {
        "state": "MORE_CHOICES_OBSERVED",
        "choice": visible_options[more_matches[0]],
        "next_history": history,
        "page_depth": len(visited_signatures),
        "execute_allowed": False,
        "requires_fresh_effect_admission": True,
    }


def _resolve_acquisition_id(item: str, cfg: dict) -> str:
    catalog = acquisition_source_catalog(cfg=cfg)["route_catalog"]
    name = _normalize_menu_label(item)
    if not name:
        raise UpgradePartsForceError("ACQUISITION_ITEM_REQUIRED")
    local_aliases = {
        "generator fuel": "generator_fuel",
        "fuel": "generator_fuel",
        "recycled fuel": "generator_fuel",
        "insect biofuel filled can": "insect_biofuel_filled_can",
        "biofuel filled can": "insect_biofuel_filled_can",
        "insect biofuel": "insect_biofuel_filled_can",
        "biofuel": "insect_biofuel_filled_can",
    }
    candidate = local_aliases.get(name)
    if candidate is None:
        try:
            candidate = resolve_part(item, cfg=cfg)["id"]
        except UpgradePartsForceError as exc:
            raise UpgradePartsForceError("UNKNOWN_ACQUISITION_ITEM:" + str(item)) from exc
    if candidate not in catalog:
        raise UpgradePartsForceError("NO_VERIFIED_SOURCE_ROUTE:" + candidate)
    return candidate


def _observed_portraits(portraits: Sequence[Mapping]) -> list[dict]:
    if not isinstance(portraits, (list, tuple)) or not 1 <= len(portraits) <= 100:
        raise UpgradePartsForceError("OBSERVED_PORTRAIT_ROSTER_REQUIRED")
    result: list[dict] = []
    keys: set[str] = set()
    slots: set[int] = set()
    for row in portraits:
        if not isinstance(row, Mapping) or row.get("observed") is not True:
            raise UpgradePartsForceError("PORTRAIT_NOT_ATTESTED")
        slot = row.get("slot")
        identity = row.get("portrait_id")
        if type(slot) is not int or slot < 0 or slot >= 100:
            raise UpgradePartsForceError("INVALID_PORTRAIT_SLOT")
        if not isinstance(identity, str) or not identity.strip() or len(identity) > 128:
            raise UpgradePartsForceError("PORTRAIT_ID_REQUIRED")
        if slot in slots or identity in keys:
            raise UpgradePartsForceError("DUPLICATE_PORTRAIT")
        slots.add(slot)
        keys.add(identity)
        result.append({"slot": slot, "portrait_id": identity})
    return result


def plan_acquisition_routes(
    *,
    portraits: Sequence[Mapping],
    requests: Sequence[Mapping],
    selected_slots: Optional[Sequence[int]] = None,
    packs_observed: Optional[Sequence[str]] = None,
    player_directed: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Actor-agnostic, read-only call stack for computer and non-computer sources.

    Portrait identities and DLC/stock observations come from the caller,
    NEVER from names, static pixel coordinates, or a fixed example household.
    """
    cfg = cfg or load_contract()
    route = acquisition_source_catalog(cfg=cfg)
    if player_directed:
        return {
            "schema": "betterinstincts.household-acquisition-plan/v1",
            "state": "YIELD_TO_PLAYER", "steps": [], "execute_allowed": False,
            "not_bi002": True, "proof_ceiling": cfg["proof_ceiling"],
        }
    actor_roster = _observed_portraits(portraits)
    if selected_slots is not None:
        if not isinstance(selected_slots, (tuple, list)) or not selected_slots:
            raise UpgradePartsForceError("SELECTED_SLOTS_REQUIRED")
        if any(type(v) is not int for v in selected_slots) or len(set(selected_slots)) != len(selected_slots):
            raise UpgradePartsForceError("INVALID_SELECTED_SLOTS")
        chosen = [p for p in actor_roster if p["slot"] in selected_slots]
        if len(chosen) != len(selected_slots):
            raise UpgradePartsForceError("SELECTED_PORTRAIT_NOT_OBSERVED")
    else:
        chosen = actor_roster
    if not isinstance(requests, (list, tuple)) or not 1 <= len(requests) <= 32:
        raise UpgradePartsForceError("ACQUISITION_REQUESTS_REQUIRED")
    items = []
    for row in requests:
        if not isinstance(row, Mapping):
            raise UpgradePartsForceError("ACQUISITION_REQUEST_INVALID")
        item_id = _resolve_acquisition_id(str(row.get("item") or ""), cfg)
        qty = _clamp_quantity(row.get("quantity", 1), cfg)
        entry = dict(route["route_catalog"][item_id])
        items.append({"item_id": item_id, "quantity": qty, **entry})
    if packs_observed is not None:
        if not isinstance(packs_observed, (tuple, list)) or not all(isinstance(p, str) for p in packs_observed):
            raise UpgradePartsForceError("PACK_OBSERVATIONS_INVALID")
        installed = {p.casefold() for p in packs_observed}
        for entry in items:
            if entry["pack"].casefold() not in installed and entry["pack"] != "base":
                raise UpgradePartsForceError("PACK_NOT_OBSERVED:" + entry["pack"])
    steps: list[dict] = [{
        "op": "REQUIRE_PAUSED_INSIDE_LOT",
        "reason": "Preserve PR163 observed computer purchase gate",
    }, {
        "op": "REQUIRE_LIVE_MODE_AND_FRESH_SCENE",
        "reason": "No Build/Buy, no camera/desktop lease bypass",
    }, {
        "op": "REQUIRE_CURRENT_OBSERVED_PORTRAIT_SET",
        "count": len(actor_roster),
        "portrait_ids": [p["portrait_id"] for p in actor_roster],
    }]
    for actor in chosen:
        slot, portrait_id = actor["slot"], actor["portrait_id"]
        steps.append({
            "op": "SELECT_OBSERVED_PORTRAIT",
            "slot": slot, "portrait_id": portrait_id,
            "method": "CURRENT_ATTESTED_PORTRAIT_HITBOX",
            "note": "No Sim names, house roster, or pixel coordinates assumed",
        })
        steps.append({"op": "VERIFY_ACTIVE_PORTRAIT", "portrait_id": portrait_id})
        computer_picker_open = False
        for item in items:
            source = item["source"]
            identity = {"slot": slot, "portrait_id": portrait_id, "item_id": item["item_id"]}
            steps.append({
                "op": "REQUIRE_FRESH_PLAYER_SCENE_EFFECT_ADMISSION",
                **identity,
                "fail": "PLAYER_OR_SCENE_CHANGED",
            })
            if item["pack"] != "base":
                steps.append({"op": "REQUIRE_PACK_OBSERVED", "pack": item["pack"], **identity})
            if source == "computer_order":
                if not computer_picker_open:
                    steps += [
                        {"op": "OBSERVE_SOURCE_OBJECT", "object": "computer_or_laptop", **identity},
                        {"op": "LEFT_CLICK_OBSERVED_COMPUTER", "requires_sim_at_computer": False, **identity},
                        {"op": "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES",
                         "choice": "Order", "max_pages": route["menu_model"]["max_page_explorations"], **identity},
                        {"op": "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES",
                         "choice": "Purchase Upgrade Parts",
                         "max_pages": route["menu_model"]["max_page_explorations"], **identity},
                        {"op": "OPEN_OBSERVED_PURCHASE_PICKER", **identity},
                    ]
                    computer_picker_open = True
                steps.extend([
                    {"op": "REQUIRE_VISIBLE_PURCHASE_ITEM", "text": item["item_id"].replace("_", " ").title(),
                     **identity, "fail": "PART_ROW_NOT_OBSERVED"},
                    {"op": "SET_OBSERVED_PICKER_QUANTITY_OR_REPEAT", "quantity": item["quantity"],
                     **identity, "fail": "BULK_CONTROLS_NOT_OBSERVED"},
                    {"op": "REQUIRE_SPEND_AUTHORIZATION_AND_FRESH_PRICE_FUNDS_CAP_POCKET_BASELINE",
                     **identity, "fail": "PURCHASE_SPENDING_OR_BASELINE_UNPROVEN"},
                    {"op": "CONFIRM_PURCHASE_WITH_FRESH_ADMISSION", **identity,
                     "effect_class": item["action_effect"]},
                    {"op": "OBSERVE_FUNDS_AND_POCKET_DELTA", **identity,
                     "quantity": item["quantity"], "fail": "PURCHASE_UNPROVEN"},
                    {"op": "IF_PICKER_CLOSED_REOBSERVE_AND_REOPEN_DOMAIN",
                     "choice": "Purchase Upgrade Parts", **identity},
                ])
            else:
                computer_picker_open = False
                source_ops = {
                    "eco_fabricator": [
                        {"op": "OBSERVE_SOURCE_OBJECT", "object": "fabricator"},
                        {"op": "OBSERVE_HOUSEHOLD_BITS_PIECES", "bits_per_attempt": 15, "pieces_per_attempt": 10},
                        {"op": "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES", "choice": "Fabricate"},
                        {"op": "SELECT_OBSERVED_RECIPE", "recipe": "Fabricated Eco-Upgrade Part"},
                        {"op": "QUEUE_CRAFT_AND_WAIT_FOR_RESULT", "failure_possible": True},
                        {"op": "OBSERVE_COMPLETION_AND_POCKET_DELTA", "fail": "ECO_PART_UNPROVEN"},
                    ],
                    "insect_farm": [
                        {"op": "OBSERVE_SOURCE_OBJECT", "object": "insect_farm"},
                        {"op": "REQUIRE_FARM_READY_AND_HEALTHY"},
                        {"op": "SELECT_OBSERVED_COLLECT_BIO_FUEL"},
                        {"op": "WAIT_FOR_COLLECTION_AND_OBSERVE_POCKET", "fail": "BIOFUEL_UNPROVEN"},
                    ],
                    "recycler_generator": [
                        {"op": "OBSERVE_GENERATOR_AND_RESOURCE_BALANCE"},
                        {"op": "IF_SHORT_OBSERVE_RECYCLER_AND_APPROVED_RECYCLABLES",
                         "forbidden": "UNAPPROVED_ITEM_RECYCLE"},
                        {"op": "OBSERVE_GENERATOR_REFILL_AFFORDANCE"},
                        {"op": "REFILL_AFTER_PLAYER_ADMISSION_AND_OBSERVE_FUEL_LEVEL",
                         "fail": "GENERATOR_FUEL_UNPROVEN"},
                    ],
                }
                if source not in source_ops:
                    raise UpgradePartsForceError("ACQUISITION_SOURCE_UNSUPPORTED:" + source)
                steps += [dict(s, **identity, effect_class=item["action_effect"]) for s in source_ops[source]]
    return {
        "schema": "betterinstincts.household-acquisition-plan/v1",
        "state": "OBSERVATIONAL_ACQUISITION_PLAN_READY",
        "portraits_observed": len(actor_roster),
        "portraits_selected": [a["portrait_id"] for a in chosen],
        "requests": items,
        "steps": steps,
        "action_classification": [
            {"item_id": p["item_id"], "class": p["action_effect"],
             "is_instant_proved": False} for p in items
        ],
        "order_entry": "LEFT_CLICK_COMPUTER__ORDER__RESOLVE_PAGED_DOMAIN__PICKER__ITERATE_ITEMS",
        "menu_choices_are_observational": True,
        "no_fixed_more_choices_count": True,
        "execute_allowed": False,
        "not_bi002": True,
        "interop": "screen_admit_only_no_computer_use_fallback",
        "proof_ceiling": cfg["proof_ceiling"],
    }


def plan_computer_order_domain(
    *,
    portraits: Sequence[Mapping],
    domain: str,
    item_labels: Sequence[str],
    selected_slots: Optional[Sequence[int]] = None,
    player_directed: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Generic Order journey when the domain and items are *goals*, not assumed UI.

    The interactive adapter must use next_observed_menu_choice for each page
    and only dispatch per-effect after fresh player, scene, portrait, and
    shared-desktop admission. This function NEVER issues purchases.
    """
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "schema": "betterinstincts.observed-computer-order.plan/v1",
            "state": "YIELD_TO_PLAYER", "steps": [], "execute_allowed": False,
            "not_bi002": True,
        }
    people = _observed_portraits(portraits)
    wanted = _normalize_menu_label(domain)
    if not wanted or wanted in {_normalize_menu_label("Order"), _normalize_menu_label("More Choices")}:
        raise UpgradePartsForceError("SPECIFIC_ORDER_DOMAIN_REQUIRED")
    if not isinstance(item_labels, (list, tuple)) or not 1 <= len(item_labels) <= 32:
        raise UpgradePartsForceError("ORDER_ITEMS_REQUIRED")
    if any(not isinstance(v, str) or not _normalize_menu_label(v) or len(v) > 120 for v in item_labels):
        raise UpgradePartsForceError("ORDER_ITEM_LABEL_INVALID")
    if selected_slots is not None:
        if not isinstance(selected_slots, (list, tuple)) or not selected_slots or any(type(s) is not int for s in selected_slots):
            raise UpgradePartsForceError("SELECTED_SLOTS_REQUIRED")
        if len(set(selected_slots)) != len(selected_slots):
            raise UpgradePartsForceError("DUPLICATE_SELECTED_SLOTS")
        chosen = [p for p in people if p["slot"] in selected_slots]
        if len(chosen) != len(selected_slots):
            raise UpgradePartsForceError("SELECTED_PORTRAIT_NOT_OBSERVED")
    else:
        chosen = people
    model = acquisition_source_catalog(cfg=cfg)["menu_model"]
    steps = [{"op": "REQUIRE_PAUSED_INSIDE_LOT"},
             {"op": "REQUIRE_LIVE_MODE_AND_FRESH_SCENE"},
             {"op": "REQUIRE_CURRENT_OBSERVED_PORTRAIT_SET",
              "portrait_ids": [p["portrait_id"] for p in people]}]
    for person in chosen:
        actor = {"slot": person["slot"], "portrait_id": person["portrait_id"]}
        steps.extend([
            {"op": "SELECT_OBSERVED_PORTRAIT", **actor,
             "method": "CURRENT_ATTESTED_PORTRAIT_HITBOX"},
            {"op": "VERIFY_ACTIVE_PORTRAIT", **actor},
            {"op": "OBSERVE_SOURCE_OBJECT", "object": "computer_or_laptop", **actor},
            {"op": "REQUIRE_FRESH_PLAYER_SCENE_EFFECT_ADMISSION", **actor},
            {"op": "LEFT_CLICK_OBSERVED_COMPUTER", "requires_sim_at_computer": False, **actor},
            {"op": "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES", "choice": "Order",
             "max_pages": model["max_page_explorations"], **actor},
            {"op": "FIND_VISIBLE_CHOICE_OR_BOUNDED_MORE_CHOICES", "choice": domain,
             "max_pages": model["max_page_explorations"], **actor},
            {"op": "OPEN_OBSERVED_PURCHASE_PICKER", "domain": domain, **actor},
        ])
        for item in item_labels:
            steps.extend([
                {"op": "REQUIRE_VISIBLE_PURCHASE_ITEM", "text": item, **actor},
                {"op": "CONFIRM_ONLY_AFTER_FRESH_ADMISSION_AND_SPEND_APPROVAL",
                 "text": item, "effect_class": "UNKNOWN", **actor},
                {"op": "OBSERVE_ACTUAL_DESTINATION_AND_CURRENCY_CHANGE",
                 "text": item, "fail": "PURCHASE_UNPROVEN", **actor},
                {"op": "IF_PICKER_CLOSED_REOBSERVE_AND_REOPEN_DOMAIN",
                 "choice": domain, **actor},
            ])
    return {
        "schema": "betterinstincts.observed-computer-order.plan/v1",
        "state": "OBSERVED_ORDER_DOMAIN_PLAN_READY",
        "domain_goal": domain,
        "item_goals": list(item_labels),
        "portraits_observed": len(people),
        "portraits_selected": [p["portrait_id"] for p in chosen],
        "steps": steps,
        "bounded_choice_resolver": "next_observed_menu_choice",
        "known_item_availability": "NOT_PROVEN_UNTIL_VISIBLE",
        "purchase_proof": "INVENTORY_OR_RESOURCE_AND_FUNDS_DELTA_REQUIRED",
        "execute_allowed": False,
        "interop": "screen_admit_only_no_computer_use_fallback",
        "not_bi002": True,
        "proof_ceiling": cfg["proof_ceiling"],
    }
