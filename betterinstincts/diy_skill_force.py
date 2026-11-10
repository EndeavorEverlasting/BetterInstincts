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
    roster = raw.get("household_roster")
    if isinstance(roster, Mapping):
        out["household_roster"] = dict(roster)
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


def resolve_skill_ref(token: str, *, cfg: Optional[dict] = None) -> dict:
    """Map a skill id or Skills-panel display name to catalog id/stat."""
    cfg = cfg or load_contract()
    raw = str(token or "").strip()
    if not raw:
        raise DiySkillForceError("SKILL_REF_REQUIRED")
    needle = raw.lower().replace(" ", "_")
    skills = cfg.get("skill_catalog") or cfg.get("skills") or []
    if not isinstance(skills, list):
        raise DiySkillForceError("SKILL_CATALOG_INVALID")
    for row in skills:
        if not isinstance(row, Mapping):
            continue
        sid = str(row.get("id") or "").strip().lower()
        display = str(row.get("display_name") or "").strip().lower()
        display_key = display.replace(" ", "_")
        if needle in {sid, display, display_key}:
            return {
                "skill_id": sid,
                "skill_stat": str(row.get("skill_stat") or ""),
                "display_name": str(row.get("display_name") or sid),
            }
    raise DiySkillForceError(f"UNKNOWN_SKILL_REF:{raw}")


CHEAT_COMMAND_TEMPLATE = "stats.set_skill_level {skill_stat} {level}"


def canonical_skill_commands(
    *,
    target_level: int = 10,
    bundle: str | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Canonical id → skill_stat → cheat line for every catalog (or bundle) skill.

    Never invent stats; skill_catalog is the only spelling authority
    (e.g. Major_MediaProduction, not Major_MediaProducton).
    """
    cfg = cfg or load_contract()
    target = int(target_level)
    if target < 1 or target > 10:
        raise DiySkillForceError("TARGET_LEVEL_OUT_OF_RANGE")
    template = str(
        (
            (cfg.get("target_sim_algorithm") or {})
            .get("lean_panel_sequence", {})
            .get("skills_panel_inventory", {})
            .get("cheat_template")
        )
        or CHEAT_COMMAND_TEMPLATE
    )
    if bundle:
        rows = resolve_skills(bundle=str(bundle), cfg=cfg)
    else:
        rows = [
            dict(r)
            for r in (cfg.get("skill_catalog") or [])
            if isinstance(r, Mapping) and r.get("id") and r.get("skill_stat")
        ]
    commands: list[dict] = []
    for row in rows:
        sid = str(row.get("id") or "").strip().lower()
        stat = str(row.get("skill_stat") or "").strip()
        if not sid or not stat:
            continue
        cmd = template.format(skill_stat=stat, level=target)
        entry = {
            "skill_id": sid,
            "display_name": str(row.get("display_name") or sid),
            "skill_stat": stat,
            "level": target,
            "command": cmd,
        }
        typos = row.get("typo_guard")
        if isinstance(typos, list) and typos:
            entry["typo_guard"] = [str(t) for t in typos]
        commands.append(entry)
    return {
        "schema": "betterinstincts.canonical-skill-commands/v1",
        "state": "CANONICAL_SKILL_COMMANDS_READY",
        "target_level": target,
        "bundle": bundle,
        "count": len(commands),
        "commands": commands,
        "owner": "contracts/diy-skill-force.v1.json#skill_catalog",
    }


def gap_targets_from_observed_levels(
    observed_levels: Mapping[str, int],
    *,
    target_level: int = 10,
    bundle: str | None = "full_unlock",
    cfg: Optional[dict] = None,
) -> dict:
    """Non-yellow / below-target Skills-panel rows → force targets + cheat lines.

    ``observed_levels`` maps skill_id (or display name) → LOCAL_OBSERVED level.
    Missing catalog skills are treated as unknown gaps (level 0) so we never
    forget an unlisted row after a full scroll inventory.
    """
    cfg = cfg or load_contract()
    target = int(target_level)
    canon = canonical_skill_commands(
        target_level=target, bundle=bundle, cfg=cfg
    )
    observed: dict[str, int] = {}
    for key, level in (observed_levels or {}).items():
        ref = resolve_skill_ref(str(key), cfg=cfg)
        observed[str(ref["skill_id"])] = int(level)
    gaps: list[dict] = []
    maxed: list[str] = []
    for row in canon["commands"]:
        sid = str(row["skill_id"])
        level = int(observed.get(sid, 0))
        if level >= target:
            maxed.append(sid)
            continue
        gaps.append(
            {
                "skill_id": sid,
                "display_name": row["display_name"],
                "skill_stat": row["skill_stat"],
                "observed_level": level,
                "target_level": target,
                "gap_cue": "NON_YELLOW_ROW_BELOW_TARGET",
                "command": row["command"],
            }
        )
    return {
        "schema": "betterinstincts.skills-gap-targets/v1",
        "state": "SKILLS_GAP_TARGETS_READY",
        "target_level": target,
        "bundle": bundle,
        "maxed_count": len(maxed),
        "gap_count": len(gaps),
        "maxed_skill_ids": maxed,
        "gaps": gaps,
        "commands": [g["command"] for g in gaps],
        "note": (
            "Scroll the Skills panel (burger expand + wheel) so every row is "
            "seen; gold/yellow checkmark rows are maxed; non-yellow are gaps."
        ),
    }


def member_observed_levels_from_ledger(
    ledger: Mapping,
    member_key: str,
) -> dict[str, int]:
    """Read LOCAL_OBSERVED levels from the completion ledger (key: ``level``)."""
    members = ledger.get("members") if isinstance(ledger, Mapping) else None
    row = members.get(str(member_key)) if isinstance(members, Mapping) else None
    skills = row.get("skills") if isinstance(row, Mapping) else None
    out: dict[str, int] = {}
    if not isinstance(skills, Mapping):
        return out
    for sid, cell in skills.items():
        if not isinstance(cell, Mapping):
            continue
        status = str(cell.get("status") or "")
        if status == "PANEL_OBSERVED_MAX":
            out[str(sid).strip().lower()] = int(cell.get("level") or 10)
        elif cell.get("level") is not None:
            out[str(sid).strip().lower()] = int(cell["level"])
    return out


def resolve_force_gap_commands(
    *,
    bundle: str = "full_unlock",
    target_level: int = 10,
    observed_levels: Mapping[str, int] | None = None,
    redo: bool = False,
    always_include: Sequence[str] | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Canonical cheat lines for gaps (or full bundle when ``redo``).

    ``always_include`` forces named skill_ids even if ledger says max
    (e.g. sticky Major_MediaProduction / Major_Photography).
    """
    cfg = cfg or load_contract()
    always = {
        str(resolve_skill_ref(s, cfg=cfg)["skill_id"])
        for s in (always_include or [])
    }
    if redo:
        canon = canonical_skill_commands(
            target_level=target_level, bundle=bundle, cfg=cfg
        )
        rows = list(canon["commands"])
    else:
        gaps = gap_targets_from_observed_levels(
            observed_levels or {},
            target_level=target_level,
            bundle=bundle,
            cfg=cfg,
        )
        rows = [
            {
                "skill_id": g["skill_id"],
                "display_name": g["display_name"],
                "skill_stat": g["skill_stat"],
                "level": target_level,
                "command": g["command"],
                "observed_level": g["observed_level"],
            }
            for g in gaps["gaps"]
        ]
        if always:
            have = {r["skill_id"] for r in rows}
            for sid in sorted(always):
                if sid in have:
                    continue
                ref = resolve_skill_ref(sid, cfg=cfg)
                rows.append(
                    {
                        "skill_id": str(ref["skill_id"]),
                        "display_name": str(ref.get("display_name") or sid),
                        "skill_stat": str(ref["skill_stat"]),
                        "level": int(target_level),
                        "command": CHEAT_COMMAND_TEMPLATE.format(
                            skill_stat=ref["skill_stat"], level=int(target_level)
                        ),
                        "observed_level": int((observed_levels or {}).get(sid, 0)),
                        "forced_include": True,
                    }
                )
    seen: set[str] = set()
    deduped: list[dict] = []
    for row in rows:
        stat = str(row["skill_stat"])
        if stat in seen:
            continue
        seen.add(stat)
        deduped.append(row)
    return {
        "schema": "betterinstincts.force-gap-commands/v1",
        "state": "FORCE_GAP_COMMANDS_READY",
        "bundle": bundle,
        "target_level": int(target_level),
        "redo": bool(redo),
        "count": len(deduped),
        "commands": [r["command"] for r in deduped],
        "rows": deduped,
        "media_production_canonical": "stats.set_skill_level Major_MediaProduction 10",
        "note": (
            "Never invent skill_stat spelling. Media Production is "
            "Major_MediaProduction (with i)."
        ),
    }


def plan_force_gaps_beat(
    *,
    member_key: str,
    portrait_client_xy: Sequence[int],
    bundle: str = "full_unlock",
    target_level: int = 10,
    redo: bool = False,
    always_include: Sequence[str] | None = None,
    observed_levels: Mapping[str, int] | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Durable lean beat: select portrait → force gap cheats → play → scroll inventory."""
    cfg = cfg or load_contract()
    if not isinstance(portrait_client_xy, (list, tuple)) or len(portrait_client_xy) != 2:
        raise DiySkillForceError("PORTRAIT_CLIENT_XY_REQUIRED")
    gaps = resolve_force_gap_commands(
        bundle=bundle,
        target_level=target_level,
        observed_levels=observed_levels,
        redo=redo,
        always_include=always_include,
        cfg=cfg,
    )
    return {
        "schema": "betterinstincts.force-gaps-beat/v1",
        "state": "FORCE_GAPS_BEAT_READY",
        "execute_allowed": False,
        "member_key": str(member_key),
        "portrait_client_xy": [int(portrait_client_xy[0]), int(portrait_client_xy[1])],
        "gaps": gaps,
        "order": [
            "IDLE_15S",
            "BORROW_SIMS",
            "ONE_PINNED_TERRAIN_ARM",
            "ENTER_CENTER_ACTIVE_SIM",
            "LEFT_CLICK_PORTRAIT",
            "PORTRAIT_RMB_FOLLOW_IF_STREET_DRIFT",
            "ENTER_RECENTER",
            "J_WORK_NAME_PROOF",
            "CONSOLE_STRIP_THEN_TYPE_GAP_COMMANDS",
            "CLOSE_CONSOLE",
            "RESTORE_OPERATOR",
            "PLAY_BRIEF",
            "L_SKILLS_BURGER_SCROLL_INVENTORY",
            "PANEL_RECORD_NON_YELLOW_GAPS",
        ],
        "forbidden": [
            "MAP_CLICK_WANDER",
            "V_VIDEO_RECORD",
            "TYPE_WITHOUT_CONSOLE_STRIP",
            "INVENTED_OPERATOR_BUSY_WHEN_AWAY",
            "FIRST_VIEWPORT_ONLY_SKILLS_READ",
        ],
        "inventory": plan_skills_panel_inventory(cfg=cfg),
        "owner": "scripts.diy_skill_force.execute_force_gaps",
    }


def plan_skills_panel_scroll(
    *,
    direction: str = "DOWN",
    pages: int = 1,
    cfg: Optional[dict] = None,
) -> dict:
    """Plan Skills-list scroll so every row can be seen (no forgotten skills)."""
    cfg = cfg or load_contract()
    inv = (
        (cfg.get("target_sim_algorithm") or {})
        .get("lean_panel_sequence", {})
        .get("skills_panel_inventory", {})
    )
    scroll = inv.get("scroll") if isinstance(inv, Mapping) else {}
    scroll = scroll if isinstance(scroll, Mapping) else {}
    direction_u = str(direction or "DOWN").strip().upper()
    if direction_u not in {"DOWN", "UP"}:
        raise DiySkillForceError("SKILLS_SCROLL_DIRECTION_MUST_BE_UP_OR_DOWN")
    pages_i = max(1, min(int(pages), int(scroll.get("max_pages") or 10)))
    notches = int(scroll.get("wheel_notches_per_page") or 6)
    xy = scroll.get("list_client_xy_1920x1080") or [1700, 520]
    if not isinstance(xy, (list, tuple)) or len(xy) != 2:
        xy = [1700, 520]
    # send_wheel: negative delta scrolls content down (toward later alphabet)
    wheel_sign = -1 if direction_u == "DOWN" else 1
    return {
        "schema": "betterinstincts.skills-panel-scroll/v1",
        "state": "SKILLS_PANEL_SCROLL_READY",
        "execute_allowed": False,
        "direction": direction_u,
        "pages": pages_i,
        "wheel_notches_per_page": notches,
        "total_wheel_notches": pages_i * notches * wheel_sign,
        "list_client_xy": [int(xy[0]), int(xy[1])],
        "helper": "scripts.win32_input.send_wheel",
        "order": [
            "ENSURE_SKILLS_PANEL_OPEN_L",
            "BURGER_EXPAND_IF_NEEDED",
            f"WHEEL_{direction_u}_PAGES_{pages_i}",
            "READ_VISIBLE_ROWS_NON_YELLOW_ARE_GAPS",
        ],
        "forbidden": ["MAP_CLICK_WANDER", "CAMERA_ZOOM_TO_READ_SKILLS"],
    }


def plan_skills_panel_inventory(
    *,
    pages: int = 8,
    cfg: Optional[dict] = None,
) -> dict:
    """Burger-expand + scroll the whole Skills list; target non-yellow gaps."""
    cfg = cfg or load_contract()
    down = plan_skills_panel_scroll(direction="DOWN", pages=pages, cfg=cfg)
    up = plan_skills_panel_scroll(direction="UP", pages=min(2, pages), cfg=cfg)
    return {
        "schema": "betterinstincts.skills-panel-inventory/v1",
        "state": "SKILLS_PANEL_INVENTORY_READY",
        "execute_allowed": False,
        "canonical_commands": canonical_skill_commands(cfg=cfg),
        "steps": [
            {"step": "OPEN_SKILLS_L", "hotkey": "L"},
            {"step": "BURGER_EXPAND_MIN_TO_MAX", "owner": "plan_skills_burger_expand"},
            {"step": "SCROLL_DOWN_FULL_LIST", "plan": down},
            {
                "step": "RECORD_VISIBLE_LEVELS",
                "maxed_cue": "GOLD_ROW_CHECKMARK_LEVEL_10",
                "gap_cue": "NON_YELLOW_ROW_BELOW_TARGET",
            },
            {"step": "SCROLL_UP_RECHECK", "plan": up},
            {
                "step": "RESOLVE_GAP_TARGETS",
                "owner": "gap_targets_from_observed_levels",
            },
            {"step": "FORCE_GAP_COMMANDS_ONLY"},
        ],
        "note": (
            "Never rely on the first viewport alone. Scroll until every "
            "catalog skill is accounted for; force only non-yellow gaps."
        ),
    }


def set_household_roster(
    ledger: dict,
    *,
    session_id: str,
    members: int,
    roster_keys: Sequence[str],
    display_names: Sequence[str] | None = None,
    evidence: str = "OPERATOR_PORTRAIT_COUNT_LOCAL_OBSERVED",
) -> dict:
    """Persist observed household N and ordered portrait keys in the ledger."""
    count = int(members)
    keys = [str(k).strip() for k in roster_keys]
    if count < 1 or count > 100:
        raise DiySkillForceError("HOUSEHOLD_ROSTER_N_OUT_OF_RANGE")
    if len(keys) != count or any(not k or len(k) > 64 for k in keys):
        raise DiySkillForceError("HOUSEHOLD_ROSTER_KEYS_MUST_MATCH_N")
    if len(set(keys)) != count:
        raise DiySkillForceError("HOUSEHOLD_ROSTER_KEYS_MUST_BE_UNIQUE")
    names = list(display_names or [])
    if names and len(names) != count:
        raise DiySkillForceError("HOUSEHOLD_DISPLAY_NAMES_MUST_MATCH_N")
    roster = {
        "session_id": str(session_id).strip() or "anonymous-session",
        "members": count,
        "roster_keys": keys,
        "display_names": names,
        "evidence": str(evidence),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "N is exact Live portrait count. Never invent a fifth portrait.",
    }
    ledger["household_roster"] = roster
    return roster


def record_skill_panel_observed(
    ledger: dict,
    *,
    member_key: str,
    skill_id: str,
    level: int,
    skill_stat: str | None = None,
    display_name: str | None = None,
    target_level: int = 10,
    evidence: str = "SKILLS_PANEL_LOCAL_OBSERVED",
    note: str | None = None,
) -> dict:
    """Record one Skills-panel reading so agents stop depending on chat screenshots.

    level >= target_level => PANEL_OBSERVED_MAX (durable skip).
    Otherwise PANEL_OBSERVED with the exact observed level (not complete).
    """
    members = ledger.setdefault("members", {})
    if not isinstance(members, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    row = members.setdefault(str(member_key), {"skills": {}})
    if not isinstance(row, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    if display_name:
        row["display_name"] = str(display_name)
    skills = row.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise DiySkillForceError("COMPLETION_LEDGER_INVALID")
    sid = str(skill_id).strip().lower()
    if not sid:
        raise DiySkillForceError("SKILL_ID_REQUIRED")
    observed = int(level)
    if observed < 0 or observed > 10:
        raise DiySkillForceError("SKILL_LEVEL_OUT_OF_RANGE")
    target = int(target_level)
    prior = skills.get(sid) if isinstance(skills.get(sid), Mapping) else {}
    status = "PANEL_OBSERVED_MAX" if observed >= target else "PANEL_OBSERVED"
    entry = {
        "skill_id": sid,
        "skill_stat": str(skill_stat or prior.get("skill_stat") or ""),
        "level": observed,
        "status": status,
        "evidence": str(evidence),
        "prior_status": str(prior.get("status") or ""),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if note:
        entry["note"] = str(note)[:500]
    skills[sid] = entry
    return entry


def record_member_panel_snapshot(
    ledger: dict,
    *,
    member_key: str,
    observed_skills: Mapping[str, int],
    display_name: str | None = None,
    mark_unlisted_full_unlock_max: bool = False,
    target_level: int = 10,
    evidence: str = "SKILLS_PANEL_LOCAL_OBSERVED",
    cfg: Optional[dict] = None,
) -> dict:
    """Write many Skills-panel levels for one portrait into the completion ledger.

    When ``mark_unlisted_full_unlock_max`` is true (operator attested every listed
    skill at max and the visible list is the full unlock set), also mark remaining
    full_unlock catalog skills PANEL_OBSERVED_MAX so sequential household runs skip
    that portrait without more screenshots.
    """
    cfg = cfg or load_contract()
    written: dict[str, dict] = {}
    for token, level in dict(observed_skills).items():
        ref = resolve_skill_ref(str(token), cfg=cfg)
        written[ref["skill_id"]] = record_skill_panel_observed(
            ledger,
            member_key=member_key,
            skill_id=ref["skill_id"],
            skill_stat=ref["skill_stat"],
            display_name=display_name,
            level=int(level),
            target_level=target_level,
            evidence=evidence,
        )
    if mark_unlisted_full_unlock_max:
        full_ids = list(((cfg.get("bundles") or {}).get("full_unlock") or {}).get("skill_ids") or [])
        for sid in full_ids:
            if str(sid).strip().lower() in written:
                continue
            ref = resolve_skill_ref(str(sid), cfg=cfg)
            written[ref["skill_id"]] = record_skill_panel_observed(
                ledger,
                member_key=member_key,
                skill_id=ref["skill_id"],
                skill_stat=ref["skill_stat"],
                display_name=display_name,
                level=int(target_level),
                target_level=target_level,
                evidence=evidence + "_FULL_UNLOCK_LIST_ATTESTED",
                note="Operator attested all visible skills at max; unlisted full_unlock rows inherited PANEL_OBSERVED_MAX",
            )
    return {
        "member_key": member_key,
        "display_name": display_name,
        "skills_written": sorted(written),
        "panel_max_count": sum(1 for e in written.values() if e.get("status") == "PANEL_OBSERVED_MAX"),
        "panel_partial_count": sum(1 for e in written.values() if e.get("status") == "PANEL_OBSERVED"),
    }


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


def evaluate_member_skill_levels(
    ledger: Mapping[str, object],
    *,
    member_key: str,
    skill_ids: Sequence[str],
    target_level: int = 10,
) -> dict:
    """Evaluate whether a portrait still has skill gaps (ledger LOCAL_OBSERVED).

    PANEL_OBSERVED_MAX / complete DISPATCHED skips are treated as leveled for
    planning only — DISPATCHED alone never authorizes a Skills-panel PASS claim.
    """
    key = str(member_key).strip()
    if not key:
        raise DiySkillForceError("MEMBER_KEY_REQUIRED")
    target = int(target_level)
    members = ledger.get("members") if isinstance(ledger, Mapping) else None
    row = members.get(key) if isinstance(members, Mapping) else None
    skills = row.get("skills") if isinstance(row, Mapping) else {}
    if not isinstance(skills, Mapping):
        skills = {}
    leveled: list[dict] = []
    gaps: list[dict] = []
    unknown: list[str] = []
    for raw in skill_ids:
        sid = str(raw).strip().lower()
        if not sid:
            continue
        entry = skills.get(sid)
        if not isinstance(entry, Mapping):
            unknown.append(sid)
            gaps.append(
                {
                    "skill_id": sid,
                    "observed_level": None,
                    "status": "UNPROVEN",
                    "reason": "NO_PANEL_OR_DISPATCH_ROW",
                }
            )
            continue
        status = str(entry.get("status") or "")
        level = entry.get("level")
        observed = int(level) if isinstance(level, int) else None
        complete = skill_is_complete(entry, target_level=target)
        item = {
            "skill_id": sid,
            "observed_level": observed,
            "status": status,
            "skill_stat": str(entry.get("skill_stat") or ""),
        }
        if complete:
            leveled.append(item)
        else:
            gaps.append({**item, "reason": "BELOW_TARGET_OR_FALSIFIED"})
    return {
        "member_key": key,
        "display_name": str((row or {}).get("display_name") or "") if isinstance(row, Mapping) else "",
        "target_level": target,
        "leveled_count": len(leveled),
        "gap_count": len(gaps),
        "unknown_count": len(unknown),
        "leveled": leveled,
        "gaps": gaps,
        "all_leveled": len(gaps) == 0 and len(leveled) > 0,
        "needs_work": len(gaps) > 0,
        "proof_ceiling": "LEDGER_EVALUATION_NOT_SKILLS_PANEL_PASS",
        "note": (
            "Gaps drive target-sim select→force. DISPATCHED rows may skip typing "
            "but never authorize maximized / Skills-panel PASS narration."
        ),
    }


def detect_selected_portrait_by_white_boundaries(
    *,
    image_path: str | Path,
    portrait_slots: Sequence[Mapping[str, object]],
    band_y: tuple[int, int] = (1005, 1070),
    luma_min: int = 220,
) -> dict:
    """Locate the household portrait between two white vertical boundaries.

    Mood glow behind chips is ignored — only near-white edge columns count.
    Fail closed when no unique width pair brackets exactly one slot center.
    """
    path = Path(image_path)
    if not path.is_file() or path.is_symlink():
        raise DiySkillForceError("WHITE_BOUND_IMAGE_REQUIRED")
    try:
        from PIL import Image
    except ImportError as exc:
        raise DiySkillForceError("PIL_REQUIRED_FOR_WHITE_BOUND_DETECT") from exc
    im = Image.open(path).convert("RGB")
    px = im.load()
    w, h = im.size
    y0 = max(0, int(band_y[0]))
    y1 = min(h, int(band_y[1]))
    if y1 - y0 < 8:
        raise DiySkillForceError("WHITE_BOUND_BAND_INVALID")
    # Column score: count near-white pixels in the portrait band
    scores: list[tuple[int, int]] = []
    for x in range(w):
        hits = 0
        for y in range(y0, y1):
            r, g, b = px[x, y]
            if (r + g + b) / 3 >= luma_min and abs(r - g) < 25 and abs(g - b) < 25:
                hits += 1
        if hits >= max(6, (y1 - y0) // 4):
            scores.append((x, hits))
    if len(scores) < 2:
        return {
            "state": "NO_PORTRAIT_WIDTH_PAIR",
            "match": False,
            "white_boundaries_x": [],
            "selected_roster_index": None,
            "forbidden": ["MOOD_COLOR_AS_SELECTION"],
        }
    # Collapse adjacent columns into edge clusters; take strongest per cluster
    clusters: list[list[tuple[int, int]]] = [[scores[0]]]
    for item in scores[1:]:
        if item[0] - clusters[-1][-1][0] <= 3:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    edges = [max(c, key=lambda t: t[1])[0] for c in clusters]
    if len(edges) < 2:
        return {
            "state": "NO_PORTRAIT_WIDTH_PAIR",
            "match": False,
            "white_boundaries_x": edges,
            "selected_roster_index": None,
            "forbidden": ["MOOD_COLOR_AS_SELECTION"],
        }
    # Prefer the closest pair that brackets exactly one portrait center
    slots = []
    for row in portrait_slots:
        xy = row.get("client_xy")
        idx = row.get("roster_index")
        if not isinstance(xy, (list, tuple)) or len(xy) != 2:
            continue
        if not isinstance(idx, int):
            continue
        slots.append({"roster_index": idx, "cx": int(xy[0]), "row": row})
    best = None
    for i in range(len(edges) - 1):
        left, right = edges[i], edges[i + 1]
        if right - left < 20 or right - left > 120:
            continue
        inside = [s for s in slots if left < s["cx"] < right]
        if len(inside) == 1:
            width = right - left
            if best is None or width < best["width"]:
                best = {
                    "left": left,
                    "right": right,
                    "width": width,
                    "slot": inside[0],
                }
    if best is None:
        return {
            "state": "NO_PORTRAIT_WIDTH_PAIR",
            "match": False,
            "white_boundaries_x": edges[:8],
            "selected_roster_index": None,
            "forbidden": ["MOOD_COLOR_AS_SELECTION", "AMBIGUOUS_WHITE_PAIR"],
        }
    return {
        "state": "WHITE_BOUNDARIES_SELECTED",
        "match": True,
        "white_boundaries_x": [best["left"], best["right"]],
        "selected_roster_index": best["slot"]["roster_index"],
        "selected_client_xy": list(best["slot"]["row"].get("client_xy") or []),
        "forbidden": ["MOOD_COLOR_AS_SELECTION"],
        "proof_ceiling": "WHITE_BOUND_PIXEL_CUE_NOT_NAME_PROOF",
    }


def extrapolate_skill_iterations(
    *,
    baseline_level: int,
    after_level: int,
    target_level: int = 10,
) -> dict:
    """Memoize one measured progress step; extrapolate remaining iterations.

    remaining = ceil((target - after) / delta) when delta > 0.
    delta <= 0 → falsified (do not invent retries).
    """
    import math

    base = int(baseline_level)
    after = int(after_level)
    target = int(target_level)
    if target < 1 or target > 10:
        raise DiySkillForceError("TARGET_LEVEL_OUT_OF_RANGE")
    delta = after - base
    if after >= target:
        return {
            "state": "SKILL_AT_TARGET",
            "baseline_level": base,
            "after_level": after,
            "target_level": target,
            "delta": delta,
            "remaining_iterations": 0,
            "complete": True,
        }
    if delta <= 0:
        return {
            "state": "SKILL_PROGRESS_FALSIFIED",
            "baseline_level": base,
            "after_level": after,
            "target_level": target,
            "delta": delta,
            "remaining_iterations": None,
            "complete": False,
            "gate": "STOP_SKILL_NO_MEASURED_PROGRESS",
            "forbidden": ["GUESS_ITERATION_COUNT", "BLIND_RETRY_SAME_COMMAND"],
        }
    remaining = int(math.ceil((target - after) / delta))
    return {
        "state": "SKILL_PROGRESS_EXTRAPOLATED",
        "baseline_level": base,
        "after_level": after,
        "target_level": target,
        "delta": delta,
        "remaining_iterations": remaining,
        "complete": False,
        "note": "Apply remaining_iterations then confirm panel LOCAL_OBSERVED",
    }


def plan_skill_progress_loop(
    *,
    skill_id: str,
    skill_stat: str,
    baseline_level: int,
    target_level: int = 10,
    probe_level: int | None = None,
    command_template: str = "stats.set_skill_level {skill_stat} {level}",
    display_name: str | None = None,
) -> dict:
    """Library plan: one probe iteration, then measure→extrapolate gate.

    execute_allowed=False. Live owner applies the probe command, reads the
    Skills panel, then calls ``resolve_skill_progress_after_probe``.
    """
    sid = str(skill_id or "").strip().lower()
    stat = str(skill_stat or "").strip()
    if not sid or not stat:
        raise DiySkillForceError("SKILL_ID_AND_STAT_REQUIRED")
    base = int(baseline_level)
    target = int(target_level)
    if base < 0 or base > 10 or target < 1 or target > 10:
        raise DiySkillForceError("SKILL_LEVEL_OUT_OF_RANGE")
    if base >= target:
        return {
            "schema": "betterinstincts.skill-progress-loop/v1",
            "state": "SKILL_ALREADY_AT_TARGET",
            "execute_allowed": False,
            "skill_id": sid,
            "skill_stat": stat,
            "display_name": display_name,
            "baseline_level": base,
            "target_level": target,
            "steps": [{"step": "SKIP_SKILL", "reason": "BASELINE_AT_TARGET"}],
            "forbidden": ["GUESS_ITERATION_COUNT"],
        }
    probe = int(probe_level) if probe_level is not None else target
    if probe < 1 or probe > 10:
        raise DiySkillForceError("PROBE_LEVEL_OUT_OF_RANGE")
    cmd = str(command_template).format(skill_stat=stat, level=probe)
    return {
        "schema": "betterinstincts.skill-progress-loop/v1",
        "state": "SKILL_PROGRESS_PROBE_READY",
        "execute_allowed": False,
        "skill_id": sid,
        "skill_stat": stat,
        "display_name": display_name,
        "baseline_level": base,
        "probe_level": probe,
        "target_level": target,
        "probe_command": cmd,
        "steps": [
            {
                "step": "SKILL_PROGRESS_PROBE",
                "command": cmd,
                "skill_id": sid,
                "skill_stat": stat,
                "level": probe,
                "note": "Type once while CONSOLE_FIELD_FOCUSED; then measure panel",
            },
            {
                "step": "MEASURE_PANEL_LEVEL",
                "skill_id": sid,
                "required": True,
                "note": "LOCAL_OBSERVE Skills-panel level for this skill after play-brief",
            },
            {
                "step": "RESOLVE_VIA_extrapolate_skill_iterations",
                "owner": "betterinstincts.diy_skill_force.resolve_skill_progress_after_probe",
            },
        ],
        "forbidden": ["GUESS_ITERATION_COUNT", "BLIND_RETRY_SAME_COMMAND"],
        "next": "resolve_skill_progress_after_probe(after_level=…)",
    }


def resolve_skill_progress_after_probe(
    *,
    skill_id: str,
    skill_stat: str,
    baseline_level: int,
    after_level: int,
    target_level: int = 10,
    command_template: str = "stats.set_skill_level {skill_stat} {level}",
    display_name: str | None = None,
) -> dict:
    """Memoize measured delta; emit remaining SET_SKILL_LEVEL commands or falsify."""
    sid = str(skill_id or "").strip().lower()
    stat = str(skill_stat or "").strip()
    if not sid or not stat:
        raise DiySkillForceError("SKILL_ID_AND_STAT_REQUIRED")
    xpol = extrapolate_skill_iterations(
        baseline_level=int(baseline_level),
        after_level=int(after_level),
        target_level=int(target_level),
    )
    memo = {
        "skill_id": sid,
        "skill_stat": stat,
        "display_name": display_name,
        "baseline_level": xpol["baseline_level"],
        "after_level": xpol["after_level"],
        "target_level": xpol["target_level"],
        "delta": xpol["delta"],
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "extrapolation": xpol,
    }
    if xpol["state"] == "SKILL_AT_TARGET":
        return {
            "schema": "betterinstincts.skill-progress-resolve/v1",
            "state": "SKILL_PROGRESS_CONFIRMED_MAX",
            "execute_allowed": False,
            "memo": memo,
            "remaining_commands": [],
            "steps": [
                {
                    "step": "SKILL_PROGRESS_CONFIRM",
                    "skill_id": sid,
                    "action": "panel-record PANEL_OBSERVED_MAX",
                },
                {"step": "NEXT_SKILL"},
            ],
            "forbidden": ["GUESS_ITERATION_COUNT"],
        }
    if xpol["state"] == "SKILL_PROGRESS_FALSIFIED":
        return {
            "schema": "betterinstincts.skill-progress-resolve/v1",
            "state": "SKILL_PROGRESS_FALSIFIED",
            "execute_allowed": False,
            "memo": memo,
            "remaining_commands": [],
            "gate": xpol.get("gate"),
            "steps": [
                {
                    "step": "SKILL_PROGRESS_FALSIFY",
                    "skill_id": sid,
                    "action": "record_skill_panel_falsified; stop this skill",
                }
            ],
            "forbidden": list(xpol.get("forbidden") or []),
        }
    remaining = int(xpol["remaining_iterations"] or 0)
    # Each remaining iteration re-applies absolute target (or +delta steps).
    # Prefer absolute target so a working set_skill_level finishes in one more hit;
    # when delta < (target-after) the count still matches measured progress units.
    commands: list[str] = []
    steps: list[dict] = []
    for i in range(remaining):
        # Climb by measured delta each iteration; final clamp at target.
        next_level = min(
            int(target_level),
            int(after_level) + (i + 1) * int(xpol["delta"]),
        )
        cmd = str(command_template).format(skill_stat=stat, level=next_level)
        commands.append(cmd)
        steps.append(
            {
                "step": "SET_SKILL_LEVEL",
                "command": cmd,
                "skill_id": sid,
                "skill_stat": stat,
                "level": next_level,
                "iteration": i + 1,
                "of": remaining,
            }
        )
    steps.append(
        {
            "step": "SKILL_PROGRESS_CONFIRM",
            "skill_id": sid,
            "note": "Re-measure panel; require after >= target before NEXT_SKILL",
        }
    )
    steps.append({"step": "NEXT_SKILL"})
    return {
        "schema": "betterinstincts.skill-progress-resolve/v1",
        "state": "SKILL_PROGRESS_REMAINING_READY",
        "execute_allowed": False,
        "memo": memo,
        "remaining_iterations": remaining,
        "remaining_commands": commands,
        "steps": steps,
        "forbidden": ["GUESS_ITERATION_COUNT", "BLIND_RETRY_SAME_COMMAND"],
        "next": "Type remaining_commands while CONSOLE_FIELD_FOCUSED; confirm panel",
    }


def assess_selection_identity(
    *,
    expected_display_name: str,
    observed_panel_header_name: str | None,
    observed_selected_roster_key: str | None = None,
    expected_roster_key: str | None = None,
    cue_source: str | None = None,
    white_bounds_roster_index: int | None = None,
    expected_roster_index: int | None = None,
) -> dict:
    """Prove the highlighted portrait matches the intended Sim before cheats.

    Identity requires a panel name embed (Servos look alike — white bounds alone
    cannot tell Olga from Bernice). Preferred lean order: **J work/career** name,
    then **L skills** for progress sight. Aspiration G also embeds the name but
    is not the preferred identity panel for skill-force.

    Accepted name embeds (open BR panels via letter hotkeys, not mood color):
    - Career/work panel name text — hotkey **J** (preferred)
    - Skills/Dynasty header (``Olga hasn't…``) — hotkey **L**
    - Aspiration Satisfaction (``Olga's Satisfaction``) — hotkey G (valid, not preferred)

    White portrait boundaries only corroborate that *some* chip is selected.
    Mood glow behind a chip is NOT selection. Space-cycle without name is rejected.
    """
    expected = str(expected_display_name or "").strip()
    observed = str(observed_panel_header_name or "").strip()
    if not expected:
        raise DiySkillForceError("EXPECTED_DISPLAY_NAME_REQUIRED")
    white_ok = (
        isinstance(white_bounds_roster_index, int)
        and isinstance(expected_roster_index, int)
        and white_bounds_roster_index == expected_roster_index
    )
    # White bounds never authorize identity alone (identical Servo portraits).
    if not observed:
        out = {
            "state": "SELECTION_UNPROVEN",
            "match": False,
            "gate": "READ_WORK_OR_SKILLS_PANEL_NAME",
            "expected_display_name": expected,
            "observed_panel_header_name": None,
            "cue_source": cue_source,
            "white_bounds_roster_index": white_bounds_roster_index,
            "white_bounds_corroborates_index": bool(white_ok),
            "proof_ceiling": "WHITE_BOUNDS_CHIP_ONLY_NOT_SERVO_IDENTITY",
            "forbidden": [
                "SPACE_CYCLE_WITHOUT_HEADER_PROOF",
                "TYPE_CHEATS_ON_UNPROVEN_SELECTION",
                "MOOD_COLOR_AS_SELECTION",
                "WHITE_BOUNDS_ALONE_AS_SERVO_IDENTITY",
            ],
            "preferred_panel_hotkeys": {
                "career_work": "J",
                "skills": "L",
                "aspirations_valid_not_preferred": "G",
            },
            "lean_panel_sequence": ["J_WORK_NAME", "L_SKILLS_PROGRESS", "CTRL_SHIFT_C"],
        }
        if white_ok:
            out["note"] = (
                "White bounds match expected roster index but Servos are visually "
                "indistinguishable — open J (work) or L (skills) for the Sim name."
            )
        return out
    # Header often embeds the first name: "Olga hasn't…" / work panel / Satisfaction
    expected_token = expected.split()[0].casefold()
    observed_l = observed.casefold()
    name_ok = expected_token in observed_l or expected.casefold() in observed_l
    key_ok = True
    if expected_roster_key and observed_selected_roster_key:
        key_ok = (
            str(expected_roster_key).strip() == str(observed_selected_roster_key).strip()
        )
    if name_ok and key_ok:
        return {
            "state": "SELECTION_PROVEN",
            "match": True,
            "gate": "PROCEED_SKILLS_PANEL_THEN_CONSOLE",
            "expected_display_name": expected,
            "observed_panel_header_name": observed,
            "cue_source": cue_source or "WORK_OR_SKILLS_PANEL_NAME",
            "expected_roster_key": expected_roster_key,
            "observed_selected_roster_key": observed_selected_roster_key,
            "white_bounds_roster_index": white_bounds_roster_index,
            "white_bounds_corroborates_index": bool(white_ok) if white_bounds_roster_index is not None else None,
            "forbidden": [
                "MOOD_COLOR_AS_SELECTION",
                "WHITE_BOUNDS_ALONE_AS_SERVO_IDENTITY",
            ],
            "next_lean": "L_SKILLS_IF_NOT_OPEN_THEN_CTRL_SHIFT_C",
        }
    return {
        "state": "SELECTION_MISMATCH",
        "match": False,
        "gate": "RECLICK_TARGET_PORTRAIT_THEN_REREAD_WORK_OR_SKILLS_NAME",
        "expected_display_name": expected,
        "observed_panel_header_name": observed,
        "cue_source": cue_source,
        "expected_roster_key": expected_roster_key,
        "observed_selected_roster_key": observed_selected_roster_key,
        "forbidden": [
            "DISPATCH_ON_WRONG_SIM",
            "SPACE_UNTIL_LUCKY",
            "MOOD_COLOR_AS_SELECTION",
            "WHITE_BOUNDS_ALONE_AS_SERVO_IDENTITY",
        ],
    }


def plan_arm_then_panel_letter(letter: str, *, purpose: str) -> dict:
    """Every Live panel letter (J/L/G/…) needs a fresh terrain RMB arm first.

    Operator correction 2026-11-10: hotkeys do not register without arm.
    Arm RMB is cancel-options on empty world — never portrait RMB.
    """
    key = str(letter or "").strip().upper()
    if len(key) != 1 or not key.isalpha():
        raise DiySkillForceError("PANEL_LETTER_REQUIRED")
    return {
        "schema": "betterinstincts.arm-then-panel-letter/v1",
        "state": "ARM_THEN_PANEL_LETTER_READY",
        "execute_allowed": False,
        "letter": key,
        "purpose": str(purpose),
        "requires_live_hotkey_arm": True,
        "order": [
            "ARM_LIVE_HOTKEYS",
            f"PRESS_{key}",
            "CONFIRM_PANEL_CUES",
        ],
        "arm": {
            "step": "ARM_LIVE_HOTKEYS",
            "detail": "RIGHT_CLICK exposed world/terrain only (LMB before RMB not required)",
            "forbidden": ["PORTRAIT_RIGHT_CLICK", "SKIP_ARM_BEFORE_PANEL_LETTER", "ARM_ON_MAPPED_FIXED_UI_COORD"],
            "owner": "betterinstincts.diy_skill_force.plan_live_hotkey_arm",
        },
        "hotkey": {
            "step": "PRESS_PANEL_LETTER",
            "chord": [key],
            "channel": "HOTKEY",
        },
        "note": (
            "If J or L does not register, you skipped terrain RMB arm "
            "immediately before the letter."
        ),
        "forbidden": [
            "PANEL_LETTER_WITHOUT_FRESH_ARM",
            "PORTRAIT_RIGHT_CLICK",
            "MOUSE_FALLBACK_WHILE_HOTKEY_ARMED",
        ],
    }


def plan_arm_then_play_brief(
    *,
    play_seconds: int | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Play (1) → wait → pause (0) with no extra map clicks.

    Operator 2026-11-10: Skills refresh only after Live plays a few seconds.
    Do NOT terrain-RMB before 1 and again before 0 — that moves the map.
    Assume the skill beat already did ONE pinned arm (or re-arm only on miss).
    """
    cfg = cfg or load_contract()
    obs = (cfg.get("inject_sequence") or {}).get("skills_panel_observation") or {}
    play_cfg = obs.get("play_brief_for_fresh_panel") or {}
    min_s = int(play_cfg.get("min_play_seconds") or 5)
    max_s = int(play_cfg.get("max_play_seconds") or 10)
    default_s = int(play_cfg.get("default_play_seconds") or 7)
    if play_seconds is None:
        seconds = default_s
    else:
        seconds = int(play_seconds)
    seconds = max(min_s, min(max_s, seconds))
    play_key = str(play_cfg.get("play_key") or "1")
    pause_key = str(play_cfg.get("pause_key") or "0")
    return {
        "schema": "betterinstincts.arm-then-play-brief/v1",
        "state": "PLAY_BRIEF_READY",
        "execute_allowed": False,
        "requires_prior_skill_beat_arm": True,
        "measure_requires_play_brief": True,
        "play_seconds": seconds,
        "min_play_seconds": min_s,
        "max_play_seconds": max_s,
        "play_key": play_key,
        "pause_key": pause_key,
        "order": [
            f"PRESS_PLAY_{play_key}",
            f"WAIT_{seconds}S",
            f"PRESS_PAUSE_{pause_key}",
            "THEN_MEASURE_OR_EXTRAPOLATE",
        ],
        "note": (
            "No terrain RMB here — map clicks are noise. Press 1, wait "
            f">={min_s}s, press 0, then read Skills. Re-arm only if 1/0 miss."
        ),
        "forbidden": [
            "MEASURE_WITHOUT_PLAY_BRIEF",
            "REPEATED_TERRAIN_RMB_PER_HOTKEY",
            "PAUSED_ONLY_SKILLS_PANEL_AS_PROGRESS_PROOF",
            "LEAVE_SIM_RUNNING_AFTER_MEASURE",
        ],
    }


def plan_lean_olga_skill_beat(
    *,
    portrait_client_xy: Sequence[int] = (454, 1055),
    roster_index: int = 2,
) -> dict:
    """Lean Olga skill-force: one pinned arm, Enter recenter, then hotkeys.

    Operator 2026-11-10: keep the camera on the active Sim. Arm once may
    displace the view — press Enter (native center-active-Sim) to refocus.
    Notice selection/camera switches and Enter again. Never roam/zoom the lot.
    Then J → L → console → type → close → play/pause. Re-arm only on hotkey miss.
    """
    xy = [int(portrait_client_xy[0]), int(portrait_client_xy[1])]
    arm_xy = list(
        (load_contract().get("live_hotkey_arm") or {}).get("default_world_client_xy")
        or [880, 480]
    )
    return {
        "schema": "betterinstincts.lean-olga-skill-beat/v1",
        "state": "LEAN_OLGA_SKILL_BEAT_READY",
        "execute_allowed": False,
        "roster_index": int(roster_index),
        "portrait_client_xy": xy,
        "arm_world_client_xy": arm_xy,
        "invariant": "ONE_ARM_ENTER_RECENTER_THEN_HOTKEYS",
        "active_sim_camera": "KEEP_FOCUSED_ENTER_TO_REFOCUS",
        "steps": [
            {
                "step": "ONE_PINNED_TERRAIN_ARM",
                "detail": "Single RIGHT_CLICK at pinned [880,480] only",
                "world_client_xy": arm_xy,
                "forbidden": [
                    "REPEATED_TERRAIN_RMB_PER_HOTKEY",
                    "ARM_BEFORE_EVERY_PANEL_LETTER",
                    "MAP_CLICK_WANDER",
                ],
            },
            {
                "step": "ENTER_CENTER_ACTIVE_SIM",
                "hotkey": "Enter",
                "purpose": "REFOCUS_CAMERA_ON_ACTIVE_SIM",
                "note": (
                    "Native Enter centers the active Sim after arm displacement. "
                    "Not Shift+Enter (lot). Repeat when camera/selection switches."
                ),
                "forbidden": [
                    "MAP_ROAM_TO_REFOCUS",
                    "WHEEL_ZOOM_OUT_TO_REFOCUS",
                    "SHIFT_ENTER_LOT_CENTER_AS_SKILL_FORCE_DEFAULT",
                ],
            },
            {
                "step": "LEFT_CLICK_OLGA_PORTRAIT",
                "detail": "LEFT_CLICK portrait only (no portrait RMB, no world roam)",
                "client_xy": xy,
                "forbidden": ["PORTRAIT_RIGHT_CLICK", "PORTRAIT_PROBE_LOOP"],
            },
            {
                "step": "J_WORK_NAME",
                "hotkey": "J",
                "purpose": "NAME_IDENTITY",
                "read": "Panel must embed Olga (work/career name text)",
            },
            {
                "step": "PROVE_SELECTION_IDENTITY",
                "owner": "assess_selection_identity",
                "require_name_embed": True,
                "forbidden": ["WHITE_BOUNDS_ALONE_AS_SERVO_IDENTITY"],
            },
            {
                "step": "L_SKILLS",
                "hotkey": "L",
                "purpose": "PROGRESS_SIGHT",
                "burger_expand_once_if_min": True,
            },
            {
                "step": "OPEN_CHEAT_CONSOLE",
                "chord": "Ctrl+Shift+C",
                "console_field_focused": True,
            },
            {
                "step": "SKILL_PROGRESS_PROBE_MEMO_EXTRAPOLATE",
                "owner": "extrapolate_skill_iterations",
                "per_skill": True,
            },
            {
                "step": "CLOSE_CONSOLE",
                "chord": "Ctrl+Shift+C",
            },
            {
                "step": "PLAY_BRIEF_THEN_PAUSE",
                "plan": plan_arm_then_play_brief(),
                "owner": "betterinstincts.diy_skill_force.plan_arm_then_play_brief",
                "note": "Press 1, wait, press 0 — no map clicks",
            },
            {
                "step": "MEASURE_SKILLS_CONFIRM_OR_EXTRAPOLATE",
                "requires_prior": "PLAY_BRIEF_THEN_PAUSE",
                "inventory": plan_skills_panel_inventory(),
                "then": "GAP_TARGETS_THEN_NEXT_OR_PANEL_RECORD",
                "note": (
                    "Burger-expand + scroll the full Skills list; non-yellow "
                    "rows are gap targets from the canonical catalog commands"
                ),
                "forbidden": [
                    "MEASURE_WITHOUT_PLAY_BRIEF",
                    "PAUSED_ONLY_SKILLS_PANEL_AS_PROGRESS_PROOF",
                    "FIRST_VIEWPORT_ONLY_SKILLS_READ",
                ],
            },
        ],
        "forbidden": list(
            (load_contract().get("target_sim_algorithm") or {}).get(
                "lean_skill_beat_forbidden"
            )
            or []
        )
        + [
            "WHITE_BOUNDS_ALONE_AS_SERVO_IDENTITY",
            "ASPIRATION_G_AS_DEFAULT_IDENTITY",
            "REPEATED_TERRAIN_RMB_PER_HOTKEY",
            "ARM_BEFORE_EVERY_PANEL_LETTER",
            "MEASURE_WITHOUT_PLAY_BRIEF",
            "CAMERA_ZOOM_LADDER_DURING_SKILL_FORCE",
            "CAMERA_PAN_DURING_SKILL_FORCE",
            "MAP_CLICK_WANDER",
            "STREET_CORNER_ARM_ROAM",
            "MAP_ROAM_TO_REFOCUS",
            "FIRST_VIEWPORT_ONLY_SKILLS_READ",
        ],
        "camera_during_skill_force": "ACTIVE_SIM_ONLY_ENTER_REFOCUS",
        "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED_AFTER_PLAY_BRIEF",
    }


def assess_console_type_safety(*, console_strip_observed: bool) -> dict:
    """Fail closed before type_text: unfocused typing is Live hotkeys (V = video)."""
    if console_strip_observed is True:
        return {
            "state": "CONSOLE_TYPE_ALLOWED",
            "console_strip_observed": True,
            "gate": "TYPE_CHEAT_LINES_VIA_WIN32_TYPE_TEXT",
            "forbidden_hotkeys_if_unfocused": ["V_VIDEO_RECORD"],
        }
    return {
        "state": "CONSOLE_TYPE_DENIED",
        "console_strip_observed": False,
        "gate": "OPEN_CTRL_SHIFT_C_AND_CONFIRM_WHITE_STRIP",
        "reason": "UNFOCUSED_TYPE_TEXT_IS_LIVE_HOTKEYS",
        "forbidden": [
            "TYPE_WITHOUT_CONSOLE_STRIP",
            "TAP_V_TO_CANCEL_VIDEO",
            "Major_VideoGaming_WHILE_CONSOLE_CLOSED",
        ],
        "note": (
            "Sims Live maps V to video recording. type_text of VideoGaming or any "
            "cheat while the strip is closed starts recording. V toggles — do not "
            "tap V to cancel."
        ),
    }


def plan_arm_to_console_handoff(cfg: Optional[dict] = None) -> dict:
    """Handoff: ARM_LIVE_HOTKEYS → CHEAT_CONSOLE microsystem (Ctrl+Shift+C).

    Seamless bridge from world focus arm into the existing console toggle /
    white-strip typing gate. Does not authorize type_text by itself.
    """
    from betterinstincts.fixed_ui_click_map import plan_arm_to_console_handoff as _plan

    return _plan(cfg=None)


def assess_arm_world_point(
    client_xy: Sequence[int],
    *,
    cfg: Optional[dict] = None,
) -> dict:
    """Fail closed if the arm click would hit mapped HUD / fixed-ui seeds.

    Operator 2026-11-10: LMB/RMB must land on exposed world/terrain in the
    remaining viewport — never a fixed-ui-click-map coordinate (that interacts
    with the interface instead of arming).
    """
    if (
        not isinstance(client_xy, (list, tuple))
        or len(client_xy) != 2
        or any(type(v) is not int for v in client_xy)
    ):
        raise DiySkillForceError("WORLD_CLIENT_XY_MUST_BE_TWO_INTS")
    x, y = int(client_xy[0]), int(client_xy[1])
    cfg = cfg or load_contract()
    arm = cfg.get("live_hotkey_arm") if isinstance(cfg.get("live_hotkey_arm"), Mapping) else {}
    bands = arm.get("hud_exclusion_bands_1920x1080") if isinstance(arm, Mapping) else {}
    if not isinstance(bands, Mapping):
        bands = {}
    top = int(bands.get("top_y_max") or 70)
    bottom = int(bands.get("bottom_y_min") or 980)
    left = int(bands.get("left_x_max") or 320)
    right = int(bands.get("right_x_min") or 1520)
    if y <= top or y >= bottom or x <= left or x >= right:
        return {
            "state": "ARM_POINT_IN_HUD_BAND",
            "ok": False,
            "client_xy": [x, y],
            "gate": "PICK_EXPOSED_WORLD_TERRAIN",
            "forbidden": ["ARM_ON_MAPPED_FIXED_UI_COORD", "ARM_IN_HUD_BAND"],
            "note": "Arm clicks in HUD bands hit the interface, not the world.",
        }
    radius = int(arm.get("mapped_exclusion_radius_px") or 36) if isinstance(arm, Mapping) else 36
    hits: list[dict] = []
    try:
        from betterinstincts.fixed_ui_click_map import load_contract as load_fixed_map
        from betterinstincts.fixed_ui_click_map import seed_targets_from_contract

        seeds = seed_targets_from_contract(cfg=load_fixed_map())
    except Exception:
        seeds = {}
    for tid, row in seeds.items():
        if not isinstance(row, Mapping):
            continue
        xy = row.get("client_xy")
        if not (
            isinstance(xy, (list, tuple))
            and len(xy) == 2
            and all(isinstance(v, int) for v in xy)
        ):
            continue
        dx = x - int(xy[0])
        dy = y - int(xy[1])
        if dx * dx + dy * dy <= radius * radius:
            hits.append({"target_id": str(tid), "client_xy": [int(xy[0]), int(xy[1])]})
    if hits:
        return {
            "state": "ARM_POINT_HITS_MAPPED_UI",
            "ok": False,
            "client_xy": [x, y],
            "mapped_hits": hits[:8],
            "gate": "PICK_UNMAPPED_EXPOSED_TERRAIN",
            "forbidden": ["ARM_ON_MAPPED_FIXED_UI_COORD"],
            "note": (
                "Left/right click on mapped coords interacts with the UI. "
                "Use the remaining exposed world/terrain only."
            ),
        }
    return {
        "state": "ARM_POINT_WORLD_TERRAIN_OK",
        "ok": True,
        "client_xy": [x, y],
        "gate": "ARM_LMB_THEN_RMB_CANCEL",
        "forbidden": [
            "ARM_ON_MAPPED_FIXED_UI_COORD",
            "ARM_IN_HUD_BAND",
            "TREAT_CANCEL_RMB_AS_PORTRAIT_FOLLOW",
        ],
    }


def plan_live_hotkey_arm(
    *,
    world_client_xy: Sequence[int] | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Plan RIGHT_CLICK on exposed world/terrain so Live hotkeys register.

    Operator 2026-11-10: a terrain right-click is enough (prior LMB→RMB also
    worked but the left-click is not required). Point must be exposed
    world/terrain — never a fixed-ui-click-map seed. Not portrait follow;
    not cheat typing authority.
    """
    cfg = cfg or load_contract()
    arm = cfg.get("live_hotkey_arm") if isinstance(cfg.get("live_hotkey_arm"), Mapping) else {}
    default_xy = arm.get("default_world_client_xy") if isinstance(arm, Mapping) else None
    if world_client_xy is not None:
        if (
            not isinstance(world_client_xy, (list, tuple))
            or len(world_client_xy) != 2
            or any(type(v) is not int for v in world_client_xy)
        ):
            raise DiySkillForceError("WORLD_CLIENT_XY_MUST_BE_TWO_INTS")
        point = [int(world_client_xy[0]), int(world_client_xy[1])]
    elif (
        isinstance(default_xy, (list, tuple))
        and len(default_xy) == 2
        and all(isinstance(v, int) for v in default_xy)
    ):
        point = [int(default_xy[0]), int(default_xy[1])]
    else:
        point = [880, 480]
    assess = assess_arm_world_point(point, cfg=cfg)
    if not assess.get("ok"):
        raise DiySkillForceError(
            f"{assess.get('state')}: pick exposed world/terrain, not mapped UI "
            f"(got {point})"
        )
    order = arm.get("order") if isinstance(arm, Mapping) else None
    if not isinstance(order, list) or not order:
        order = [
            "WAIT_TRUSTED_IDLE_GE_15S",
            "SNAPSHOT_OPERATOR_FOREGROUND",
            "BORROW_SIMS_FOREGROUND",
            "RIGHT_CLICK_EXPOSED_WORLD_TERRAIN",
            "RESTORE_OPERATOR_FOREGROUND",
        ]
    return {
        "step": "ARM_LIVE_HOTKEYS",
        "schema": "betterinstincts.live-hotkey-arm/v1",
        "order": list(order),
        "world_client_xy": point,
        "arm_point_assessment": assess,
        "select_note": str(
            arm.get("operator_rule")
            if isinstance(arm, Mapping) and arm.get("operator_rule")
            else (
                "Borrow Sims briefly, right-click exposed world/terrain to arm "
                "Live hotkeys, then restore the operator's foreground app."
            )
        ),
        "world_point_rule": str(
            arm.get("world_point_rule")
            if isinstance(arm, Mapping)
            else "EXPOSED_WORLD_TERRAIN_ONLY"
        ),
        "interruptible": True,
        "repository_skill": ".cursor/skills/live-hotkey-arm",
        "forbidden": [
            "BARE_HOTKEY_WITHOUT_ARM",
            "TREAT_CANCEL_RMB_AS_PORTRAIT_FOLLOW",
            "SPACE_WITHOUT_ARM_WHEN_FOCUS_AMBIGUOUS",
            "ARM_ON_MAPPED_FIXED_UI_COORD",
            "ARM_IN_HUD_BAND",
            "MONOPOLIZE_FOREGROUND_FOR_AGENT_SESSION",
            "LEAVE_OPERATOR_TRAPPED_IN_SIMS",
        ],
        "not": [
            "RIGHT_CLICK_VIEW",
            "CONSOLE_TYPE_AUTHORITY",
            "PRIMARY_TARGET_SIM_SELECT",
            "ARM_ON_MAPPED_FIXED_UI_COORD",
            "LEAVE_OPERATOR_TRAPPED_IN_SIMS",
        ],
        "next": "SEND_LIVE_HOTKEY",
    }


def plan_target_sim_skill_algorithm(
    *,
    session_id: str,
    member_key: str,
    display_name: str,
    roster_index: int,
    members: int,
    roster_keys: Sequence[str],
    bundle: str = "full_unlock",
    target_level: int = 10,
    ledger: Mapping[str, object] | None = None,
    observed_panel_header_name: str | None = None,
    observed_selected_roster_key: str | None = None,
    console_strip_observed: bool = False,
    portrait_client_xy: Sequence[int] | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Central algorithm: evaluate → select portrait → camera → console → force → panel.

    Library plans only (``execute_allowed=False``). Live typing stays in
    ``scripts/diy_skill_force.py`` behind identity + console-strip gates.
    """
    cfg = cfg or load_contract()
    algo = cfg.get("target_sim_algorithm") or {}
    if not isinstance(algo, Mapping):
        raise DiySkillForceError("TARGET_SIM_ALGORITHM_REQUIRED")
    sid = str(session_id or "").strip()
    if not sid:
        raise DiySkillForceError("SESSION_ID_REQUIRED")
    keys = [str(k).strip() for k in roster_keys]
    n = int(members)
    if n < 1 or len(keys) != n:
        raise DiySkillForceError("EXACT_OBSERVED_PORTRAIT_ROSTER_REQUIRED")
    idx = int(roster_index)
    if idx < 0 or idx >= n:
        raise DiySkillForceError("ROSTER_INDEX_OUT_OF_RANGE")
    label = str(member_key).strip()
    if not label:
        raise DiySkillForceError("MEMBER_KEY_REQUIRED")
    expected_key = keys[idx]
    if "::key::" in label:
        mkey = label
        bare = label.split("::key::", 1)[-1]
        if bare not in keys:
            raise DiySkillForceError("MEMBER_KEY_NOT_IN_ROSTER")
        if bare != expected_key:
            raise DiySkillForceError("ROSTER_INDEX_MEMBER_KEY_MISMATCH")
    else:
        if label not in keys:
            raise DiySkillForceError("MEMBER_KEY_NOT_IN_ROSTER")
        if label != expected_key:
            raise DiySkillForceError("ROSTER_INDEX_MEMBER_KEY_MISMATCH")
        mkey = completion_member_key(sid, idx, label)

    skill_rows = resolve_skills(bundle=str(bundle or "full_unlock"), cfg=cfg)
    skill_ids = [str(r["id"]) for r in skill_rows]
    book = dict(ledger) if isinstance(ledger, Mapping) else empty_completion_ledger()
    evaluation = evaluate_member_skill_levels(
        book, member_key=mkey, skill_ids=skill_ids, target_level=int(target_level),
    )
    identity = assess_selection_identity(
        expected_display_name=str(display_name),
        observed_panel_header_name=observed_panel_header_name,
        observed_selected_roster_key=observed_selected_roster_key,
        expected_roster_key=expected_key,
    )
    console = assess_console_type_safety(console_strip_observed=bool(console_strip_observed))

    steps: list[dict] = [
        {
            "step": "EVALUATE_SKILLS_LEDGER_OR_PANEL",
            "evaluation": evaluation,
            "owner": "betterinstincts.diy_skill_force.evaluate_member_skill_levels",
        }
    ]
    if not evaluation["needs_work"]:
        return {
            "schema": "betterinstincts.target-sim-skill-algorithm/v1",
            "state": "TARGET_SIM_ALREADY_LEVELED",
            "execute_allowed": False,
            "session_id": sid,
            "member_key": mkey,
            "roster_key": expected_key,
            "roster_index": idx,
            "display_name": str(display_name),
            "evaluation": evaluation,
            "steps": steps + [{"step": "SKIP_SELECT_AND_FORCE", "reason": "NO_GAPS"}],
            "proof_ceiling": str(algo.get("proof_ceiling") or cfg["proof_ceiling"]),
            "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
            "next": "ADVANCE_TO_NEXT_GAP_MEMBER_OR_STOP",
        }

    gap_ids = [g["skill_id"] for g in evaluation["gaps"] if g.get("skill_id")]
    force_plan = plan_skill_force(
        skill_ids=gap_ids,
        level=int(target_level),
        cfg=cfg,
    )
    force_commands = steps_to_commands(force_plan)

    point = None
    if portrait_client_xy is not None:
        if (
            not isinstance(portrait_client_xy, (list, tuple))
            or len(portrait_client_xy) != 2
            or any(type(v) is not int for v in portrait_client_xy)
        ):
            raise DiySkillForceError("PORTRAIT_CLIENT_XY_MUST_BE_TWO_INTS")
        point = [int(portrait_client_xy[0]), int(portrait_client_xy[1])]

    steps.extend(
        [
            {
                "step": "SELECT_TARGET_PORTRAIT_CLICK",
                "roster_index": idx,
                "roster_key": expected_key,
                "control": "LEFT_CLICK_HOUSEHOLD_PORTRAIT",
                "client_xy": point,
                "forbidden": ["SPACE_CYCLE_WITHOUT_HEADER_PROOF", "GUESS_SELECTION"],
                "recovery_if_portrait_miss": (
                    "ARM_LIVE_HOTKEYS (left-click world, right-click cancel) then SPACE; "
                    "reopen Skills/Dynasty and require header match before any type_text"
                ),
                "prerequisite_for_space_recovery": "ARM_LIVE_HOTKEYS",
                "note": str(algo.get("select_note") or ""),
            },
            {
                "step": "PROVE_SELECTION_IDENTITY",
                "identity": identity,
                "read": "Skills or Dynasty panel header must embed target display name",
            },
            {
                "step": "CAMERA_CENTER_RIGHT_CLICK_VIEW",
                "mode": "RIGHT_CLICK_VIEW",
                "execute_allowed": False,
                "lean_skill_beat": False,
                "execute_on_lean_skill_beat": False,
                "skipped_for_skill_force": True,
                "note": (
                    "FORBIDDEN during skill force (operator 2026-11-09/10): "
                    "portrait RMB / zoom / map wander is disruptive noise and "
                    "does not level skills. Leave camera alone."
                ),
            },
            {
                "step": "OPEN_CHEAT_CONSOLE",
                "chord": ["CTRL", "SHIFT", "C"],
                "require_white_strip_observed": True,
                "console_safety": console,
                "lean_skill_beat": True,
                "forbidden_before_open": list(algo.get("lean_skill_beat_forbidden") or []),
            },
            {
                "step": "DISPATCH_GAP_SKILLS",
                "commands": list(force_commands),
                "skills": gap_ids,
                "typing_gate": console,
                "forbidden_unless_console_strip": True,
            },
            {
                "step": "PLAY_BRIEF_OBSERVE_REPAUSE",
                "policy": skills_panel_observation_policy(purpose="verify", cfg=cfg),
            },
            {
                "step": "PANEL_RECORD_LOCAL_OBSERVED",
                "cli": "python -m scripts.diy_skill_force panel-record …",
                "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
            },
        ]
    )

    ready = identity.get("match") is True and console.get("state") == "CONSOLE_TYPE_ALLOWED"
    return {
        "schema": "betterinstincts.target-sim-skill-algorithm/v1",
        "state": (
            "TARGET_SIM_FORCE_READY"
            if ready
            else "TARGET_SIM_FORCE_PLAN_GATED"
        ),
        "execute_allowed": False,
        "live_dispatch_ready": bool(ready),
        "session_id": sid,
        "member_key": mkey,
        "roster_key": expected_key,
        "roster_index": idx,
        "display_name": str(display_name),
        "evaluation": evaluation,
        "identity": identity,
        "console_safety": console,
        "live_hotkey_arm": plan_live_hotkey_arm(cfg=cfg),
        "force_plan": {
            "commands": list(force_commands),
            "skills": list(force_plan.get("skills") or []),
            "level": int(target_level),
        },
        "steps": steps,
        "algorithm_order": list(
            algo.get("order")
            or [
                "EVALUATE",
                "SELECT_PORTRAIT",
                "PROVE_IDENTITY",
                "CONSOLE_CONFIRM",
                "DISPATCH",
                "PLAY_BRIEF",
                "PANEL_RECORD",
            ]
        ),
        "camera_during_skill_force": "FORBIDDEN",
        "map_click_during_skill_force": "FORBIDDEN_EXCEPT_ONE_FIXED_ARM_POINT",
        "proof_ceiling": str(algo.get("proof_ceiling") or cfg["proof_ceiling"]),
        "pass_claim": "FORBIDDEN_UNTIL_SKILLS_PANEL_LOCAL_OBSERVED",
        "next": (
            "scripts.diy_skill_force target-sim --execute only after identity+console gates"
            if ready
            else identity.get("gate") or console.get("gate")
        ),
    }


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
    Verify: ARM → PLAY_BRIEF (5–10s) → ARM → PAUSE → OBSERVE.
    Paused-only UI is STALE. Play/pause hotkeys need fresh terrain RMB arm.
    Never leave sim speed running after verify. Not main-menu Resume.
    """
    cfg = cfg or load_contract()
    obs = (cfg.get("inject_sequence") or {}).get("skills_panel_observation") or {}
    play_cfg = obs.get("play_brief_for_fresh_panel") or {}
    purpose_l = str(purpose or "verify").lower()
    precious = bool(precious_time or concurrent_live_cert or main_goal_unfinished)
    play_plan = plan_arm_then_play_brief(cfg=cfg)
    play_seconds = int(play_plan["play_seconds"])
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
        "min_play_seconds": int(play_plan["min_play_seconds"]),
        "max_play_seconds": int(play_plan["max_play_seconds"]),
        "play_key": str(play_plan["play_key"]),
        "pause_key": str(play_plan["pause_key"]),
        "always_repause": bool(play_cfg.get("always_repause", True)),
        "requires_live_hotkey_arm_before_play": True,
        "requires_live_hotkey_arm_before_pause": True,
        "play_brief_plan": play_plan if purpose_l == "verify" else None,
        "dispatch_while_paused_allowed": bool(obs.get("dispatch_while_paused_allowed", True)),
        "forbidden": [
            "MEASURE_WITHOUT_PLAY_BRIEF",
            "PLAY_OR_PAUSE_HOTKEY_WITHOUT_FRESH_ARM",
            "PAUSED_ONLY_SKILLS_PANEL_AS_PROGRESS_PROOF",
        ]
        if purpose_l == "verify"
        else [],
        "note": (
            obs.get("keep_paused_policy")
            if purpose_l == "dispatch"
            else (
                "Arm → play 5–10s at 1x → arm → pause → capture Skills panel. "
                "Paused-only reads are STALE."
            )
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
    algo = cfg.get("target_sim_algorithm")
    if not isinstance(algo, Mapping):
        raise DiySkillForceError("TARGET_SIM_ALGORITHM_REQUIRED")
    if algo.get("console_strip_required_before_type") is not True:
        raise DiySkillForceError("TARGET_SIM_CONSOLE_STRIP_GATE_REQUIRED")
    if algo.get("space_cycle_without_header_proof_forbidden") is not True:
        raise DiySkillForceError("TARGET_SIM_SPACE_WITHOUT_PROOF_FORBIDDEN")
    if algo.get("v_starts_video_recording") is not True:
        raise DiySkillForceError("TARGET_SIM_V_VIDEO_GUARD_REQUIRED")
    if algo.get("dispatched_is_not_panel_pass") is not True:
        raise DiySkillForceError("TARGET_SIM_DISPATCHED_NOT_PASS_REQUIRED")
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
    commands = canonical_skill_commands(cfg=cfg)
    return {
        "skills": list(cfg["skill_catalog"]),
        "bundles": dict(cfg["bundles"]),
        "canonical_commands": commands,
        "required_residual_skills": required_residual_skills(cfg),
        "household_traverse": dict(cfg.get("household_traverse") or {}),
        "live_hotkey_arm": dict(cfg.get("live_hotkey_arm") or {}),
        "target_sim_algorithm": dict(cfg.get("target_sim_algorithm") or {}),
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
