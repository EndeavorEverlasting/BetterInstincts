"""Skill-force planner: DIY maker set plus full adult unlock catalog.

P95/P100 stack: soft-focus Sims → Ctrl+Shift+C → testingcheats enabled true →
stats.set_skill_level <stat> <N> for each resolved skill → bounded
ACCEPT_OFFERED_REWARD_TRAIT (OK on offered mastery/reward traits).
Household: count N members → Space-traverse each → dispatch (opt-in --detach).
Required residuals Cooking/Fitness/Natural Living always re-applied at end.
Completion ledger: skip already-DISPATCHED skills; Space past members with
nothing left. Mode-agnostic; never force F1 while the operator builds.

Bundles: diy_maker / servo_core / creative / social / athletic / residual_core /
full_unlock. Library plans only; scripts/diy_skill_force.py owns typing + OK
accept + household async worker. Never edits saves. Never practice_skill / BI-005.
"""
from __future__ import annotations

import json
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
            "Not Skills-panel PASS. PANEL_OBSERVED_MAX may be set after LOCAL_OBSERVED."
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
    return cfg


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
            "state": "SKILL_FORCE_MEMBER_ALREADY_MAXED",
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
            "note": "Completion ledger shows all requested skills already at target; Space to next needing Sim.",
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
        "note": "Operator-authorized OK on offered mastery/reward traits; never Cancel",
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
    """Plan skill-force across every observed household member.

    ``members`` is the exact Live portrait count (any N in contract min..max).
    Traverse uses SPACE between members. Does not invent household size.
    Completion ledger omits already-maxed skills; fully-done members are
    marked skip_dispatch so execute Spaces to the next Sim that still needs work.
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
        }

    target = int(probe.get("level") or cfg["inject_sequence"]["default_level"])
    ledger = completion_ledger if completion_ledger is not None else empty_completion_ledger()
    slots: list[dict] = []
    needing = 0
    for index in range(count):
        mkey = completion_member_key(session_id, index, labels[index])
        omit: list[str] = []
        if not redo:
            omit = sorted(
                completed_skill_ids_for_member(ledger, mkey, target_level=target)
            )
        member_plan = plan_skill_force(
            skill_ids=skill_ids,
            bundle=bundle,
            level=level,
            player_directed=player_directed,
            game_mode=game_mode,
            accept_reward_dialogs=accept_reward_dialogs,
            omit_skill_ids=omit,
            cfg=cfg,
        )
        skip = bool(member_plan.get("skip_dispatch")) or member_plan.get("state") == (
            "SKILL_FORCE_MEMBER_ALREADY_MAXED"
        )
        if not skip:
            needing += 1
        slots.append(
            {
                "member_index": index,
                "member_key": mkey,
                "skip_dispatch": skip,
                "skipped_skill_ids": omit,
                "remaining_skill_ids": [s["id"] for s in (member_plan.get("skills") or [])],
                "select": (
                    None
                    if index == 0
                    else {
                        "step": "SELECT_NEXT_HOUSEHOLD_SIM",
                        "key": ht.get("next_member_key", "SPACE"),
                        "chord": list(ht.get("next_member_chord") or ["SPACE"]),
                        "close_console_before": bool(ht.get("close_console_before_space", True)),
                        "required": True,
                        "note": "Space to next portrait; skip console when member already maxed",
                    }
                ),
                "plan": member_plan,
            }
        )
    state = (
        "HOUSEHOLD_SKILL_FORCE_ALL_MEMBERS_ALREADY_MAXED"
        if needing == 0
        else "HOUSEHOLD_SKILL_FORCE_PLAN_READY"
    )
    return {
        "state": state,
        "next_gate": (
            "NONE_ALL_MEMBERS_COMPLETE"
            if needing == 0
            else "EXECUTE_HOUSEHOLD_SKILL_FORCE"
        ),
        "household_members": count,
        "members_needing_work": needing,
        "household_traverse": {
            "next_member_key": ht.get("next_member_key", "SPACE"),
            "min_members": min_m,
            "sanity_max_members": max_m,
            "observed_n": count,
            "skip_already_maxed_members": True,
            "note": (
                "N is observed portrait count; sanity_max is anti-runaway only; "
                "Space past members with no remaining skills"
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
        "skills": probe.get("skills"),
        "required_residual_skills": required_residual_skills(cfg),
        "member_plans": slots,
        "game_mode": probe.get("game_mode"),
        "mode_agnostic": True,
        "accept_reward_dialogs": probe.get("accept_reward_dialogs"),
        "typing_owner": probe.get("typing_owner"),
        "skills_panel_observation": probe.get("skills_panel_observation"),
        "keep_paused_default": True,
        "forbidden": probe.get("forbidden"),
        "invariants": probe.get("invariants"),
        "execute_allowed": False,
        "proof_ceiling": probe.get("proof_ceiling"),
        "not_bi005": True,
        "not_practice_skill": True,
        "async_detach_supported": True,
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
