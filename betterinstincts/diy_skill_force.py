"""DIY skill-force planner for Handiness / Robotics / Fabrication / Programming.

P95 stack: soft-focus Sims → Ctrl+Shift+C → testingcheats enabled true →
stats.set_skill_level <stat> <N> for each resolved DIY skill. Mode-agnostic;
never force F1 while the operator builds.

Library plans only; scripts/diy_skill_force.py owns SendInput. Never edits
saves. Never authorizes practice_skill or BI-005 skill-growth certification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "diy-skill-force.v1.json"
MAX_BYTES = 48_000


class DiySkillForceError(ValueError):
    pass


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
    return cfg


def catalog_snapshot(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    return {
        "skills": list(cfg["skill_catalog"]),
        "bundles": dict(cfg["bundles"]),
        "default_level": int(cfg["inject_sequence"]["default_level"]),
        "proof_ceiling": cfg["proof_ceiling"],
        "forbidden": list(cfg["inject_sequence"].get("forbidden") or []),
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
        # Default operator bundle when nothing named.
        for sid in (cfg["bundles"]["diy_maker"].get("skill_ids") or []):
            _add(str(sid))
    return [index[sid] for sid in ordered]


def plan_skill_force(
    *,
    skill_ids: Optional[Sequence[str]] = None,
    bundle: Optional[str] = None,
    level: Optional[int] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
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
    for row in skills:
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
    if seq.get("close_console_optional", True):
        steps.append(
            {
                "step": "CLOSE_CHEAT_CONSOLE",
                "key": seq["close_console_key"],
                "required": False,
                "note": "Optional — avoid Esc spam that opens pause MENU while building",
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
        "open_console": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
        "steps": steps,
        "forbidden": list(seq.get("forbidden") or []),
        "invariants": list(cfg.get("invariants") or []),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "not_bi005": True,
        "not_practice_skill": True,
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
