"""Household Object Force — durable useful-item catalog into any household.

Library plans only. bb.showhiddenobjects is ELEMENTARY for catalog/hidden list
items; Better BuildBuy is optional UX and never a substitute. Never emits
hallucinated gsi_create_obj hex IDs. SendInput stays with the host CLI/adapter.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "household-object-force.v1.json"
MAX_BYTES = 96_000


class HouseholdObjectForceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise HouseholdObjectForceError("HOUSEHOLD_OBJECT_FORCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.household-object-force/v1":
        raise HouseholdObjectForceError("BAD_HOUSEHOLD_OBJECT_FORCE_SCHEMA")
    unlock = cfg.get("elementary_unlock") or {}
    if unlock.get("show_hidden_objects") != "bb.showhiddenobjects":
        raise HouseholdObjectForceError("ELEMENTARY_SHOW_HIDDEN_OBJECTS_REQUIRED")
    if unlock.get("one_command_per_line") is not True:
        raise HouseholdObjectForceError("ONE_COMMAND_PER_LINE_REQUIRED")
    if list(unlock.get("player_lines") or []) != [
        "testingcheats true",
        "bb.showhiddenobjects",
    ]:
        raise HouseholdObjectForceError("ELEMENTARY_PLAYER_LINES_REQUIRED")
    forbidden = set(unlock.get("forbidden_typable_forms") or [])
    for needle in ("buydebug", "gsi_create_obj", "objects.gsi_create_obj"):
        if needle not in forbidden:
            raise HouseholdObjectForceError("FORBIDDEN_FORMS_INCOMPLETE:" + needle)
    ux = cfg.get("optional_catalog_ux") or {}
    if ux.get("never_replaces_elementary_unlock") is not True:
        raise HouseholdObjectForceError("BBB_MUST_NEVER_REPLACE_ELEMENTARY_UNLOCK")
    if ux.get("required") is True:
        raise HouseholdObjectForceError("BBB_MUST_REMAIN_OPTIONAL")
    catalog = cfg.get("useful_item_catalog")
    if not isinstance(catalog, list) or len(catalog) < 6:
        raise HouseholdObjectForceError("USEFUL_ITEM_CATALOG_REQUIRED")
    for row in catalog:
        if not isinstance(row, dict) or not row.get("id") or not row.get("delivery"):
            raise HouseholdObjectForceError("CATALOG_ROW_INVALID")
        if row.get("delivery") == "catalog_search" and row.get("requires_elementary_unlock") is not True:
            raise HouseholdObjectForceError("CATALOG_SEARCH_MUST_REQUIRE_ELEMENTARY_UNLOCK:" + str(row.get("id")))
    always = set(cfg.get("forbidden_always") or [])
    for needle in (
        "HALLUCINATED_INSTANCE_HEX",
        "SUBSTITUTE_BBB_FOR_SHOW_HIDDEN_OBJECTS",
        "SKIP_ELEMENTARY_UNLOCK_FOR_CATALOG_PATH",
        "PERSONAL_POCKET_FOR_LARGE_OBJECT",
    ):
        if needle not in always:
            raise HouseholdObjectForceError("FORBIDDEN_ALWAYS_INCOMPLETE:" + needle)
    return cfg


def reject_forbidden_console(raw: str) -> None:
    text = (raw or "").strip().lower()
    if not text:
        return
    if "/" in text:
        raise HouseholdObjectForceError("SLASH_JOINED_CONSOLE_LINE_FORBIDDEN")
    if text == "buydebug" or "buydebug" in text.split():
        raise HouseholdObjectForceError("BUYDEBUG_NICKNAME_NOT_A_COMMAND")
    if "gsi_create_obj" in text:
        raise HouseholdObjectForceError("GSI_CREATE_OBJ_FORBIDDEN")


def useful_item_catalog(
    *,
    include_optional: bool = False,
    delivery: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> list[dict]:
    cfg = cfg or load_contract()
    rows = []
    for row in cfg["useful_item_catalog"]:
        if row.get("optional") and not include_optional:
            continue
        if delivery and row.get("delivery") != delivery:
            continue
        rows.append(dict(row))
    return rows


def resolve_items(
    item_ids: Sequence[str] | str | None = None,
    *,
    include_optional: bool = False,
    cfg: Optional[dict] = None,
) -> list[dict]:
    cfg = cfg or load_contract()
    by_id = {str(r["id"]): r for r in cfg["useful_item_catalog"]}
    if item_ids is None or item_ids == "all" or item_ids == ["all"]:
        return useful_item_catalog(include_optional=include_optional, cfg=cfg)
    if isinstance(item_ids, str):
        raw_ids = [part.strip() for part in item_ids.split(",") if part.strip()]
    else:
        raw_ids = [str(x).strip() for x in item_ids if str(x).strip()]
    if not raw_ids:
        raise HouseholdObjectForceError("ITEM_IDS_REQUIRED")
    out = []
    for iid in raw_ids:
        if iid == "all":
            return useful_item_catalog(include_optional=include_optional, cfg=cfg)
        row = by_id.get(iid)
        if row is None:
            raise HouseholdObjectForceError("UNKNOWN_ITEM_ID:" + iid)
        out.append(dict(row))
    return out


def elementary_unlock_steps(cfg: Optional[dict] = None) -> list[dict]:
    cfg = cfg or load_contract()
    unlock = cfg["elementary_unlock"]
    steps = [
        {
            "step": "OPEN_CHEAT_CONSOLE",
            "chord": list(unlock["open_console_chord"]),
            "label": unlock["open_console_chord_label"],
            "required": True,
        }
    ]
    for line in unlock["player_lines"]:
        reject_forbidden_console(line)
        steps.append({
            "step": "CONSOLE_LINE",
            "command": line,
            "required": True,
            "one_command_per_line": True,
        })
    steps.append({
        "step": "ELEMENTARY_UNLOCK_ASSERTED",
        "show_hidden_objects": "bb.showhiddenobjects",
        "note": "Elementary for catalog/hidden list items; BBB is not a substitute.",
        "required": True,
    })
    return steps


def _career_promote_steps(row: Mapping) -> list[dict]:
    cheat = str(row["career_cheat"])
    reject_forbidden_console(cheat)
    target = int(row["target_level"])
    return [
        {
            "step": "CAREER_PROMOTE_LOOP",
            "item_id": row["id"],
            "display_name": row["display_name"],
            "command": cheat,
            "repeat_until_level": target,
            "branch": row.get("branch"),
            "destination": row.get("destination", "HOUSEHOLD_INVENTORY"),
            "note": "Repeat promote until reward deposits into Household Inventory; observe UI, do not invent ACK.",
            "required": True,
        }
    ]


def _catalog_search_steps(row: Mapping, *, elementary_already: bool) -> list[dict]:
    if not elementary_already:
        raise HouseholdObjectForceError("ELEMENTARY_UNLOCK_REQUIRED:" + str(row["id"]))
    terms = list(row.get("search_terms") or [])
    if not terms:
        raise HouseholdObjectForceError("SEARCH_TERMS_REQUIRED:" + str(row["id"]))
    return [
        {
            "step": "ENTER_BUILD_BUY_OBSERVED",
            "item_id": row["id"],
            "required": True,
            "note": "Confirm Build/Buy chrome independently; do not infer from keystroke alone.",
        },
        {
            "step": "CATALOG_SEARCH",
            "item_id": row["id"],
            "display_name": row["display_name"],
            "search_terms": terms,
            "destination": row.get("destination", "LOT_PLACEMENT"),
            "optional_ux": row.get("optional_ux"),
            "optional_ux_role": "OPTIONAL_CATALOG_UX_ONLY_AFTER_ELEMENTARY_UNLOCK",
            "required": True,
        },
    ]


def plan_force(
    *,
    item_ids: Sequence[str] | str | None = "all",
    include_optional: bool = False,
    player_directed: bool = False,
    skip_elementary_unlock: bool = False,
    substitute_bbb_for_unlock: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Return ordered library steps. Does not touch the game."""
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "next_gate": "YIELD_TO_PLAYER",
            "steps": [],
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if substitute_bbb_for_unlock:
        raise HouseholdObjectForceError("SUBSTITUTE_BBB_FOR_SHOW_HIDDEN_OBJECTS")

    items = resolve_items(item_ids, include_optional=include_optional, cfg=cfg)
    needs_unlock = any(bool(r.get("requires_elementary_unlock")) for r in items)
    if needs_unlock and skip_elementary_unlock:
        raise HouseholdObjectForceError("ELEMENTARY_UNLOCK_REQUIRED")

    steps: list[dict] = [
        {
            "step": "REQUIRE_FOREGROUND_SIMS",
            "required": True,
            "note": "Soft focus only; never force mode switch while operator builds.",
        }
    ]
    elementary_done = False
    if needs_unlock:
        steps.extend(elementary_unlock_steps(cfg))
        elementary_done = True

    for row in items:
        dest = str(row.get("destination") or "")
        if row.get("large_object") and dest == "PERSONAL_POCKET":
            raise HouseholdObjectForceError("PERSONAL_POCKET_FORBIDDEN:" + str(row["id"]))
        if dest == "PERSONAL_POCKET" and row.get("large_object"):
            raise HouseholdObjectForceError("PERSONAL_POCKET_FORBIDDEN:" + str(row["id"]))
        delivery = row.get("delivery")
        if delivery == "career_promote":
            steps.extend(_career_promote_steps(row))
        elif delivery == "catalog_search":
            steps.extend(_catalog_search_steps(row, elementary_already=elementary_done))
        else:
            raise HouseholdObjectForceError("UNKNOWN_DELIVERY:" + str(delivery))

    return {
        "state": "HOUSEHOLD_OBJECT_FORCE_PLANNED",
        "items": [{"id": r["id"], "display_name": r["display_name"], "delivery": r["delivery"]} for r in items],
        "elementary_unlock_applied": elementary_done,
        "optional_catalog_ux": cfg.get("optional_catalog_ux"),
        "steps": steps,
        "forbidden": list(cfg.get("forbidden_always") or []),
        "inventory_rules": cfg.get("inventory_rules"),
        "execute_allowed": False,
        "manual_only": True,
        "proof_ceiling": cfg["proof_ceiling"],
        "commands": cfg.get("activation", {}).get("cli"),
    }


def steps_to_commands(plan: Mapping) -> list[str]:
    cmds: list[str] = []
    for step in plan.get("steps") or []:
        if not isinstance(step, dict):
            continue
        cmd = step.get("command")
        if isinstance(cmd, str) and cmd.strip():
            reject_forbidden_console(cmd)
            cmds.append(cmd.strip())
    return cmds


def catalog_summary(*, include_optional: bool = False, cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    rows = useful_item_catalog(include_optional=include_optional, cfg=cfg)
    return {
        "schema": cfg["schema"],
        "version": cfg["version"],
        "count": len(rows),
        "elementary_unlock": "bb.showhiddenobjects",
        "bbb_role": "OPTIONAL_CATALOG_UX_ONLY",
        "items": [
            {
                "id": r["id"],
                "display_name": r["display_name"],
                "delivery": r["delivery"],
                "requires_elementary_unlock": bool(r.get("requires_elementary_unlock")),
                "destination": r.get("destination"),
                "optional": bool(r.get("optional")),
            }
            for r in rows
        ],
        "proof_ceiling": cfg["proof_ceiling"],
    }
