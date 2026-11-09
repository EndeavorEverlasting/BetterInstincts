"""Skill-force planner: DIY maker set plus full adult unlock catalog.

P95/P100 stack: soft-focus Sims → Ctrl+Shift+C → testingcheats enabled true →
stats.set_skill_level <stat> <N> for each resolved skill → bounded
ACCEPT_OFFERED_REWARD_TRAIT (OK on offered mastery/reward traits).
Household: count N members → Space-traverse each → dispatch (opt-in --detach).
Required residuals Cooking/Fitness/Natural Living always re-applied at end.
Mode-agnostic; never force F1 while the operator builds.

Bundles: diy_maker / servo_core / creative / social / athletic / residual_core /
full_unlock. Library plans only; scripts/diy_skill_force.py owns typing + OK
accept + household async worker. Never edits saves. Never practice_skill / BI-005.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "diy-skill-force.v1.json"
MAX_BYTES = 96_000
DEFAULT_REQUIRED_RESIDUALS = ("cooking", "fitness", "natural_living")


class DiySkillForceError(ValueError):
    pass


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
    cfg: Optional[dict] = None,
) -> list[dict]:
    """Resolve catalog rows from explicit ids and/or a named bundle."""
    cfg = cfg or load_contract()
    index = _skill_index(cfg)
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(sid: str) -> None:
        key = str(sid).strip().lower()
        if not key:
            return
        if key not in index:
            raise DiySkillForceError("UNKNOWN_DIY_SKILL:" + key)
        if key not in seen:
            seen.add(key)
            ordered.append(key)

    if bundle is not None:
        bkey = str(bundle).strip()
        brow = (cfg.get("bundles") or {}).get(bkey)
        if not isinstance(brow, Mapping):
            raise DiySkillForceError("UNKNOWN_DIY_BUNDLE:" + bkey)
        for sid in brow.get("skill_ids") or []:
            _add(str(sid))
    if skill_ids:
        for sid in skill_ids:
            _add(str(sid))
    if not ordered:
        # All-the-way unlock is the operator default when nothing is named.
        default_bundle = "full_unlock" if "full_unlock" in cfg["bundles"] else "diy_maker"
        for sid in (cfg["bundles"][default_bundle].get("skill_ids") or []):
            _add(str(sid))
    # Operator miss set: always re-queue residuals at the end of full_unlock so
    # mid-batch console truncation cannot leave Cooking/Fitness/Natural Living at 1.
    if bundle == "full_unlock" or (bundle is None and not skill_ids):
        for sid in required_residual_skills(cfg):
            key = str(sid).strip().lower()
            if key in index and key in seen:
                # Force a second dispatch pass for residuals already in the set.
                ordered.append(key)
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

    skills = resolve_skills(skill_ids=skill_ids, bundle=bundle, cfg=cfg)
    default_level = int(seq["default_level"])
    min_level = int(seq["min_level"])
    max_level = int(seq["max_level"])
    target = default_level if level is None else int(level)
    if isinstance(level, bool) or target < min_level or target > max_level:
        raise DiySkillForceError("INVALID_SKILL_LEVEL")

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
    cfg: Optional[dict] = None,
) -> dict:
    """Plan skill-force across every observed household member.

    ``members`` is the exact Live portrait count (any N in contract min..max).
    Traverse uses SPACE between members. Does not invent household size.
    """
    cfg = cfg or load_contract()
    ht = cfg.get("household_traverse") or {}
    min_m = int(ht.get("min_members") or 1)
    max_m = int(ht.get("max_members") or 8)
    count = int(members)
    if isinstance(members, bool) or count < min_m or count > max_m:
        raise DiySkillForceError("INVALID_HOUSEHOLD_MEMBER_COUNT")
    if bundle is None and not skill_ids:
        bundle = "full_unlock"
    member_plan = plan_skill_force(
        skill_ids=skill_ids,
        bundle=bundle,
        level=level,
        player_directed=player_directed,
        game_mode=game_mode,
        accept_reward_dialogs=accept_reward_dialogs,
        cfg=cfg,
    )
    if member_plan.get("state") == "YIELD_TO_PLAYER":
        return {
            **member_plan,
            "household_members": count,
            "member_plans": [],
        }
    slots: list[dict] = []
    for index in range(count):
        slots.append(
            {
                "member_index": index,
                "select": (
                    None
                    if index == 0
                    else {
                        "step": "SELECT_NEXT_HOUSEHOLD_SIM",
                        "key": ht.get("next_member_key", "SPACE"),
                        "chord": list(ht.get("next_member_chord") or ["SPACE"]),
                        "close_console_before": bool(ht.get("close_console_before_space", True)),
                        "required": True,
                    }
                ),
                "plan": member_plan,
            }
        )
    return {
        "state": "HOUSEHOLD_SKILL_FORCE_PLAN_READY",
        "next_gate": "EXECUTE_HOUSEHOLD_SKILL_FORCE",
        "household_members": count,
        "household_traverse": {
            "next_member_key": ht.get("next_member_key", "SPACE"),
            "min_members": min_m,
            "max_members": max_m,
        },
        "bundle": member_plan.get("bundle"),
        "level": member_plan.get("level"),
        "skills": member_plan.get("skills"),
        "required_residual_skills": required_residual_skills(cfg),
        "member_plans": slots,
        "game_mode": member_plan.get("game_mode"),
        "mode_agnostic": True,
        "accept_reward_dialogs": member_plan.get("accept_reward_dialogs"),
        "typing_owner": member_plan.get("typing_owner"),
        "skills_panel_observation": member_plan.get("skills_panel_observation"),
        "keep_paused_default": True,
        "forbidden": member_plan.get("forbidden"),
        "invariants": member_plan.get("invariants"),
        "execute_allowed": False,
        "proof_ceiling": member_plan.get("proof_ceiling"),
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
