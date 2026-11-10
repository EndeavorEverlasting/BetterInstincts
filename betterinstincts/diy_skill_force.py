"""Skill-force planner: DIY maker set plus full adult unlock catalog.

P95/P100 stack: soft-focus Sims → Ctrl+Shift+C → testingcheats enabled true →
stats.set_skill_level <stat> <N> for each resolved skill → bounded
ACCEPT_OFFERED_REWARD_TRAIT (OK on offered mastery/reward traits).
Household: count N portraits → skill-round-robin (one skill × every member,
then the next skill) via Space between cells (one foreground screen owner). Required
residuals Cooking/Fitness/Natural Living always re-applied at end.
Completion ledger: skip already-DISPATCHED skill×member cells. Mode-agnostic;
never force F1 while the operator builds.

Bundles: diy_maker / servo_core / creative / social / athletic / residual_core /
full_unlock. Library plans only; scripts/diy_skill_force.py owns typing + OK
accept + foreground serial household executor. Never edits saves. Never practice_skill / BI-005.

Trait safety (2026-11-09 Evil/laundry-fire incident, same owner — no trait daemon):
classify_reward_trait / decide_reward_dialog never blind-OK Evil or other harmful
reward traits (ESCAPE_CANCEL_DIALOG or HOLD only); plan_trait_repair emits
``traits.remove_trait trait_Evil`` for the selected Sim (equip trait_Good only on
explicit operator request); evaluate_ui_action encodes the Escape / new-Servo /
CAS-Continue forbids. All library plans: execute_allowed=False.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "diy-skill-force.v1.json"
MAX_BYTES = 96_000
DEFAULT_REQUIRED_RESIDUALS = ("cooking", "fitness", "natural_living")
COMPLETION_SCHEMA = "betterinstincts.diy-skill-force.completion/v1"
DEFAULT_COMPLETION_LEDGER = ROOT / "dist" / "game-host" / "diy-skill-force-completion.json"
COMPLETE_STATUSES = frozenset({"DISPATCHED", "PANEL_OBSERVED_MAX"})
# PANEL_FALSIFIED is recorded evidence, never a skip/complete status.
NONCOMPLETE_STATUSES = frozenset({"PANEL_FALSIFIED", "UNPROVEN"})
_MAXIMIZE_CLAIM_RE = re.compile(
    r"\b(maximized|maximi[sz]ed|maxed|fully\s+leveled|skills?-?\s*panel\s+pass|"
    r"level\s*10\s+pass|handiness\s+maximized)\b",
    re.IGNORECASE,
)
_DISPATCHED_ONLY_STATES = frozenset(
    {
        "DIY_SKILL_FORCE_DISPATCHED",
        "HOUSEHOLD_SKILL_FORCE_DISPATCHED",
        "HOST_CHEAT_TYPED",
        "DISPATCHED",
    }
)


class DiySkillForceError(ValueError):
    pass


def default_completion_ledger_path() -> Path:
    return Path(DEFAULT_COMPLETION_LEDGER)


def completion_member_key(
    session_id: str | None,
    member_index: int,
    member_key: str | None = None,
) -> str:
    """Stable ledger key for one household portrait slot."""
    sid = str(session_id or "").strip() or "anonymous-session"
    label = str(member_key or "").strip()
    if label:
        return f"{sid}::key::{label}"
    return f"{sid}::idx::{int(member_index)}"


def empty_completion_ledger() -> dict:
    return {
        "schema": COMPLETION_SCHEMA,
        "updated_at": None,
        "members": {},
        "note": (
            "DISPATCHED = host typed stats.set_skill_level for resume/skip. "
            "Not Skills-panel PASS. Never report DISPATCHED as maximized. "
            "PANEL_OBSERVED_MAX only after Skills-panel LOCAL_OBSERVED. "
            "PANEL_FALSIFIED clears skip after a contradicting panel read."
        ),
    }


def load_completion_ledger(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else default_completion_ledger_path()
    if path.is_symlink():
        raise DiySkillForceError("COMPLETION_LEDGER_SYMLINK_FORBIDDEN")
    if not path.exists():
        return empty_completion_ledger()
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise DiySkillForceError("COMPLETION_LEDGER_UNSAFE")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    if raw.get("schema") not in (None, COMPLETION_SCHEMA):
        raise DiySkillForceError("COMPLETION_LEDGER_BAD_SCHEMA")
    members = raw.get("members")
    if members is None:
        members = {}
    if not isinstance(members, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    out = empty_completion_ledger()
    out["updated_at"] = raw.get("updated_at")
    out["members"] = dict(members)
    if isinstance(raw.get("note"), str):
        out["note"] = raw["note"]
    return out


def save_completion_ledger(ledger: Mapping[str, object], path: Path | None = None) -> Path:
    path = Path(path) if path is not None else default_completion_ledger_path()
    if path.is_symlink():
        raise DiySkillForceError("COMPLETION_LEDGER_SYMLINK_FORBIDDEN")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(ledger)
    payload["schema"] = COMPLETION_SCHEMA
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def skill_is_complete(entry: object, *, target_level: int) -> bool:
    if not isinstance(entry, Mapping):
        return False
    status = str(entry.get("status") or "")
    if status not in COMPLETE_STATUSES:
        return False
    try:
        level = int(entry.get("level"))
    except (TypeError, ValueError):
        return False
    return level >= int(target_level)


def completed_skill_ids_for_member(
    ledger: Mapping[str, object],
    member_key: str,
    *,
    target_level: int,
) -> set[str]:
    members = ledger.get("members") or {}
    if not isinstance(members, Mapping):
        return set()
    row = members.get(member_key) or {}
    if not isinstance(row, Mapping):
        return set()
    skills = row.get("skills") or {}
    if not isinstance(skills, Mapping):
        return set()
    out: set[str] = set()
    for sid, entry in skills.items():
        if skill_is_complete(entry, target_level=target_level):
            out.add(str(sid).strip().lower())
    return out


def record_skill_dispatched(
    ledger: dict,
    *,
    member_key: str,
    skill_id: str,
    skill_stat: str,
    level: int,
    evidence: str = "HOST_CHEAT_TYPED",
) -> dict:
    """Mark one skill done for resume/skip. Not a panel PASS claim."""
    members = ledger.setdefault("members", {})
    if not isinstance(members, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    row = members.setdefault(str(member_key), {"skills": {}})
    if not isinstance(row, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    skills = row.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    sid = str(skill_id).strip().lower()
    skills[sid] = {
        "skill_id": sid,
        "skill_stat": str(skill_stat),
        "level": int(level),
        "status": "DISPATCHED",
        "evidence": str(evidence),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return skills[sid]


def record_skill_panel_falsified(
    ledger: dict,
    *,
    member_key: str,
    skill_id: str,
    observed_level: int | None = None,
    evidence: str = "SKILLS_PANEL_LOCAL_OBSERVED_CONTRADICTS_DISPATCHED",
    note: str | None = None,
) -> dict:
    """Clear a DISPATCHED skip after Skills-panel proof contradicts maximize claims.

    PANEL_FALSIFIED is never treated as complete by ``skill_is_complete``.
    """
    members = ledger.setdefault("members", {})
    if not isinstance(members, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    row = members.setdefault(str(member_key), {"skills": {}})
    if not isinstance(row, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    skills = row.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    sid = str(skill_id).strip().lower()
    prior = skills.get(sid) if isinstance(skills.get(sid), Mapping) else {}
    entry = {
        "skill_id": sid,
        "skill_stat": str(prior.get("skill_stat") or ""),
        "level": int(observed_level) if observed_level is not None else prior.get("level"),
        "status": "PANEL_FALSIFIED",
        "evidence": str(evidence),
        "prior_status": str(prior.get("status") or ""),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if note:
        entry["note"] = str(note)
    skills[sid] = entry
    return entry


def assess_skill_force_claim(
    *,
    claim: str,
    live_state: str | None = None,
    panel_observed_max: bool = False,
    pass_claim: str | None = None,
) -> dict:
    """Fail closed: DISPATCHED / host-typed receipts are never 'maximized'.

    P83 2026-11-09: operator Skills panel showed Cooking 10 and Handiness absent
    after a household Handiness DISPATCHED receipt was narrated as maximized.
    """
    text = str(claim or "").strip()
    state = str(live_state or "").strip()
    wants_maximize = bool(_MAXIMIZE_CLAIM_RE.search(text))
    dispatched_only = state in _DISPATCHED_ONLY_STATES or state.endswith("_DISPATCHED")
    forbidden_pass = str(pass_claim or "").upper().startswith("FORBIDDEN")
    if wants_maximize and panel_observed_max and not forbidden_pass:
        return {
            "state": "CLAIM_ALLOWED_PANEL_OBSERVED_MAX",
            "allowed": True,
            "proof_ceiling": "SKILLS_PANEL_LOCAL_OBSERVED_MAX",
            "live_state": state or None,
        }
    if wants_maximize:
        return {
            "state": "CLAIM_REJECTED_DISPATCHED_IS_NOT_MAXIMIZED",
            "allowed": False,
            "proof_ceiling": "HOST_SENDINPUT_DIY_SKILL_CHEAT_DISPATCH_NOT_BI005_SKILL_GROWTH_CERT",
            "live_state": state or None,
            "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
            "correction": (
                "Say DISPATCHED / host typed only. Do not say maximized, maxed, "
                "or Skills-panel PASS until LOCAL_OBSERVED level 10."
            ),
            "dispatched_only_state": dispatched_only,
        }
    return {
        "state": "CLAIM_ALLOWED_NON_MAXIMIZE_LANGUAGE",
        "allowed": True,
        "proof_ceiling": "LANGUAGE_DOES_NOT_CLAIM_PANEL_MAX",
        "live_state": state or None,
    }


def member_needs_skill_work(
    ledger: Mapping[str, object],
    *,
    member_key: str,
    skill_ids: Sequence[str],
    target_level: int,
) -> bool:
    done = completed_skill_ids_for_member(ledger, member_key, target_level=target_level)
    for sid in skill_ids:
        if str(sid).strip().lower() not in done:
            return True
    return False


def skills_panel_observation_policy(
    *,
    purpose: str = "verify",
    live_paused: bool = True,
    precious_time: bool = True,
    concurrent_live_cert: bool = False,
    main_goal_unfinished: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Skills-panel proof policy for skill-force.

    Dispatch under precious time: KEEP_PAUSED.
    Verify: PLAY_BRIEF (5–10s) → OBSERVE → REPAUSE. Paused-only UI is STALE.
    Never leave sim speed running after verify. Not main-menu Resume.
    """
    cfg = cfg or load_contract()
    obs = (cfg.get("inject_sequence") or {}).get("skills_panel_observation") or {}
    play_cfg = obs.get("play_brief_for_fresh_panel") or {}
    purpose_l = str(purpose or "verify").lower()
    precious = bool(precious_time or concurrent_live_cert or main_goal_unfinished)
    min_s = int(play_cfg.get("min_play_seconds") or 5)
    max_s = int(play_cfg.get("max_play_seconds") or 10)
    default_s = int(play_cfg.get("default_play_seconds") or 7)
    play_seconds = max(min_s, min(max_s, default_s))
    if purpose_l == "dispatch":
        action = "KEEP_PAUSED"
        panel_status = str(obs.get("paused_panel_status") or "UNPROVEN_STALE")
    elif purpose_l == "verify":
        action = "PLAY_BRIEF_OBSERVE_REPAUSE"
        panel_status = "FRESH_PANEL_AFTER_PLAY_BRIEF"
    else:
        raise DiySkillForceError("UNKNOWN_SKILLS_PANEL_PURPOSE")
    if purpose_l == "verify" and not live_paused:
        panel_status = "LIVE_ALREADY_PLAYING_CAPTURE_THEN_REPAUSE"
    return {
        "step": str(obs.get("step") or "PLAY_BRIEF_OBSERVE_REPAUSE"),
        "purpose": purpose_l,
        "action": action,
        "panel_status": panel_status,
        "live_paused": bool(live_paused),
        "precious_time": precious,
        "concurrent_live_cert": bool(concurrent_live_cert),
        "main_goal_unfinished": bool(main_goal_unfinished),
        "play_seconds": play_seconds,
        "min_play_seconds": min_s,
        "max_play_seconds": max_s,
        "play_key": str(play_cfg.get("play_key") or "1"),
        "pause_key": str(play_cfg.get("pause_key") or "0"),
        "always_repause": bool(play_cfg.get("always_repause", True)),
        "dispatch_while_paused_allowed": bool(obs.get("dispatch_while_paused_allowed", True)),
        "note": (
            obs.get("keep_paused_policy")
            if purpose_l == "dispatch"
            else "Play 5–10s at 1x, capture Skills panel, pause again."
        ),
    }


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise DiySkillForceError("DIY_SKILL_FORCE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.diy-skill-force/v1":
        raise DiySkillForceError("BAD_DIY_SKILL_FORCE_SCHEMA")
    seq = cfg.get("inject_sequence") or {}
    if seq.get("activate_testing_cheats") != "testingcheats enabled true":
        raise DiySkillForceError("TESTINGCHEATS_ENABLED_TRUE_REQUIRED")
    if list(seq.get("open_console_chord") or []) != ["CTRL", "SHIFT", "C"]:
        raise DiySkillForceError("CTRL_SHIFT_C_CONSOLE_CHORD_REQUIRED")
    if seq.get("mode_agnostic") is not True:
        raise DiySkillForceError("MODE_AGNOSTIC_REQUIRED")
    if seq.get("never_force_mode_switch") is not True:
        raise DiySkillForceError("NEVER_FORCE_MODE_SWITCH_REQUIRED")
    if seq.get("require_live_mode") is True:
        raise DiySkillForceError("REQUIRE_LIVE_MODE_FORBIDDEN")
    template = str(seq.get("skill_command_template") or "")
    if "{skill_stat}" not in template or "{level}" not in template:
        raise DiySkillForceError("SKILL_COMMAND_TEMPLATE_REQUIRED")
    catalog = cfg.get("skill_catalog")
    if not isinstance(catalog, list) or not catalog:
        raise DiySkillForceError("SKILL_CATALOG_REQUIRED")
    bundles = cfg.get("bundles")
    if not isinstance(bundles, dict) or "diy_maker" not in bundles:
        raise DiySkillForceError("DIY_MAKER_BUNDLE_REQUIRED")
    if "full_unlock" not in bundles:
        raise DiySkillForceError("FULL_UNLOCK_BUNDLE_REQUIRED")
    if "residual_core" not in bundles:
        raise DiySkillForceError("RESIDUAL_CORE_BUNDLE_REQUIRED")
    full_ids = list((bundles["full_unlock"] or {}).get("skill_ids") or [])
    if "handiness" not in full_ids or "cooking" not in full_ids or "logic" not in full_ids:
        raise DiySkillForceError("FULL_UNLOCK_CORE_SKILLS_REQUIRED")
    residuals = list(cfg.get("required_residual_skills") or DEFAULT_REQUIRED_RESIDUALS)
    if not residuals:
        raise DiySkillForceError("REQUIRED_RESIDUAL_SKILLS_REQUIRED")
    for sid in residuals:
        if sid not in full_ids:
            raise DiySkillForceError("REQUIRED_RESIDUAL_SKILL_MISSING:" + str(sid))
        if sid not in list((bundles["residual_core"] or {}).get("skill_ids") or []):
            raise DiySkillForceError("RESIDUAL_CORE_MISSING:" + str(sid))
    ht = cfg.get("household_traverse") or {}
    if not isinstance(ht, Mapping) or ht.get("next_member_key") != "SPACE":
        raise DiySkillForceError("HOUSEHOLD_TRAVERSE_SPACE_REQUIRED")
    if str(ht.get("dispatch_order") or "") != "skill_round_robin":
        raise DiySkillForceError("HOUSEHOLD_DISPATCH_ORDER_SKILL_ROUND_ROBIN_REQUIRED")
    if (cfg.get("execution_policy") or {}).get("detached_worker") is not False:
        raise DiySkillForceError("DETACHED_HOUSEHOLD_EXECUTION_FORBIDDEN")
    if (cfg.get("execution_policy") or {}).get("model") != "SINGLE_FOREGROUND_SERIAL_UI_OWNER":
        raise DiySkillForceError("HOUSEHOLD_FOREGROUND_SERIAL_OWNER_REQUIRED")
    _validate_trait_safety(cfg)
    return cfg


def _validate_trait_safety(cfg: Mapping[str, object]) -> None:
    """Fail closed if the durable Evil / Escape / new-Servo guards are weakened."""
    seq = cfg.get("inject_sequence") or {}
    reward = (seq.get("reward_dialog_accept") or {}) if isinstance(seq, Mapping) else {}
    if not isinstance(reward, Mapping) or reward.get("refuse_blind_ok") is not True:
        raise DiySkillForceError("REWARD_REFUSE_BLIND_OK_REQUIRED")
    if "trait_Evil" not in list(reward.get("forbidden_reward_traits") or []):
        raise DiySkillForceError("REWARD_FORBID_EVIL_REQUIRED")
    if reward.get("harmful_trait_action") != "ESCAPE_CANCEL_DIALOG":
        raise DiySkillForceError("REWARD_HARMFUL_ACTION_ESCAPE_CANCEL_REQUIRED")
    safety = cfg.get("trait_safety")
    if not isinstance(safety, Mapping) or safety.get("refuse_blind_ok") is not True:
        raise DiySkillForceError("TRAIT_SAFETY_REQUIRED")
    if "trait_Evil" not in list(safety.get("forbidden_reward_traits") or []):
        raise DiySkillForceError("TRAIT_SAFETY_EVIL_REQUIRED")
    repair = cfg.get("trait_repair")
    if not isinstance(repair, Mapping):
        raise DiySkillForceError("TRAIT_REPAIR_REQUIRED")
    if list(repair.get("default_remove_trait_ids") or []) != ["trait_Evil"]:
        raise DiySkillForceError("TRAIT_REPAIR_DEFAULT_REMOVE_EVIL_ONLY_REQUIRED")
    good = repair.get("optional_equip_good") or {}
    if not isinstance(good, Mapping) or good.get("requires_operator_request") is not True:
        raise DiySkillForceError("TRAIT_REPAIR_GOOD_REQUIRES_OPERATOR_REQUEST")
    if repair.get("execute_allowed") is not False:
        raise DiySkillForceError("TRAIT_REPAIR_EXECUTE_MUST_BE_FALSE")
    forbids = cfg.get("ui_forbids")
    if not isinstance(forbids, Mapping):
        raise DiySkillForceError("UI_FORBIDS_REQUIRED")
    esc = forbids.get("escape_as_household_traverse_close") or {}
    if not isinstance(esc, Mapping) or esc.get("forbidden") is not True:
        raise DiySkillForceError("UI_FORBID_ESCAPE_TRAVERSE_CLOSE_REQUIRED")
    if (forbids.get("escape_spam") or {}).get("forbidden") is not True:
        raise DiySkillForceError("UI_FORBID_ESCAPE_SPAM_REQUIRED")
    servo = forbids.get("create_or_activate_new_servo") or {}
    if not isinstance(servo, Mapping) or servo.get("forbidden_without_operator_consent") is not True:
        raise DiySkillForceError("UI_FORBID_NEW_SERVO_CONSENT_REQUIRED")
    if (forbids.get("cas_continue_when_escape_cancel_requested") or {}).get("forbidden") is not True:
        raise DiySkillForceError("UI_FORBID_CAS_CONTINUE_REQUIRED")


def _trait_key(value: object) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _forbidden_trait_keys(cfg: Mapping[str, object]) -> dict[str, str]:
    """lower-case alias/id -> canonical forbidden trait id."""
    safety = cfg.get("trait_safety") or {}
    reward = ((cfg.get("inject_sequence") or {}).get("reward_dialog_accept") or {})
    out: dict[str, str] = {}
    for tid in list(safety.get("forbidden_reward_traits") or []) + list(
        reward.get("forbidden_reward_traits") or []
    ):
        out[_trait_key(tid)] = str(tid)
    aliases = safety.get("aliases") or {}
    if isinstance(aliases, Mapping):
        for canon, names in aliases.items():
            out[_trait_key(canon)] = str(canon)
            for name in names or []:
                out[_trait_key(name)] = str(canon)
    for name in reward.get("forbidden_reward_trait_aliases") or []:
        key = _trait_key(name)
        out.setdefault(key, "trait_Evil" if "evil" in key else str(name))
    return out


def classify_reward_trait(
    observed: object = None,
    *,
    dialog_text: object = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Classify an observed reward/trait id or dialog text. Offline; no input.

    HARMFUL: id/alias matches a forbidden trait, or text contains a harmful
    label token (e.g. "evil"). UNKNOWN: nothing observed. OTHER: observed but
    not harmful — still never auto-OK'd here (decide_reward_dialog owns that).
    """
    cfg = cfg or load_contract()
    keys = _forbidden_trait_keys(cfg)
    tokens = [
        _trait_key(t)
        for t in ((cfg.get("trait_safety") or {}).get("harmful_label_tokens") or [])
        if str(t).strip()
    ]
    obs = _trait_key(observed)
    text = str(dialog_text or "").lower()
    if not obs and not text.strip():
        return {"class": "UNKNOWN", "trait_id": None, "reason": "NO_OBSERVATION"}
    if obs in keys:
        return {"class": "HARMFUL", "trait_id": keys[obs], "reason": "FORBIDDEN_TRAIT_ID"}
    haystack = " ".join(w for w in (obs.replace("_", " "), text) if w)
    for token in tokens:
        if token and re.search(r"\b" + re.escape(token.replace("_", " ")) + r"\b", haystack):
            return {
                "class": "HARMFUL",
                "trait_id": keys.get(token, "trait_Evil" if token == "evil" else token),
                "reason": "HARMFUL_LABEL_TOKEN:" + token,
            }
    return {"class": "OTHER", "trait_id": obs or None, "reason": "NOT_FORBIDDEN"}


def decide_reward_dialog(
    observed: object = None,
    *,
    dialog_text: object = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Reward-dialog policy. Never ACCEPT an Evil/harmful trait; never blind-OK.

    Harmful -> ESCAPE_CANCEL_DIALOG (Escape on that one observed dialog only).
    Unknown/unclassified -> HOLD. Other observed rewards -> ACCEPT_ELIGIBLE,
    which still requires the owning one-step adapter and a fresh observation.
    """
    cfg = cfg or load_contract()
    reward = ((cfg.get("inject_sequence") or {}).get("reward_dialog_accept") or {})
    verdict = classify_reward_trait(observed, dialog_text=dialog_text, cfg=cfg)
    never = list(reward.get("harmful_trait_never_keys") or ["ENTER", "OK_CLICK"])
    base = {
        "classification": verdict,
        "refuse_blind_ok": True,
        "forbidden_keys": never,
        "proof_ceiling": "OFFLINE_REWARD_TRAIT_POLICY_NOT_LIVE_DIALOG_OBSERVATION",
    }
    if verdict["class"] == "HARMFUL":
        return {
            **base,
            "decision": "ESCAPE_CANCEL_DIALOG",
            "accept": False,
            "allowed_keys": ["ESCAPE"],
            "scope": "THIS_OBSERVED_DIALOG_ONLY",
            "note": "Harmful reward trait: cancel the dialog; never Enter/OK. Escape is not a console or traverse close.",
        }
    if verdict["class"] == "UNKNOWN":
        return {
            **base,
            "decision": "HOLD",
            "accept": False,
            "allowed_keys": [],
            "state": "NEEDS_DIALOG_IDENTIFICATION",
            "note": "No classified dialog: no Enter, no OK click, no Cancel.",
        }
    return {
        **base,
        "decision": "ACCEPT_ELIGIBLE",
        "accept": True,
        "allowed_keys": [str(reward.get("primary_confirm_key") or "ENTER")],
        "note": "Non-harmful observed reward; owning one-step adapter must still verify the fresh dialog.",
    }


def _canonical_repair_trait(trait: object, cfg: Mapping[str, object]) -> str:
    repair = cfg.get("trait_repair") or {}
    repairable = {str(t) for t in repair.get("repairable_trait_ids") or []}
    key = _trait_key(trait)
    lookup = {_trait_key(t): str(t) for t in repairable}
    aliases = repair.get("aliases") or {}
    if isinstance(aliases, Mapping):
        for canon, names in aliases.items():
            if str(canon) in repairable:
                for name in names or []:
                    lookup[_trait_key(name)] = str(canon)
    if key not in lookup:
        raise DiySkillForceError("TRAIT_NOT_REPAIRABLE:" + str(trait))
    return lookup[key]


def plan_trait_repair(
    *,
    remove_traits: Optional[Sequence[str]] = None,
    equip_good: bool = False,
    operator_requested_good: bool = False,
    player_directed: bool = False,
    game_mode: str = "unknown",
    cfg: Optional[dict] = None,
) -> dict:
    """Console plan for the selected Sim: remove Evil (default), optional Good.

    ``traits.equip_trait trait_Good`` is emitted ONLY when the operator asked for
    it (equip_good AND operator_requested_good). Evaluate-only; no live execute.
    """
    cfg = cfg or load_contract()
    repair = cfg["trait_repair"]
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "next_gate": "YIELD_TO_PLAYER",
            "steps": [],
            "execute_allowed": False,
            "proof_ceiling": repair["proof_ceiling"],
        }
    seq = cfg["inject_sequence"]
    mode = str(game_mode or "unknown").lower()
    allowed = {str(m) for m in (seq.get("allowed_modes") or [])}
    if allowed and mode not in allowed:
        raise DiySkillForceError("UNSUPPORTED_GAME_MODE")
    names = list(remove_traits) if remove_traits else list(repair["default_remove_trait_ids"])
    canon: list[str] = []
    for name in names:
        tid = _canonical_repair_trait(name, cfg)
        if tid not in canon:
            canon.append(tid)
    good_cfg = repair.get("optional_equip_good") or {}
    good_id = str(good_cfg.get("trait_id") or "trait_Good")
    if equip_good and not operator_requested_good:
        raise DiySkillForceError("GOOD_TRAIT_REQUIRES_OPERATOR_REQUEST")
    steps: list[dict] = [
        {
            "step": "REQUIRE_FOREGROUND_SIMS",
            "required": True,
            "note": "Soft focus only; never force F1",
        },
        {
            "step": "REQUIRE_ACTIVE_SIM_SELECTION",
            "required": True,
            "note": "Select the Sim that has the unwanted trait; commands apply to the selected Sim only. Do NOT create or activate a new Sim.",
        },
        {
            "step": "OPEN_CHEAT_CONSOLE",
            "chord": list(repair.get("open_console_chord") or seq["open_console_chord"]),
            "chord_label": "Ctrl+Shift+C",
            "required": True,
        },
        {
            "step": "ACTIVATE_TESTING_CHEATS",
            "command": seq["activate_testing_cheats"],
            "alias": seq.get("activate_testing_cheats_alias"),
            "required": True,
        },
    ]
    removed: list[str] = []
    for tid in canon:
        cmd = str(repair["remove_command_template"]).format(trait_id=tid)
        steps.append({"step": "REMOVE_TRAIT", "command": cmd, "trait_id": tid, "required": True})
        removed.append(tid)
    equipped: list[str] = []
    if equip_good and operator_requested_good:
        cmd = str(repair["equip_command_template"]).format(trait_id=good_id)
        steps.append(
            {
                "step": "EQUIP_TRAIT",
                "command": cmd,
                "trait_id": good_id,
                "required": True,
                "operator_requested": True,
            }
        )
        equipped.append(good_id)
    steps.append(
        {
            "step": "CLOSE_CHEAT_CONSOLE",
            "key": repair.get("close_console_key") or seq["close_console_key"],
            "required": True,
            "note": "Ctrl+Shift+C toggle — never Escape (opens Travel map / pause MENU)",
        }
    )
    steps.append(
        {
            "step": "OBSERVE_TRAIT_REMOVED",
            "required": True,
            "note": "LOCAL_OBSERVED trait gone on the selected Sim (CAS/Traits panel) before any PASS claim",
        }
    )
    return {
        "state": "TRAIT_REPAIR_PLAN_READY",
        "next_gate": "OPERATOR_OR_LOCAL_AGENT_EXECUTE_AFTER_SELECTION_VERIFIED",
        "game_mode": mode,
        "mode_agnostic": True,
        "remove_trait_ids": removed,
        "equip_trait_ids": equipped,
        "operator_requested_good": bool(operator_requested_good and equip_good),
        "open_console": "Ctrl+Shift+C",
        "steps": steps,
        "forbidden": list(seq.get("forbidden") or []),
        "ui_forbids": dict(cfg.get("ui_forbids") or {}),
        "execute_allowed": False,
        "live_gate": repair["live_gate"],
        "proof_ceiling": repair["proof_ceiling"],
        "not_bi005": True,
        "not_practice_skill": True,
    }


def trait_repair_commands(plan: Mapping[str, object]) -> list[str]:
    """Flatten a trait-repair plan to console lines (testingcheats first)."""
    out: list[str] = []
    for step in plan.get("steps") or []:
        if isinstance(step, Mapping) and isinstance(step.get("command"), str):
            out.append(step["command"].strip())
    if not out or out[0] != "testingcheats enabled true":
        raise DiySkillForceError("PLAN_MUST_START_WITH_TESTINGCHEATS_ENABLED_TRUE")
    if not any(c.startswith("traits.remove_trait ") for c in out[1:]):
        raise DiySkillForceError("PLAN_MISSING_TRAIT_REMOVE")
    return out


_ESCAPE_ACTIONS = frozenset({"ESCAPE", "ESC", "PRESS_ESCAPE", "TAP_ESCAPE"})
_NEW_SERVO_ACTIONS = frozenset(
    {
        "ACTIVATE_NEW_SERVO",
        "CREATE_NEW_SERVO",
        "CREATE_NEW_SIM",
        "ACTIVATE_NEW_SIM",
        "PLAY_NEW_SERVO",
    }
)


def evaluate_ui_action(
    action: str,
    *,
    context: str = "",
    operator_consent: bool = False,
    escape_cancel_requested: bool = False,
    operator_requested_good: bool = False,
    repeat_count: int = 1,
    cfg: Optional[dict] = None,
) -> dict:
    """Offline verdict for a proposed UI action. Never dispatches input.

    Encodes: Escape is never the household-traverse / console close (use
    Ctrl+Shift+C); Escape spam opens the Travel map / pause MENU; creating or
    activating a new Servo needs explicit operator consent; CAS Continue is
    forbidden once Escape-cancel was requested; trait_Good needs an operator ask.
    """
    cfg = cfg or load_contract()
    forbids = cfg["ui_forbids"]
    act = str(action or "").strip().upper().replace(" ", "_")
    ctx = str(context or "").strip().upper().replace(" ", "_")

    def verdict(allowed: bool, reason: str, **extra: object) -> dict:
        return {
            "action": act,
            "context": ctx,
            "allowed": allowed,
            "reason": reason,
            "proof_ceiling": forbids.get("proof_ceiling"),
            **extra,
        }

    if act in _ESCAPE_ACTIONS:
        if int(repeat_count) > 1 or ctx in {"SPAM", "ESCAPE_SPAM"}:
            return verdict(
                False,
                "ESCAPE_SPAM_FORBIDDEN_OPENS_TRAVEL_MAP_OR_MENU",
                use_instead="ONE_ESCAPE_CANCEL_OF_OBSERVED_DIALOG_OR_CTRL_SHIFT_C",
            )
        if ctx in {
            "HOUSEHOLD_TRAVERSE",
            "HOUSEHOLD_TRAVERSE_CLOSE",
            "CONSOLE_CLOSE",
            "CLOSE_CHEAT_CONSOLE",
            "SKILL_FORCE",
        }:
            return verdict(
                False,
                "ESCAPE_AS_HOUSEHOLD_TRAVERSE_CLOSE_FORBIDDEN",
                use_instead=str(
                    (forbids.get("escape_as_household_traverse_close") or {}).get("use_instead")
                    or "CTRL_SHIFT_C_TOGGLE"
                ),
            )
        if ctx in {"CAS", "REWARD_DIALOG", "OBSERVED_DIALOG", "CANCEL_DIALOG"}:
            return verdict(True, "ESCAPE_CANCEL_OF_OBSERVED_DIALOG_ONLY", scope="ONE_PRESS")
        return verdict(False, "ESCAPE_CONTEXT_UNIDENTIFIED_HOLD", use_instead="HOLD")
    if act in _NEW_SERVO_ACTIONS:
        if not operator_consent:
            return verdict(
                False,
                "NEW_SERVO_CREATE_ACTIVATE_REQUIRES_OPERATOR_CONSENT",
                use_instead="ESCAPE_CANCEL_CAS" if escape_cancel_requested else "HOLD",
            )
        if escape_cancel_requested:
            return verdict(False, "ESCAPE_CANCEL_REQUESTED_CONFLICTS_WITH_NEW_SERVO", use_instead="ESCAPE_CANCEL_CAS")
        return verdict(True, "OPERATOR_CONSENTED_NEW_SERVO")
    if act in {"CAS_CONTINUE", "CAS_GENDER_CONTINUE", "CAS_GENDER_SELECT_CONTINUE"}:
        if escape_cancel_requested:
            return verdict(
                False,
                "CAS_CONTINUE_FORBIDDEN_WHEN_ESCAPE_CANCEL_REQUESTED",
                use_instead="ESCAPE_CANCEL_CAS",
            )
        if not operator_consent:
            return verdict(
                False,
                "CAS_CONTINUE_REQUIRES_OPERATOR_CONSENT_FOR_NEW_SIM",
                use_instead="HOLD",
            )
        return verdict(True, "OPERATOR_CONSENTED_CAS_CONTINUE")
    if act in {"EQUIP_TRAIT_GOOD", "EQUIP_GOOD_TRAIT"}:
        if not operator_requested_good:
            return verdict(False, "GOOD_TRAIT_REQUIRES_OPERATOR_REQUEST")
        return verdict(True, "OPERATOR_REQUESTED_GOOD_TRAIT")
    if act in {"ENTER_ON_REWARD_DIALOG", "OK_CLICK_REWARD_DIALOG", "BLIND_OK_REWARD_TRAIT"}:
        return verdict(False, "BLIND_OK_REWARD_TRAIT_FORBIDDEN", use_instead="decide_reward_dialog")
    return verdict(True, "NOT_COVERED_BY_UI_FORBIDS")


def required_residual_skills(cfg: Optional[dict] = None) -> list[str]:
    cfg = cfg or load_contract()
    return [str(s) for s in (cfg.get("required_residual_skills") or DEFAULT_REQUIRED_RESIDUALS)]


def catalog_snapshot(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    seq = cfg.get("inject_sequence") or {}
    return {
        "skills": list(cfg["skill_catalog"]),
        "bundles": dict(cfg["bundles"]),
        "required_residual_skills": required_residual_skills(cfg),
        "household_traverse": dict(cfg.get("household_traverse") or {}),
        "default_level": int(seq["default_level"]),
        "close_console_key": seq.get("close_console_key"),
        "cheat_line_submit": seq.get("cheat_line_submit"),
        "inject_sequence": {
            "close_console_key": seq.get("close_console_key"),
            "cheat_line_submit": seq.get("cheat_line_submit"),
            "mode_agnostic": bool(seq.get("mode_agnostic")),
            "open_console_chord_owner": seq.get("open_console_chord_owner"),
            "pass_requires_skills_panel_local_observed": bool(
                seq.get("pass_requires_skills_panel_local_observed")
            ),
            "console_text_is_not_pass": bool(seq.get("console_text_is_not_pass")),
            "level_up_toast_is_not_pass": bool(seq.get("level_up_toast_is_not_pass")),
        },
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": list(seq.get("forbidden") or []),
        "trait_safety": dict(cfg.get("trait_safety") or {}),
        "trait_repair": dict(cfg.get("trait_repair") or {}),
        "ui_forbids": dict(cfg.get("ui_forbids") or {}),
    }


def _skill_index(cfg: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in cfg["skill_catalog"]:
        if not isinstance(row, Mapping):
            continue
        sid = str(row.get("id") or "").strip()
        if sid:
            out[sid] = dict(row)
    return out


def resolve_skills(
    *,
    skill_ids: Optional[Sequence[str]] = None,
    bundle: Optional[str] = None,
    omit_skill_ids: Optional[Sequence[str]] = None,
    cfg: Optional[dict] = None,
) -> list[dict]:
    """Resolve catalog rows from explicit ids and/or a named bundle.

    ``omit_skill_ids`` drops skills already recorded complete in the durable
    completion ledger so the host does not retype maxed cheats.
    """
    cfg = cfg or load_contract()
    index = _skill_index(cfg)
    omit = {
        str(s).strip().lower()
        for s in (omit_skill_ids or [])
        if str(s).strip()
    }
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(sid: str, *, allow_duplicate_residual: bool = False) -> None:
        key = str(sid).strip().lower()
        if not key:
            return
        if key not in index:
            raise DiySkillForceError("UNKNOWN_DIY_SKILL:" + key)
        if key in omit:
            return
        if key in seen and not allow_duplicate_residual:
            return
        if key not in seen:
            seen.add(key)
        ordered.append(key)

    loaded_any = False
    if bundle is not None:
        bkey = str(bundle).strip()
        brow = (cfg.get("bundles") or {}).get(bkey)
        if not isinstance(brow, Mapping):
            raise DiySkillForceError("UNKNOWN_DIY_BUNDLE:" + bkey)
        for sid in brow.get("skill_ids") or []:
            loaded_any = True
            _add(str(sid))
    if skill_ids:
        for sid in skill_ids:
            loaded_any = True
            _add(str(sid))
    if not loaded_any:
        # All-the-way unlock is the operator default when nothing is named.
        default_bundle = "full_unlock" if "full_unlock" in cfg["bundles"] else "diy_maker"
        for sid in (cfg["bundles"][default_bundle].get("skill_ids") or []):
            _add(str(sid))
    # Operator miss set: re-queue residuals at end of full_unlock so mid-batch
    # truncation cannot leave Cooking/Fitness/Natural Living behind — but never
    # re-queue a residual the completion ledger already marked done, and do not
    # double-type when the remaining set is residuals-only (already-maxed skip).
    if bundle == "full_unlock" or (bundle is None and not skill_ids):
        residual_ids = {
            str(s).strip().lower() for s in required_residual_skills(cfg)
        }
        non_residual_remaining = [s for s in ordered if s not in residual_ids]
        for sid in required_residual_skills(cfg):
            key = str(sid).strip().lower()
            if key in omit:
                continue
            if key in index and key in seen:
                if non_residual_remaining:
                    _add(key, allow_duplicate_residual=True)
            else:
                _add(key)
    return [index[sid] for sid in ordered]


def _reward_accept_cfg(seq: Mapping[str, object]) -> dict:
    raw = seq.get("reward_dialog_accept") or {}
    if not isinstance(raw, Mapping):
        return {}
    return dict(raw)


def plan_skill_force(
    *,
    skill_ids: Optional[Sequence[str]] = None,
    bundle: Optional[str] = None,
    level: Optional[int] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
    accept_reward_dialogs: Optional[bool] = None,
    omit_skill_ids: Optional[Sequence[str]] = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Return ordered console steps. Mode-agnostic; does not touch the game."""
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "next_gate": "YIELD_TO_PLAYER",
            "steps": [],
            "skills": [],
            "game_mode": game_mode,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    seq = cfg["inject_sequence"]
    reward = _reward_accept_cfg(seq)
    accept = (
        bool(reward.get("enabled_by_default", True))
        if accept_reward_dialogs is None
        else bool(accept_reward_dialogs)
    )
    allowed = {str(m) for m in (seq.get("allowed_modes") or [])}
    mode = str(game_mode or "unknown").lower()
    if allowed and mode not in allowed:
        raise DiySkillForceError("UNSUPPORTED_GAME_MODE")

    default_level = int(seq["default_level"])
    min_level = int(seq["min_level"])
    max_level = int(seq["max_level"])
    target = default_level if level is None else int(level)
    if isinstance(level, bool) or target < min_level or target > max_level:
        raise DiySkillForceError("INVALID_SKILL_LEVEL")

    omit = [str(s).strip().lower() for s in (omit_skill_ids or []) if str(s).strip()]
    skills = resolve_skills(
        skill_ids=skill_ids,
        bundle=bundle,
        omit_skill_ids=omit,
        cfg=cfg,
    )
    if not skills:
        return {
            "state": "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED",
            "next_gate": "SELECT_NEXT_HOUSEHOLD_SIM_IF_ANY",
            "bundle": bundle,
            "level": target,
            "skills": [],
            "skipped_skill_ids": sorted(set(omit)),
            "skip_dispatch": True,
            "steps": [],
            "game_mode": mode,
            "mode_agnostic": True,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "not_bi005": True,
            "note": "Completion ledger shows dispatched commands only, not panel-proved levels; review before PASS.",
        }

    template = str(seq["skill_command_template"])
    interleave_n = int(reward.get("interleave_every_n_skill_commands") or 5)
    accept_step = {
        "step": "ACCEPT_OFFERED_REWARD_TRAIT",
        "required": bool(accept),
        "confirm_key": reward.get("primary_confirm_key", "ENTER"),
        "never_press_cancel": True,
        "max_rounds": int(reward.get("max_accept_rounds_per_batch") or 3),
        "ok_click_client_fractions": list(
            reward.get("ok_click_client_fractions") or [[0.50, 0.72]]
        ),
        "refuse_blind_ok": True,
        "forbidden_reward_traits": list(reward.get("forbidden_reward_traits") or []),
        "harmful_trait_action": str(reward.get("harmful_trait_action") or "ESCAPE_CANCEL_DIALOG"),
        "harmful_trait_fallback_action": str(reward.get("harmful_trait_fallback_action") or "HOLD"),
        "policy_owner": "betterinstincts.diy_skill_force.decide_reward_dialog",
        "note": (
            "Only a fresh classified non-harmful mastery/reward trait may be OK'd; "
            "Evil/harmful -> ESCAPE_CANCEL_DIALOG or HOLD, never Enter/OK; benign traits never Cancel"
        ),
    }
    steps = [
        {
            "step": "REQUIRE_FOREGROUND_SIMS",
            "required": True,
            "note": "Soft focus only — never force F1 / leave Build while operator builds",
        },
        {
            "step": "PRESERVE_OPERATOR_MODE",
            "required": True,
            "game_mode": mode,
            "note": "Tandem with Build/Buy/Live; never_force_mode_switch",
        },
        {
            "step": "REQUIRE_ACTIVE_SIM_SELECTION",
            "required": True,
            "note": seq.get(
                "selection_note",
                "Commands apply to the currently selected Sim/Servo only.",
            ),
        },
        {
            "step": "OPEN_CHEAT_CONSOLE",
            "chord": list(seq["open_console_chord"]),
            "chord_label": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
            "required": True,
        },
        {
            "step": "ACTIVATE_TESTING_CHEATS",
            "command": seq["activate_testing_cheats"],
            "alias": seq.get("activate_testing_cheats_alias"),
            "required": True,
        },
    ]
    resolved = []
    for idx, row in enumerate(skills, start=1):
        skill_stat = str(row["skill_stat"])
        cmd = template.format(skill_stat=skill_stat, level=target)
        steps.append(
            {
                "step": "SET_SKILL_LEVEL",
                "command": cmd,
                "skill_id": row["id"],
                "display_name": row.get("display_name"),
                "skill_stat": skill_stat,
                "level": target,
                "required": True,
            }
        )
        resolved.append(
            {
                "id": row["id"],
                "display_name": row.get("display_name"),
                "skill_stat": skill_stat,
                "level": target,
                "pack_hint": row.get("pack_hint"),
                "diy_role": row.get("diy_role"),
            }
        )
        if accept and interleave_n > 0 and idx % interleave_n == 0:
            steps.append(dict(accept_step))
    if accept:
        steps.append({**accept_step, "note": "Final reward-trait OK sweep after skill lines"})
    if seq.get("close_console_optional", True):
        steps.append(
            {
                "step": "CLOSE_CHEAT_CONSOLE",
                "key": seq["close_console_key"],
                "required": False,
                "note": "Optional — avoid Esc spam that opens pause MENU while building",
            }
        )
    dispatch_policy = skills_panel_observation_policy(
        purpose="dispatch",
        live_paused=True,
        precious_time=True,
        concurrent_live_cert=True,
        main_goal_unfinished=True,
        cfg=cfg,
    )
    verify_policy = skills_panel_observation_policy(
        purpose="verify",
        live_paused=True,
        precious_time=True,
        concurrent_live_cert=True,
        main_goal_unfinished=True,
        cfg=cfg,
    )
    steps.append(
        {
            "step": "KEEP_PAUSED",
            "required": True,
            "action": dispatch_policy["action"],
            "purpose": "dispatch",
            "note": dispatch_policy["note"],
        }
    )
    steps.append(
        {
            "step": "PLAY_BRIEF_OBSERVE_REPAUSE",
            "required": False,
            "action": verify_policy["action"],
            "purpose": "verify",
            "play_seconds": verify_policy["play_seconds"],
            "play_key": verify_policy["play_key"],
            "pause_key": verify_policy["pause_key"],
            "always_repause": True,
            "panel_status_if_skipped": "UNPROVEN_STALE",
            "note": verify_policy["note"],
        }
    )
    return {
        "state": "DIY_SKILL_FORCE_PLAN_READY",
        "next_gate": "EXECUTE_DIY_SKILL_FORCE",
        "bundle": bundle,
        "level": target,
        "skills": resolved,
        "skipped_skill_ids": sorted(set(omit)),
        "skip_dispatch": False,
        "game_mode": mode,
        "mode_agnostic": True,
        "accept_reward_dialogs": accept,
        "open_console": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
        "typing_owner": seq.get("typing_owner", "scripts/win32_input.type_text"),
        "skills_panel_observation": {
            "dispatch": dispatch_policy,
            "verify": verify_policy,
        },
        "keep_paused_default": True,
        "steps": steps,
        "forbidden": list(seq.get("forbidden") or []),
        "invariants": list(cfg.get("invariants") or []),
        "ui_forbids": dict(cfg.get("ui_forbids") or {}),
        "trait_safety": dict(cfg.get("trait_safety") or {}),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "not_bi005": True,
        "not_practice_skill": True,
        "required_residual_skills": required_residual_skills(cfg),
    }


def plan_household_skill_force(
    *,
    members: int,
    skill_ids: Optional[Sequence[str]] = None,
    bundle: Optional[str] = None,
    level: Optional[int] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
    accept_reward_dialogs: Optional[bool] = None,
    session_id: Optional[str] = None,
    member_keys: Optional[Sequence[str]] = None,
    completion_ledger: Optional[Mapping[str, object]] = None,
    redo: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Plan skill-round-robin force across every observed household portrait.

    ``members`` is the exact Live portrait count (any N in contract min..max).
    Default dispatch: for each skill, visit every member (SPACE between cells),
    then the next skill — until all requested skills are at target. Does not
    invent household size. Completion ledger skips already-maxed skill×member
    cells while still advancing selection so Space stays in sync.
    """
    cfg = cfg or load_contract()
    ht = cfg.get("household_traverse") or {}
    min_m = int(ht.get("min_members") or 1)
    # N = observed household size. sanity_max is anti-runaway only — not a
    # preferred Sims household ceiling (8/10 pedantry rejected).
    max_m = int(ht.get("sanity_max_members") or ht.get("max_members") or 100)
    count = int(members)
    if isinstance(members, bool) or count < min_m or count > max_m:
        raise DiySkillForceError("INVALID_HOUSEHOLD_MEMBER_COUNT")
    if bundle is None and not skill_ids:
        bundle = "full_unlock"
    labels: list[str | None]
    if member_keys is None:
        labels = [None] * count
    else:
        labels = [str(k) if k is not None else None for k in member_keys]
        if len(labels) != count:
            raise DiySkillForceError("HOUSEHOLD_MEMBER_KEYS_COUNT_MISMATCH")

    probe = plan_skill_force(
        skill_ids=skill_ids,
        bundle=bundle,
        level=level,
        player_directed=player_directed,
        game_mode=game_mode,
        accept_reward_dialogs=accept_reward_dialogs,
        cfg=cfg,
    )
    if probe.get("state") == "YIELD_TO_PLAYER":
        return {
            **probe,
            "household_members": count,
            "member_plans": [],
            "dispatch_units": [],
            "dispatch_order": "skill_round_robin",
        }

    target = int(probe.get("level") or cfg["inject_sequence"]["default_level"])
    ledger = completion_ledger if completion_ledger is not None else empty_completion_ledger()
    skill_rows = list(probe.get("skills") or [])
    member_keys_resolved = [
        completion_member_key(session_id, index, labels[index]) for index in range(count)
    ]
    completed_by_member: list[set[str]] = []
    for mkey in member_keys_resolved:
        if redo:
            completed_by_member.append(set())
        else:
            completed_by_member.append(
                completed_skill_ids_for_member(ledger, mkey, target_level=target)
            )

    select_step = {
        "step": "SELECT_NEXT_HOUSEHOLD_SIM",
        "key": ht.get("next_member_key", "SPACE"),
        "chord": list(ht.get("next_member_chord") or ["SPACE"]),
        "close_console_before": bool(ht.get("close_console_before_space", True)),
        "required": True,
        "note": "Space to next portrait (wraps); keeps skill-round-robin selection aligned",
    }

    units: list[dict] = []
    cells_needing = 0
    for skill_row in skill_rows:
        sid = str(skill_row["id"])
        for index in range(count):
            mkey = member_keys_resolved[index]
            already = sid in completed_by_member[index]
            if already:
                unit_plan = {
                    "state": "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED",
                    "skip_dispatch": True,
                    "skills": [],
                    "level": target,
                }
            else:
                unit_plan = plan_skill_force(
                    skill_ids=[sid],
                    bundle=None,
                    level=level,
                    player_directed=player_directed,
                    game_mode=game_mode,
                    accept_reward_dialogs=accept_reward_dialogs,
                    cfg=cfg,
                )
                cells_needing += 1
            units.append(
                {
                    "skill_id": sid,
                    "skill_stat": skill_row.get("skill_stat"),
                    "display_name": skill_row.get("display_name"),
                    "member_index": index,
                    "member_key": mkey,
                    "skip_dispatch": already,
                    "select_before": None if not units else dict(select_step),
                    "plan": unit_plan,
                }
            )

    slots: list[dict] = []
    members_needing = 0
    for index in range(count):
        mkey = member_keys_resolved[index]
        omit = sorted(completed_by_member[index])
        remaining = [str(s["id"]) for s in skill_rows if str(s["id"]) not in completed_by_member[index]]
        skip = not remaining
        if not skip:
            members_needing += 1
        slots.append(
            {
                "member_index": index,
                "member_key": mkey,
                "skip_dispatch": skip,
                "skipped_skill_ids": omit,
                "remaining_skill_ids": remaining,
                "select": None if index == 0 else dict(select_step),
                "plan": {
                    "state": (
                        "SKILL_FORCE_MEMBER_NO_PENDING_DISPATCH_UNVERIFIED"
                        if skip
                        else "DIY_SKILL_FORCE_PLAN_READY"
                    ),
                    "skip_dispatch": skip,
                    "skills": [
                        {
                            "id": s["id"],
                            "skill_stat": s.get("skill_stat"),
                            "level": target,
                        }
                        for s in skill_rows
                        if str(s["id"]) not in completed_by_member[index]
                    ],
                    "level": target,
                },
            }
        )

    # DISPATCHED is a console-typing receipt, never Skills-panel max proof.
    # Do not return an invented already-maxed observation from ledger skips.
    state = (
        "HOUSEHOLD_SKILL_FORCE_NO_PENDING_DISPATCH_UNVERIFIED"
        if cells_needing == 0
        else "HOUSEHOLD_SKILL_FORCE_PLAN_READY"
    )
    return {
        "state": state,
        "next_gate": (
            "REVIEW_SKILLS_PANEL_BEFORE_MAX_CLAIM"
            if cells_needing == 0
            else "EXECUTE_HOUSEHOLD_SKILL_FORCE"
        ),
        "household_members": count,
        "members_needing_work": members_needing,
        "cells_needing_work": cells_needing,
        "max_level_verified_by_ledger": False,
        "dispatch_order": "skill_round_robin",
        "dispatch_units": units,
        "household_traverse": {
            "next_member_key": ht.get("next_member_key", "SPACE"),
            "min_members": min_m,
            "sanity_max_members": max_m,
            "observed_n": count,
            "dispatch_order": "skill_round_robin",
            "skip_already_maxed_cells": True,
            "note": (
                "N is observed portrait count; sanity_max is anti-runaway only; "
                "one skill for every member, then the next skill; Space between cells"
            ),
        },
        "completion_ledger": {
            "schema": COMPLETION_SCHEMA,
            "session_id": session_id,
            "redo": bool(redo),
            "skip_already_maxed": not bool(redo),
        },
        "bundle": probe.get("bundle") or bundle,
        "requested_skill_ids": list(skill_ids) if skill_ids else None,
        "level": target,
        "skills": skill_rows,
        "required_residual_skills": required_residual_skills(cfg),
        "member_plans": slots,
        "game_mode": probe.get("game_mode"),
        "mode_agnostic": True,
        "accept_reward_dialogs": probe.get("accept_reward_dialogs"),
        "typing_owner": probe.get("typing_owner"),
        "skills_panel_observation": probe.get("skills_panel_observation"),
        "keep_paused_default": True,
        "forbidden": probe.get("forbidden"),
        "ui_forbids": probe.get("ui_forbids"),
        "trait_safety": probe.get("trait_safety"),
        "invariants": probe.get("invariants"),
        "execute_allowed": False,
        "proof_ceiling": probe.get("proof_ceiling"),
        "not_bi005": True,
        "not_practice_skill": True,
        "async_detach_supported": False,
    }


def steps_to_commands(plan: Mapping[str, object]) -> list[str]:
    """Flatten plan steps into console command strings (skips key-only steps)."""
    out: list[str] = []
    for step in plan.get("steps") or []:
        if not isinstance(step, Mapping):
            continue
        cmd = step.get("command")
        if isinstance(cmd, str) and cmd.strip():
            out.append(cmd.strip())
    if not out or out[0] != "testingcheats enabled true":
        raise DiySkillForceError("PLAN_MUST_START_WITH_TESTINGCHEATS_ENABLED_TRUE")
    if not any(c.startswith("stats.set_skill_level ") for c in out[1:]):
        raise DiySkillForceError("PLAN_MISSING_SKILL_COMMANDS")
    return out
