"""Generalized, opt-in Sims 4 active-household funds planning.

Pure policy: no game/OS input, saves, portrait IDs, or persistent state.
EA documents testingcheats true followed by money N as an exact household
balance setter. Never append motherlode after that command or lower funds
because the starting balance was guessed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "host-funds.v1.json"
MAX_BYTES = 48_000
MAX_HOUSEHOLD_FUNDS = 9_999_999


class FundsInjectError(ValueError):
    pass


def _funds_int(value: object, label: str, *, positive: bool = False) -> int:
    """Fail closed on bools, strings, NaN, infinity, fractions and overflow."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FundsInjectError(label + "_MUST_BE_INTEGER")
    if isinstance(value, int):
        amount = value
    elif not math.isfinite(value) or value != int(value):
        raise FundsInjectError(label + "_MUST_BE_INTEGER")
    else:
        amount = int(value)
    if amount < (1 if positive else 0) or amount > MAX_HOUSEHOLD_FUNDS:
        raise FundsInjectError(label + "_OUT_OF_RANGE")
    return amount


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise FundsInjectError("HOST_FUNDS_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.host-funds/v1":
        raise FundsInjectError("BAD_HOST_FUNDS_SCHEMA")
    seq = cfg.get("inject_sequence") or {}
    if seq.get("activate_testing_cheats") != "testingcheats true":
        raise FundsInjectError("CANONICAL_TESTINGCHEATS_TRUE_REQUIRED")
    if list(seq.get("open_console_chord") or []) != ["CTRL", "SHIFT", "C"]:
        raise FundsInjectError("CTRL_SHIFT_C_CONSOLE_CHORD_REQUIRED")
    if seq.get("mode_agnostic") is not True or seq.get("never_force_mode_switch") is not True:
        raise FundsInjectError("MODE_AGNOSTIC_NO_SWITCH_REQUIRED")
    if seq.get("require_live_mode") is True:
        raise FundsInjectError("REQUIRE_LIVE_MODE_FORBIDDEN")
    if seq.get("set_funds_template") != "money {amount}":
        raise FundsInjectError("CANONICAL_EXACT_MONEY_TEMPLATE_REQUIRED")
    if seq.get("auto_fallback") is not False:
        raise FundsInjectError("UNVERIFIED_AUTO_FALLBACK_FORBIDDEN")
    if seq.get("max_household_funds") != MAX_HOUSEHOLD_FUNDS:
        raise FundsInjectError("HOUSEHOLD_FUNDS_CAP_REQUIRED")
    sub = cfg.get("subsidy") or {}
    _funds_int(sub.get("trigger_funds_below"), "SUBSIDY_TRIGGER", positive=True)
    _funds_int(sub.get("boost_to"), "SUBSIDY_BOOST", positive=True)
    return cfg


def needs_subsidy_prompt(funds: float, cfg: Optional[dict] = None) -> bool:
    cfg = cfg or load_contract()
    return _funds_int(funds, "OBSERVED_FUNDS") < _funds_int(
        cfg["subsidy"]["trigger_funds_below"], "SUBSIDY_TRIGGER", positive=True
    )


def subsidy_prompt(cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    sub = cfg["subsidy"]
    return {
        "prompt_id": sub["prompt_id"],
        "title": sub["title"],
        "body": sub["body"],
        "options": [
            {"option_id": sub["option_yes"]["option_id"], "label": sub["option_yes"]["label"]},
            {"option_id": sub["option_no"]["option_id"], "label": sub["option_no"]["label"]},
        ],
        "default_option_id": sub["default_option_id"],
        "style": "sims_chance_card",
        "proof_ceiling": cfg["proof_ceiling"],
    }


def plan_inject(
    *,
    amount: Optional[float] = None,
    funds_observed: Optional[float] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
    cfg: Optional[dict] = None,
) -> dict:
    """Plan exact *target balance*, not an increment, for the active household.

    A money command can subtract wealth. Unknown starting funds therefore
    produce a read-only observation gate, never a guessed SendInput sequence.
    """
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER", "next_gate": "YIELD_TO_PLAYER",
            "steps": [], "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
        }
    seq = cfg["inject_sequence"]
    mode = str(game_mode or "unknown").lower()
    if mode not in set(seq.get("allowed_modes") or []):
        raise FundsInjectError("UNSUPPORTED_GAME_MODE")
    target = _funds_int(
        cfg["subsidy"]["boost_to"] if amount is None else amount,
        "TARGET", positive=True,
    )
    base = {
        "amount": target,
        "target_funds": target,
        "game_mode": mode,
        "mode_agnostic": True,
        "open_console": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
        "motherlode_count": 0,
        "forbidden": list(seq.get("forbidden") or []),
        "invariants": list(cfg.get("invariants") or []),
        "proof_ceiling": cfg["proof_ceiling"],
        "steps": [],
    }
    if funds_observed is None:
        return {
            **base, "state": "FUNDS_OBSERVATION_REQUIRED",
            "next_gate": "OBSERVE_ACTIVE_HOUSEHOLD_FUNDS",
            "funds_observed": None, "remaining": None,
        }
    current = _funds_int(funds_observed, "OBSERVED_FUNDS")
    if current >= target:
        return {
            **base, "state": "TARGET_ALREADY_MET", "next_gate": "CONTINUE_HOST",
            "funds_observed": current, "remaining": 0,
        }
    steps = [
        {
            "step": "REQUIRE_FOREGROUND_SIMS", "required": True,
            "note": "Exclusive admitted screen lease; no desktop/OS settings",
        },
        {
            "step": "PRESERVE_OPERATOR_MODE", "required": True, "game_mode": mode,
            "note": "Never force F1 or a portrait switch",
        },
        {
            "step": "OPEN_CHEAT_CONSOLE", "required": True,
            "chord": list(seq["open_console_chord"]),
            "chord_label": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
        },
        {
            "step": "ACTIVATE_TESTING_CHEATS", "required": True,
            "command": "testingcheats true",
        },
        {
            "step": "SET_EXACT_FUNDS", "required": True,
            "command": seq["set_funds_template"].format(amount=target),
        },
        {
            "step": "VERIFY_HOUSEHOLD_FUNDS", "required": True,
            "target": target, "note": "Observe HUD before any potential retry",
        },
    ]
    return {
        **base,
        "state": "FUNDS_INJECT_PLAN_READY",
        "next_gate": "EXECUTE_FUNDS_INJECT_WITH_ADMISSION",
        "funds_observed": current,
        "remaining": target - current,
        "steps": steps,
    }


def evaluate_subsidy_gate(
    funds: float,
    *,
    choice: Optional[str] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
    cfg: Optional[dict] = None,
) -> dict:
    cfg = cfg or load_contract()
    current = _funds_int(funds, "OBSERVED_FUNDS")
    prompt = subsidy_prompt(cfg)
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER", "next_gate": "YIELD_TO_PLAYER",
            "prompt": prompt, "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
        }
    if not needs_subsidy_prompt(current, cfg):
        return {
            "state": "SUBSIDY_NOT_NEEDED", "next_gate": "CONTINUE_HOST",
            "funds": current, "trigger_below": cfg["subsidy"]["trigger_funds_below"],
            "prompt": prompt, "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
        }
    if choice is None:
        return {
            "state": "SUBSIDY_PROMPT_REQUIRED", "next_gate": "SHOW_SUBSIDY_PROMPT",
            "funds": current, "prompt": prompt,
            "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
        }
    yes_id = cfg["subsidy"]["option_yes"]["option_id"]
    no_id = cfg["subsidy"]["option_no"]["option_id"]
    if choice == no_id or choice in ("no", "decline_subsidy", "No Thanks"):
        return {
            "state": "SUBSIDY_DECLINED", "next_gate": "CONTINUE_HOST",
            "funds": current, "prompt": prompt,
            "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
        }
    if choice != yes_id and choice not in ("yes", "accept_subsidy", "Yes, Please"):
        raise FundsInjectError("UNKNOWN_SUBSIDY_CHOICE")
    plan = plan_inject(funds_observed=current, game_mode=game_mode, cfg=cfg)
    return {
        "state": "SUBSIDY_ACCEPTED", "next_gate": plan["next_gate"],
        "funds": current, "prompt": prompt,
        "inject": plan, "game_mode": game_mode, "proof_ceiling": cfg["proof_ceiling"],
    }


def steps_to_commands(plan: Mapping[str, object]) -> list[str]:
    """Only the canonical two commands are admissible for host dispatch."""
    if plan.get("state") != "FUNDS_INJECT_PLAN_READY":
        raise FundsInjectError("FUNDS_PLAN_NOT_EXECUTABLE")
    target = _funds_int(plan.get("target_funds"), "TARGET", positive=True)
    commands = []
    for step in plan.get("steps") or []:
        if not isinstance(step, Mapping):
            raise FundsInjectError("INVALID_FUNDS_STEP")
        cmd = step.get("command")
        if cmd is not None:
            if not isinstance(cmd, str):
                raise FundsInjectError("INVALID_FUNDS_COMMAND")
            commands.append(cmd)
    expected = ["testingcheats true", f"money {target}"]
    if commands != expected:
        raise FundsInjectError("FUNDS_COMMAND_STACK_UNSAFE")
    return commands


def verify_funds_outcome(
    plan: Mapping[str, object],
    *,
    funds_after: float,
    evidence_ref: Optional[str] = None,
) -> dict:
    """Classify an external HUD observation; never trigger an automatic retry."""
    if plan.get("state") != "FUNDS_INJECT_PLAN_READY":
        raise FundsInjectError("FUNDS_PLAN_NOT_EXECUTABLE")
    target = _funds_int(plan.get("target_funds"), "TARGET", positive=True)
    observed = _funds_int(funds_after, "OBSERVED_FUNDS")
    reference = str(evidence_ref or "").strip()
    verified = observed >= target and bool(reference)
    return {
        "state": (
            "TARGET_ATTESTED_BY_EXTERNAL_OBSERVATION" if verified
            else "FUNDS_NOT_VERIFIED"
        ),
        "target": target,
        "funds_after_reported": observed,
        "evidence_ref": reference or None,
        "next_gate": "CONTINUE_HOST" if verified else "RECHECK_UI_WITH_PLAYER",
        "auto_retry": False,
        "proof_ceiling": "EXTERNAL_OBSERVATION_ATTESTATION_NOT_GAME_CERTIFICATION",
    }
