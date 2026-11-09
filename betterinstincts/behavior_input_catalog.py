"""Canonical hotkey/cheat identity adapter for the opt-in behavior listener.

Only ids proven in existing BetterInstincts contracts qualify. No raw keys,
typed cheat arguments, player names, screenshots, input hooks or game actions.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from betterinstincts.ui_chrome import load_contract as ui_contract

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[^a-z0-9]+")


class BehaviorInputCatalogError(ValueError):
    pass


def _read_contract(name: str, schema: str) -> dict:
    path = ROOT / "contracts" / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 96_000:
        raise BehaviorInputCatalogError("CATALOG_FILE_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != schema:
        raise BehaviorInputCatalogError("CATALOG_SCHEMA_MISMATCH")
    return cfg


def _slug(command: str) -> str:
    if not isinstance(command, str) or not command.strip():
        raise BehaviorInputCatalogError("INVALID_CANONICAL_CHEAT")
    slug = SLUG.sub("_", command.lower()).strip("_")
    if not 2 <= len(slug) <= 64:
        raise BehaviorInputCatalogError("CANONICAL_CHEAT_ID_TOO_LONG")
    return slug


@lru_cache(maxsize=1)
def catalog() -> dict:
    """Derive ids from authoritative contracts, not independent command copies."""
    chrome = ui_contract()
    hotkeys = {
        mode: sorted({row["id"] for row in details["hotkeys"]})
        for mode, details in chrome["modes"].items()
    }
    hidden = _read_contract(
        "hidden-object-discovery.v1.json",
        "betterinstincts.hidden-object-discovery/v1",
    )
    force = _read_contract(
        "household-object-force.v1.json",
        "betterinstincts.household-object-force/v1",
    )
    funds = _read_contract("host-funds.v1.json", "betterinstincts.host-funds/v1")
    command_lines = [
        *hidden["ordered_console_lines"],
        hidden["optional_live_edit_line"],
        *force["elementary_unlock"]["player_lines"],
        *(row["career_cheat"] for row in force["useful_item_catalog"]
          if row.get("career_cheat")),
        funds["inject_sequence"]["activate_testing_cheats"],
        funds["inject_sequence"]["activate_testing_cheats_alias"],
        funds["inject_sequence"]["durable_additive_command"],
        funds["inject_sequence"]["set_funds_template"],
    ]
    cheats = sorted({_slug(line) for line in command_lines})
    if not hotkeys or not cheats:
        raise BehaviorInputCatalogError("EMPTY_INPUT_CATALOG")
    return {"hotkeys": hotkeys, "cheats": cheats,
            "catalog_owners": [
                "contracts/ui-chrome.v1.json",
                "contracts/hidden-object-discovery.v1.json",
                "contracts/household-object-force.v1.json",
                "contracts/host-funds.v1.json",
            ]}


def resolve_hotkey(mode: str, hotkey_id: str) -> str:
    """Record a known named *invocation*, not an inferred mode change."""
    if not isinstance(mode, str) or not isinstance(hotkey_id, str):
        raise BehaviorInputCatalogError("INVALID_HOTKEY_REFERENCE")
    choices = catalog()["hotkeys"]
    if mode not in choices or hotkey_id not in choices[mode]:
        raise BehaviorInputCatalogError("HOTKEY_NOT_IN_MODE_CATALOG")
    return "hotkey:" + mode.lower() + ":" + hotkey_id.lower()


def resolve_cheat(cheat_id: str) -> str:
    """Match a canonical command family; never accept typed command text."""
    if not isinstance(cheat_id, str) or cheat_id not in catalog()["cheats"]:
        raise BehaviorInputCatalogError("CHEAT_NOT_IN_CANONICAL_CATALOG")
    return "cheat:" + cheat_id
