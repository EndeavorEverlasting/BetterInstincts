"""Deterministic, read-only hidden-object catalog discovery for The Sims 4.

This is a host *proposal*, not a SendInput adapter or gameplay certification.
Each actual UI step is subject to independent game-host scene/control admission.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "hidden-object-discovery.v1.json"
_PATCH = re.compile(r"^[0-9]+(?:\\.[0-9]+){3}$")
_QUERY = re.compile(r"^[\\w][\\w .'\\-]{0,63}$", re.UNICODE)
_PROOF = "OFFLINE_ADVISORY_NOT_GAME_INPUT_NOT_ITEM_INVENTORY_NOT_BI002_CERT"


class DiscoveryError(ValueError):
    """Invalid trusted contract or untrusted input, without game side effects."""


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64_000:
        raise DiscoveryError("CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.hidden-object-discovery/v1":
        raise DiscoveryError("CONTRACT_SCHEMA_INVALID")
    if cfg.get("host_execution") != "NEVER_FROM_THIS_MODULE":
        raise DiscoveryError("HOST_EXECUTION_MUST_BE_DISABLED")
    if cfg.get("ordered_console_lines") != ["testingcheats true", "bb.showhiddenobjects"]:
        raise DiscoveryError("CONSOLE_ORDER_INVALID")
    if cfg.get("optional_live_edit_line") != "bb.showliveeditobjects":
        raise DiscoveryError("LIVE_EDIT_LINE_INVALID")
    requirements = cfg.get("requirements") or {}
    if requirements.get("explicit_opt_in") is not True or requirements.get("unknowns") != "ABSTAIN":
        raise DiscoveryError("FAIL_CLOSED_CONTRACT_REQUIRED")
    if not {"clutter", "collectibles", "world", "landscape", "lighting", "all"}.issubset(
        cfg.get("search_contract", {}).get("classes", {})
    ):
        raise DiscoveryError("DISCOVERY_CLASSES_REQUIRED")
    return cfg


def _query_text(value: str) -> str:
    if not isinstance(value, str):
        raise DiscoveryError("INVALID_QUERY")
    value = value.strip()
    if not _QUERY.fullmatch(value) or value.lower() in {"buydebug", "testingcheats", "bb.showhiddenobjects"}:
        raise DiscoveryError("UNSAFE_QUERY")
    return value


def _abstain(reasons: list[str]) -> dict:
    return {
        "state": "ABSTAIN",
        "reasons": reasons,
        "dispatch_authorized": False,
        "steps": [],
        "proof_ceiling": _PROOF,
    }


def plan_discovery(
    observation: Mapping[str, object],
    *,
    category: str = "all",
    target: str | None = None,
    include_live_edit: bool = False,
    cfg: dict | None = None,
) -> dict:
    """Produce manual-only steps only for a positively attested host observation.

    A caller's fields are untrusted declarations, not independently verified UI
    evidence. A real host must reacquire the scene and control permit per step.
    """
    cfg = cfg or load_contract()
    if not isinstance(observation, Mapping):
        return _abstain(["OBSERVATION_MISSING"])
    classes = cfg["search_contract"]["classes"]
    if category not in classes:
        raise DiscoveryError("UNKNOWN_CATEGORY")
    if type(include_live_edit) is not bool:
        raise DiscoveryError("LIVE_EDIT_FLAG_MUST_BE_BOOLEAN")
    if target is not None:
        target = _query_text(target)

    reasons = []
    version = observation.get("exact_game_build")
    if not isinstance(version, str) or not _PATCH.fullmatch(version):
        reasons.append("UNKNOWN_EXACT_GAME_BUILD")
    platform = observation.get("platform")
    if platform not in cfg["platform_console_chords"]:
        reasons.append("UNKNOWN_PLATFORM")
    if observation.get("scene_id") not in ("live_mode", "build_buy"):
        reasons.append("WRONG_OR_UNKNOWN_SCENE")
    for cue in ("visual_cue_ref", "operator_cue_ref"):
        if not isinstance(observation.get(cue), str) or not str(observation[cue]).strip():
            reasons.append("MISSING_" + cue.upper())
    if observation.get("capture_quality") != "CONTENT_PRESENT" or observation.get("viewport") != "NORMAL":
        reasons.append("BAD_OR_UNKNOWN_VIEWPORT")
    if observation.get("save_attestation") != "OPERATOR_ATTESTED_DISPOSABLE_LAB":
        reasons.append("UNATTESTED_OR_PROTECTED_SAVE")
    if observation.get("player_explicit_opt_in") is not True:
        reasons.append("PLAYER_OPT_IN_REQUIRED")
    if observation.get("player_idle") is not True:
        reasons.append("PLAYER_ACTIVE_OR_UNKNOWN")
    if observation.get("host_control_lease") != "HOST_EXCLUSIVE":
        reasons.append("HOST_LEASE_NOT_VERIFIED")
    if observation.get("game_paused") is not True:
        reasons.append("GAME_NOT_CONFIRMED_PAUSED")
    if platform in ("playstation", "xbox") and observation.get("acknowledge_testingcheats_trophy_risk") is not True:
        reasons.append("CONSOLE_ACHIEVEMENT_ACK_REQUIRED")
    if reasons:
        return _abstain(reasons)

    lines = list(cfg["ordered_console_lines"])
    if include_live_edit:
        lines.append(cfg["optional_live_edit_line"])
    # Refuse accidentally combined or unexpected commands.
    if any("/" in s or "\\n" in s or s.lower() == "buydebug" for s in lines):
        raise DiscoveryError("INVALID_CONSOLE_LINE")
    steps = [
        {
            "step_id": "OPEN_CONSOLE",
            "manual_only": True,
            "chord": list(cfg["platform_console_chords"][platform]),
            "after": "OBSERVE_CONSOLE_VISIBLE",
        },
    ]
    steps += [
        {
            "step_id": "CONSOLE_LINE_" + str(i + 1),
            "manual_only": True,
            "command": line,
            "submit": "ENTER",
            "after": "OBSERVE_CONSOLE_STILL_RESPONSIVE",
        }
        for i, line in enumerate(lines)
    ]
    steps.extend([
        {"step_id": "CLOSE_CONSOLE", "manual_only": True, "after": "OBSERVE_CONSOLE_CLOSED"},
        {
            "step_id": "ENTER_OR_CONFIRM_BUILD_BUY",
            "manual_only": True,
            "hint": "Use the hammer-and-wrench icon, or the patch-verified Build shortcut; do not force F1.",
            "after": "OBSERVE_BUILD_BUY_CHROME_AND_CATALOG",
        },
        {
            "step_id": "SEARCH_DEBUG",
            "manual_only": True,
            "search_text": "debug",
            "after": "OBSERVE_VISIBLE_DEBUG_SUGGESTIONS",
        },
        {
            "step_id": "SELECT_DEBUG_SUGGESTION",
            "manual_only": True,
            "after": "OBSERVE_FILTERED_CATALOG",
        },
        {
            "step_id": "INSPECT_AND_FILTER",
            "manual_only": True,
            "category": category,
            "search_hints": list(classes[category]["search_hints"]),
            "target": target,
            "after": "OBSERVE_ITEM_LABEL_PACK_AND_PRICE_IN_CURRENT_BUILD",
        },
        {
            "step_id": "PLACEMENT_SEPARATE_APPROVAL",
            "manual_only": True,
            "after": "NO_PLACEMENT_UNLESS_PLAYER_APPROVES_EACH_ITEM",
        },
    ])
    return {
        "state": "DISCOVERY_PLAN_READY_NOT_AUTHORIZED",
        "dispatch_authorized": False,
        "host_executes": False,
        "game_build": version,
        "platform": platform,
        "save_scope": "OPERATOR_ATTESTED_DISPOSABLE_LAB",
        "category": category,
        "target": target,
        "include_live_edit": include_live_edit,
        "console_lines": lines,
        "one_command_per_line": True,
        "steps": steps,
        "existing_capability": "Curious Catalog",
        "next_gate": "LOCAL_HOST_REOBSERVE_EACH_STEP_AND_OPERATOR_APPROVAL",
        "item_availability": "UNKNOWN_UNTIL_OBSERVED",
        "free_item_claim": "UNKNOWN_UNTIL_PRICE_OBSERVED",
        "proof_ceiling": _PROOF,
    }


def review_catalog_entry(entry: Mapping[str, object]) -> dict:
    """Classify one reviewed, visible item; never infer free from the debug label."""
    if not isinstance(entry, Mapping):
        return {"state": "ENTRY_NOT_VERIFIED", "free": None}
    if entry.get("operator_reviewed") is not True or entry.get("result_visible") is not True:
        return {"state": "ENTRY_NOT_VERIFIED", "free": None}
    if not isinstance(entry.get("capture_ref"), str) or not entry["capture_ref"].strip():
        return {"state": "ENTRY_NOT_VERIFIED", "free": None}
    if not isinstance(entry.get("item_label"), str) or not entry["item_label"].strip():
        return {"state": "ENTRY_NOT_VERIFIED", "free": None}
    price = entry.get("price_simoleons")
    if type(price) is int and price >= 0:
        state = "OBSERVED_FREE_ITEM" if price == 0 else "OBSERVED_PRICED_ITEM"
        free = price == 0
    else:
        state, free = "OBSERVED_PRICE_UNKNOWN", None
    return {
        "state": state,
        "free": free,
        "price_simoleons": price if type(price) is int and price >= 0 else None,
        "item_label": entry["item_label"],
        "capture_ref": entry["capture_ref"],
        "proof_ceiling": "OPERATOR_REVIEWED_CATALOG_ENTRY_NOT_PURCHASE_OR_PLACEMENT",
    }
