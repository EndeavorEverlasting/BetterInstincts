"""Resolve player-facing names from a private, process-bound save inventory."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from time import time
import unicodedata

from betterinstincts.installation_profiles import HOUSEHOLD_ID
from betterinstincts.player_learning import ACTOR
from betterinstincts.save_policy import PATCH_RE, REF_RE, SAVE_ID_RE, SavePolicyError

SCHEMA = "betterinstincts.startup-save-catalog/v1"
SLOT = re.compile(r"Slot_[a-fA-F0-9]{8}", re.IGNORECASE)
PROTECTED_SLOT = "slot_00000007"


def name_key(name):
    if (not isinstance(name, str) or not 1 <= len(name) <= 120
            or any(unicodedata.category(c).startswith("C") for c in name)):
        raise SavePolicyError("INVALID_GAME_VISIBLE_NAME")
    key = " ".join(unicodedata.normalize("NFKC", name).split()).casefold()
    if not key:
        raise SavePolicyError("INVALID_GAME_VISIBLE_NAME")
    return key


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


@dataclass(frozen=True)
class Household:
    id: str
    name: str
    members: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Save:
    id: str
    slot: str
    name: str
    last_played: str | None
    households: tuple[Household, ...]


def read_catalog(process, packet):
    now = time()
    stamp = packet.get("observed_at_unix") if isinstance(packet, dict) else None
    if (not isinstance(packet, dict)
            or type(stamp) not in (int, float) or not now - 120 <= stamp <= now or packet.get("schema") != SCHEMA
            or packet.get("process") != asdict(process)
            or not _matches(PATCH_RE, process.game_version)
            or packet.get("source") != "IN_GAME_SAVE_INVENTORY"
            or packet.get("scene") != "MAIN_MENU"
            or packet.get("inventory_complete") is not True
            or not _matches(REF_RE, packet.get("capture_ref"))):
        raise SavePolicyError("CURRENT_GAME_SAVE_CATALOG_REQUIRED")
    rows = packet.get("saves")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 150:
        raise SavePolicyError("INVALID_SAVE_CATALOG_COUNT")
    saves = {}
    slots = set()
    for row in rows:
        if (not isinstance(row, dict) or not _matches(SAVE_ID_RE, row.get("save_id"))
                or row["save_id"] in saves or not _matches(SLOT, row.get("slot"))
                or row["slot"].casefold() in slots
                or not isinstance(row.get("households"), list) or len(row["households"]) > 150):
            raise SavePolicyError("SAVE_CATALOG_IDENTITY_UNVERIFIED")
        name_key(row.get("save_name"))
        households = {}
        for entry in row["households"]:
            household = _read_household(entry)
            if household.id in households:
                raise SavePolicyError("SAVE_CATALOG_HOUSEHOLD_DUPLICATED")
            households[household.id] = household
        saves[row["save_id"]] = Save(row["save_id"], row["slot"], row["save_name"],
                                     row.get("last_played_utc"), tuple(households.values()))
        slots.add(row["slot"].casefold())
    return saves


def _read_household(entry):
    if (not isinstance(entry, dict) or not _matches(HOUSEHOLD_ID, entry.get("household_id"))
            or not isinstance(entry.get("members"), list) or not 1 <= len(entry["members"]) <= 16):
        raise SavePolicyError("SAVE_CATALOG_HOUSEHOLD_UNVERIFIED")
    name_key(entry.get("household_name"))
    members = {}
    for item in entry["members"]:
        if (not isinstance(item, dict) or not _matches(ACTOR, item.get("sim_id"))
                or item["sim_id"] in members):
            raise SavePolicyError("SAVE_CATALOG_ROSTER_UNVERIFIED")
        name_key(item.get("sim_name"))
        members[item["sim_id"]] = item["sim_name"]
    return Household(entry["household_id"], entry["household_name"], tuple(members.items()))


def household_choices(saves):
    labels = {}
    for save in saves.values():
        for household in save.households:
            labels.setdefault(household.id, household.name)
    return labels


def matching_households(saves, household_name, preferred_id):
    if household_name is None:
        choices = set(household_choices(saves))
        return choices & {preferred_id} if preferred_id is not None else choices
    expected = name_key(household_name)
    return {
        household.id for save in saves.values() for household in save.households
        if name_key(household.name) == expected
    }


def matching_saves(saves, household_id, minimum, required):
    return {
        save.id: household
        for save in saves.values() for household in save.households
        if (household.id == household_id and save.slot.casefold() != PROTECTED_SLOT
            and len(household.members) >= minimum
            and all(sum(name_key(name) == member for _, name in household.members) == 1
                    for member in required))
    }
