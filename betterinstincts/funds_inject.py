"""Mode-agnostic household-funds inject plan for the Windows game host.

P95 stack: soft-focus Sims → Ctrl+Shift+C → testingcheats enabled true →
Money N (best-effort) → motherlode chunks. Works in Live, Build, or Buy —
never force F1 / mode switch while the operator is building.

Library plans only; scripts/funds_inject.py owns SendInput. Never edits saves.
Subsidy and BI-004 earned income are different proof ceilings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "host-funds.v1.json"
MAX_BYTES = 48_000


class FundsInjectError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise FundsInjectError("HOST_FUNDS_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.host-funds/v1":
        raise FundsInjectError("BAD_HOST_FUNDS_SCHEMA")
    seq = cfg.get("inject_sequence") or {}
    if seq.get("activate_testing_cheats") != "testingcheats enabled true":
        raise FundsInjectError("TESTINGCHEATS_ENABLED_TRUE_REQUIRED")
    if list(seq.get("open_console_chord") or []) != ["CTRL", "SHIFT", "C"]:
        raise FundsInjectError("CTRL_SHIFT_C_CONSOLE_CHORD_REQUIRED")
    if seq.get("mode_agnostic") is not True:
        raise FundsInjectError("MODE_AGNOSTIC_REQUIRED")
    if seq.get("never_force_mode_switch") is not True:
        raise FundsInjectError("NEVER_FORCE_MODE_SWITCH_REQUIRED")
    if seq.get("require_live_mode") is True:
        raise FundsInjectError("REQUIRE_LIVE_MODE_FORBIDDEN")
    if seq.get("durable_additive_command") != "motherlode":
        raise FundsInjectError("MOTHERLODE_FALLBACK_REQUIRED")
    if not isinstance(seq.get("durable_additive_chunk"), (int, float)) or float(seq["durable_additive_chunk"]) <= 0:
        raise FundsInjectError("MOTHERLODE_CHUNK_REQUIRED")
    if "Money {amount}" not in str(seq.get("set_funds_template", "")):
        raise FundsInjectError("MONEY_TEMPLATE_REQUIRED")
    sub = cfg.get("subsidy") or {}
    if not isinstance(sub.get("trigger_funds_below"), (int, float)):
        raise FundsInjectError("SUBSIDY_TRIGGER_REQUIRED")
    if not isinstance(sub.get("boost_to"), (int, float)) or float(sub["boost_to"]) <= 0:
        raise FundsInjectError("SUBSIDY_BOOST_REQUIRED")
    return cfg


def needs_subsidy_prompt(funds: float, cfg: Optional[dict] = None) -> bool:
    cfg = cfg or load_contract()
    if isinstance(funds, bool) or not isinstance(funds, (int, float)) or funds < 0:
        raise FundsInjectError("INVALID_FUNDS")
    return float(funds) < float(cfg["subsidy"]["trigger_funds_below"])


def subsidy_prompt(cfg: Optional[dict] = None) -> dict:
    """Sims-styled chance-card payload for the host overlay / decision catalog."""
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
    """Return ordered console steps. Mode-agnostic; does not touch the game."""
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "next_gate": "YIELD_TO_PLAYER",
            "steps": [],
            "game_mode": game_mode,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    seq = cfg["inject_sequence"]
    allowed = {str(m) for m in (seq.get("allowed_modes") or [])}
    mode = str(game_mode or "unknown").lower()
    if allowed and mode not in allowed:
        raise FundsInjectError("UNSUPPORTED_GAME_MODE")
    boost = float(cfg["subsidy"]["boost_to"] if amount is None else amount)
    if boost <= 0 or boost != int(boost):
        raise FundsInjectError("AMOUNT_MUST_BE_POSITIVE_INTEGER")
    amount_i = int(boost)
    money_cmd = str(seq["set_funds_template"]).format(amount=amount_i)
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
            "step": "OPEN_CHEAT_CONSOLE",
            "chord": list(seq["open_console_chord"]),
            "chord_label": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
            "required": True,
            "note": seq.get(
                "open_console_note",
                "Ctrl+Shift+C opens the cheat console in any playable mode",
            ),
        },
        {
            "step": "ACTIVATE_TESTING_CHEATS",
            "command": seq["activate_testing_cheats"],
            "alias": seq.get("activate_testing_cheats_alias"),
            "required": True,
            "note": "Must precede funds commands; user correction 2026-11-07",
        },
        {
            "step": "TRY_SET_EXACT_FUNDS",
            "command": money_cmd,
            "required": False,
            "note": "Best-effort exact set; motherlode is the durable path",
        },
    ]
    chunk = int(seq["durable_additive_chunk"])
    # Additive chunks toward boost_to from zero-ish; when funds_observed known,
    # only request remaining chunks (tandem-safe: do not dump another full 1M).
    remaining = amount_i
    if funds_observed is not None and float(funds_observed) >= 0:
        remaining = max(0, amount_i - int(float(funds_observed)))
    motherlode_n = 0 if remaining <= 0 else max(1, (remaining + chunk - 1) // chunk)
    for i in range(motherlode_n):
        steps.append({
            "step": "ADD_FUNDS_CHUNK",
            "command": "motherlode",
            "chunk": chunk,
            "index": i + 1,
            "of": motherlode_n,
            "required": True,
        })
    if seq.get("close_console_optional", True):
        steps.append({
            "step": "CLOSE_CHEAT_CONSOLE",
            "key": seq["close_console_key"],
            "required": False,
            "note": "Optional — avoid Esc spam that opens the pause MENU while building",
        })
    return {
        "state": "FUNDS_INJECT_PLAN_READY",
        "next_gate": "EXECUTE_FUNDS_INJECT",
        "amount": amount_i,
        "funds_observed": funds_observed,
        "remaining": remaining if funds_observed is not None else amount_i,
        "motherlode_count": motherlode_n,
        "game_mode": mode,
        "mode_agnostic": True,
        "open_console": seq.get("open_console_chord_label", "Ctrl+Shift+C"),
        "steps": steps,
        "forbidden": list(seq.get("forbidden") or []),
        "invariants": list(cfg.get("invariants") or []),
        "proof_ceiling": cfg["proof_ceiling"],
    }


def evaluate_subsidy_gate(
    funds: float,
    *,
    choice: Optional[str] = None,
    player_directed: bool = False,
    game_mode: str = "unknown",
    cfg: Optional[dict] = None,
) -> dict:
    """Host gate: under trigger → prompt; accept → inject plan; decline → hold."""
    cfg = cfg or load_contract()
    prompt = subsidy_prompt(cfg)
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "next_gate": "YIELD_TO_PLAYER",
            "prompt": prompt,
            "game_mode": game_mode,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if not needs_subsidy_prompt(funds, cfg):
        return {
            "state": "SUBSIDY_NOT_NEEDED",
            "next_gate": "CONTINUE_HOST",
            "funds": float(funds),
            "trigger_below": cfg["subsidy"]["trigger_funds_below"],
            "prompt": prompt,
            "game_mode": game_mode,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if choice is None:
        return {
            "state": "SUBSIDY_PROMPT_REQUIRED",
            "next_gate": "SHOW_SUBSIDY_PROMPT",
            "funds": float(funds),
            "prompt": prompt,
            "game_mode": game_mode,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    yes_id = cfg["subsidy"]["option_yes"]["option_id"]
    no_id = cfg["subsidy"]["option_no"]["option_id"]
    if choice == no_id or choice in ("no", "decline_subsidy", "No Thanks"):
        return {
            "state": "SUBSIDY_DECLINED",
            "next_gate": "CONTINUE_HOST",
            "funds": float(funds),
            "prompt": prompt,
            "game_mode": game_mode,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if choice != yes_id and choice not in ("yes", "accept_subsidy", "Yes, Please"):
        raise FundsInjectError("UNKNOWN_SUBSIDY_CHOICE")
    plan = plan_inject(funds_observed=funds, game_mode=game_mode, cfg=cfg)
    return {
        "state": "SUBSIDY_ACCEPTED",
        "next_gate": "EXECUTE_FUNDS_INJECT",
        "funds": float(funds),
        "prompt": prompt,
        "inject": plan,
        "game_mode": game_mode,
        "proof_ceiling": cfg["proof_ceiling"],
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
        raise FundsInjectError("INJECT_MUST_START_WITH_TESTINGCHEATS_ENABLED_TRUE")
    return out
