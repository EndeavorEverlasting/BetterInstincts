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
_PATCH = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
_QUERY = re.compile(r"^[\w][\w .'\-]{0,63}$", re.UNICODE)
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
    if any("/" in s or "\n" in s or s.lower() == "buydebug" for s in lines):
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


def p04_guide(*, cfg: dict | None = None) -> dict:
    """Emit the complete five-step operator playbook, even without game access.

    P04 can ingest this read-only output before obtaining a host observation.
    It neither authorizes nor performs any UI action.
    """
    cfg = cfg or load_contract()
    book = cfg.get("operator_playbook") or {}
    steps = book.get("ordered_steps") or []
    required = (
        "OPEN_CHEAT_CONSOLE", "ENABLE_CHEATS", "REVEAL_HIDDEN_OBJECTS",
        "ENTER_BUILD_BUY", "SELECT_DEBUG_RESULTS",
    )
    if [s.get("step_id") for s in steps] != list(required):
        raise DiscoveryError("P04_PLAYBOOK_SEQUENCE_CHANGED")
    if [s.get("number") for s in steps] != list(range(1, 6)):
        raise DiscoveryError("P04_PLAYBOOK_NUMBERING_CHANGED")
    if steps[1].get("console_line") != cfg["ordered_console_lines"][0]:
        raise DiscoveryError("P04_TESTINGCHEATS_LINE_CHANGED")
    if steps[2].get("console_line") != cfg["ordered_console_lines"][1]:
        raise DiscoveryError("P04_HIDDEN_LINE_CHANGED")
    if steps[2].get("optional_console_line") != cfg["optional_live_edit_line"]:
        raise DiscoveryError("P04_LIVE_EDIT_LINE_CHANGED")
    if steps[4].get("search_term") != cfg["search_contract"]["primary"]:
        raise DiscoveryError("P04_DEBUG_SEARCH_CHANGED")
    return {
        "state": "P04_PLAYBOOK_RETRIEVED_NO_GAME_ACTION",
        "prompt_id": "P04",
        "operator_order_preserved": True,
        "steps": steps,
        "platform_console_chords": cfg["platform_console_chords"],
        "console_commands": list(cfg["ordered_console_lines"]),
        "optional_live_edit_command": cfg["optional_live_edit_line"],
        "item_families": list(book.get("candidate_item_families") or []),
        "cost_claim_rule": book["item_price_rule"],
        "receipt_audit_command": book["completion_audit"],
        "host_action_authorized": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def audit_p04_receipt(receipt: Mapping[str, object], *, cfg: dict | None = None) -> dict:
    """Check a host-supplied receipt's *shape*, not the truth of its captures.

    Never promote this check to proof that a screenshot was reviewed or that a
    Sims process actually received the commands. Real-game certification is an
    independent local-host responsibility.
    """
    cfg = cfg or load_contract()
    guide = p04_guide(cfg=cfg)
    problems: list[str] = []
    if not isinstance(receipt, Mapping):
        return {
            "state": "P04_EVIDENCE_INCOMPLETE",
            "problems": ["RECEIPT_NOT_OBJECT"],
            "live_certified": False,
            "host_action_authorized": False,
        }
    if receipt.get("schema") != "betterinstincts.hidden-object-discovery-receipt/v1":
        problems.append("RECEIPT_SCHEMA_MISMATCH")
    version = receipt.get("exact_game_build")
    if not isinstance(version, str) or not _PATCH.fullmatch(version):
        problems.append("EXACT_GAME_BUILD_MISSING")
    platform = receipt.get("platform")
    if platform not in guide["platform_console_chords"]:
        problems.append("PLATFORM_UNKNOWN")
    if receipt.get("save_attestation") != "OPERATOR_ATTESTED_DISPOSABLE_LAB":
        problems.append("SAVE_NOT_ATTESTED_LAB")
    if receipt.get("player_explicit_opt_in") is not True:
        problems.append("PLAYER_OPT_IN_MISSING")
    if receipt.get("game_speed_unchanged") is not True:
        problems.append("SPEED_UNCHANGED_UNPROVEN")
    if receipt.get("player_queue_unchanged") is not True:
        problems.append("PLAYER_QUEUE_UNCHANGED_UNPROVEN")
    if platform in ("playstation", "xbox") and receipt.get(
        "acknowledge_testingcheats_trophy_risk"
    ) is not True:
        problems.append("CONSOLE_ACHIEVEMENT_ACK_MISSING")
    cues = receipt.get("scene_cues")
    if not isinstance(cues, Mapping) or not all(
        isinstance(cues.get(name), str) and cues[name].strip()
        for name in ("visual_ref", "operator_ref")
    ):
        problems.append("TWO_SOURCE_SCENE_CUES_MISSING")
    elif cues["visual_ref"] == cues["operator_ref"]:
        problems.append("SCENE_CUE_SOURCES_NOT_DISTINCT")
    expected = [x["step_id"] for x in guide["steps"]]
    evidence = receipt.get("steps")
    seen: list[str] = []
    if not isinstance(evidence, list) or len(evidence) != len(expected):
        problems.append("FIVE_ORDERED_STEP_RECEIPTS_REQUIRED")
    else:
        for idx, item in enumerate(evidence):
            if not isinstance(item, Mapping):
                problems.append("STEP_RECEIPT_NOT_OBJECT:" + str(idx + 1))
                continue
            if item.get("step_id") != expected[idx]:
                problems.append("STEP_SEQUENCE_INVALID:" + str(idx + 1))
            ref = item.get("observation_ref")
            permit = item.get("control_permit_ref")
            if not isinstance(ref, str) or not ref.strip():
                problems.append("STEP_OBSERVATION_MISSING:" + str(idx + 1))
            else:
                seen.append(ref)
            if not isinstance(permit, str) or not permit.strip():
                problems.append("STEP_PERMIT_MISSING:" + str(idx + 1))
            if item.get("outcome") != "OBSERVED":
                problems.append("STEP_OUTCOME_UNVERIFIED:" + str(idx + 1))
        if len(seen) != len(set(seen)):
            problems.append("STEP_CAPTURE_REFS_NOT_DISTINCT")
    if receipt.get("live_edit_requested") is True:
        optional = receipt.get("live_edit_observation")
        if not isinstance(optional, Mapping) or optional.get("outcome") != "OBSERVED" or not isinstance(
            optional.get("observation_ref"), str
        ) or not optional["observation_ref"].strip():
            problems.append("OPTIONAL_LIVE_EDIT_UNVERIFIED")
    if receipt.get("all_items_free") is True or receipt.get("catalog_exhaustive") is True:
        problems.append("UNSUPPORTED_GLOBAL_CATALOG_CLAIM")
    entries = receipt.get("catalog_entries")
    checked = []
    if not isinstance(entries, list) or not (1 <= len(entries) <= cfg["search_contract"]["search_limit"]):
        problems.append("REVIEWED_CATALOG_ENTRIES_REQUIRED")
    else:
        for idx, entry in enumerate(entries):
            row = review_catalog_entry(entry)
            if row["state"] == "ENTRY_NOT_VERIFIED":
                problems.append("CATALOG_ENTRY_UNVERIFIED:" + str(idx + 1))
            else:
                checked.append(row)
    return {
        "state": (
            "P04_EVIDENCE_INCOMPLETE" if problems else
            "P04_EVIDENCE_SHAPE_COMPLETE_PENDING_INDEPENDENT_REVIEW"
        ),
        "problems": problems,
        "steps_structurally_checked": len(seen),
        "reviewed_catalog_entries": len(checked),
        "observed_zero_price_claims_in_receipt": sum(1 for x in checked if x["free"] is True),
        "price_unknown_entries_in_receipt": sum(1 for x in checked if x["free"] is None),
        "live_certified": False,
        "host_action_authorized": False,
        "next_gate": "INDEPENDENT_LOCAL_HOST_VISUAL_AND_PLAYER_REVIEW",
        "proof_ceiling": "STRUCTURAL_RECEIPT_CHECK_ONLY_NOT_GAMEPLAY_CERTIFICATION",
    }
