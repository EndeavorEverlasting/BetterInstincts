"""Score intended ui_chrome targets vs observed clicks; Escape-cancel on miss.

Evaluate-only. Quantifies pixel/normalized error, ABOVE_TARGET lot punch-through
risk, and whether a recipe must halt. Never SendInput.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.ui_chrome import UIChromeError, load_contract, resolve_target

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "click-error-eval.v1.json"
MAX_BYTES = 48_000


class ClickErrorEvalError(ValueError):
    pass


def load_contract_eval(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ClickErrorEvalError("CLICK_ERROR_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.click-error-eval/v1":
        raise ClickErrorEvalError("BAD_CLICK_ERROR_SCHEMA")
    if cfg.get("architecture", {}).get("selected") != "POST_CLICK_VERIFY_ESCAPE_CANCEL":
        raise ClickErrorEvalError("CLICK_ERROR_ARCHITECTURE_DRIFT")
    if cfg.get("execute_allowed_default") is not False:
        raise ClickErrorEvalError("CLICK_ERROR_MUST_DEFAULT_EXECUTE_FALSE")
    thr = cfg.get("thresholds_px") or {}
    if not isinstance(thr.get("hit_radius"), int) or not isinstance(thr.get("near_miss_radius"), int):
        raise ClickErrorEvalError("THRESHOLDS_REQUIRED")
    if thr["hit_radius"] < 1 or thr["near_miss_radius"] < thr["hit_radius"]:
        raise ClickErrorEvalError("THRESHOLDS_INVALID")
    recovery = cfg.get("recovery") or {}
    if recovery.get("on_non_hit") != "ESCAPE_CANCEL" or recovery.get("continue_recipe") is not False:
        raise ClickErrorEvalError("RECOVERY_MUST_ESCAPE_CANCEL_AND_HALT")
    if "AUTO_RECLICK" not in set(recovery.get("forbidden") or []):
        raise ClickErrorEvalError("RECOVERY_MUST_FORBID_AUTO_RECLICK")
    return cfg


def evaluate_click(
    *,
    intended_x: int,
    intended_y: int,
    observed_x: int,
    observed_y: int,
    client_width: int,
    client_height: int,
    target_id: Optional[str] = None,
    mode: Optional[str] = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Compare one observed client-pixel click to an intended point."""
    cfg = cfg or load_contract_eval()
    if type(client_width) is not int or type(client_height) is not int:
        raise ClickErrorEvalError("CLIENT_SIZE_REQUIRED")
    if client_width < 320 or client_height < 240:
        raise ClickErrorEvalError("CLIENT_SIZE_TOO_SMALL")
    for label, val in (
        ("intended_x", intended_x),
        ("intended_y", intended_y),
        ("observed_x", observed_x),
        ("observed_y", observed_y),
    ):
        if type(val) is not int or not (0 <= val <= 16_000):
            raise ClickErrorEvalError("CLICK_COORDS_OUT_OF_RANGE:" + label)

    dx = observed_x - intended_x
    dy = observed_y - intended_y
    err = math.hypot(dx, dy)
    hit_r = int(cfg["thresholds_px"]["hit_radius"])
    near_r = int(cfg["thresholds_px"]["near_miss_radius"])
    if err <= hit_r:
        classification = "HIT"
    elif err <= near_r:
        classification = "NEAR_MISS"
    else:
        classification = "MISS"

    if abs(dy) <= hit_r:
        vertical_bias = "NONE"
    elif dy < 0:
        vertical_bias = "ABOVE_TARGET"
    else:
        vertical_bias = "BELOW_TARGET"

    surface_risk = "NONE"
    if (
        vertical_bias == "ABOVE_TARGET"
        and classification != "HIT"
        and intended_y >= int(0.70 * client_height)
    ):
        surface_risk = "LOT_PUNCH_THROUGH_RISK"

    return {
        "schema": "betterinstincts.click-error-eval.result/v1",
        "target_id": target_id,
        "mode": mode,
        "intended": {"x": intended_x, "y": intended_y},
        "observed": {"x": observed_x, "y": observed_y},
        "error_px": {"dx": dx, "dy": dy, "euclidean": round(err, 3)},
        "error_normalized": {
            "dx": round(dx / client_width, 6),
            "dy": round(dy / client_height, 6),
            "euclidean": round(err / math.hypot(client_width, client_height), 6),
        },
        "classification": classification,
        "vertical_bias": vertical_bias,
        "surface_risk": surface_risk,
        "thresholds_px": {"hit_radius": hit_r, "near_miss_radius": near_r},
        "client_width": client_width,
        "client_height": client_height,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def decide_post_click(result: Mapping, *, cfg: Optional[dict] = None) -> dict:
    """Halt recipe and plan Escape cancel when the click was not a HIT."""
    cfg = cfg or load_contract_eval()
    classification = result.get("classification")
    if classification not in {"HIT", "NEAR_MISS", "MISS"}:
        raise ClickErrorEvalError("RESULT_CLASSIFICATION_REQUIRED")
    recovery = cfg["recovery"]
    if classification == "HIT":
        return {
            "schema": "betterinstincts.click-error-eval.decision/v1",
            "decision": "CONTINUE",
            "continue_recipe": True,
            "recovery": None,
            "classification": classification,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "schema": "betterinstincts.click-error-eval.decision/v1",
        "decision": "ESCAPE_CANCEL",
        "continue_recipe": False,
        "recovery": {
            "op": "KEY",
            "chord": list(recovery["chord"]),
            "hotkey_id": recovery["hotkey_id"],
            "reason": "CLICK_MISSED_TARGET",
            "forbidden": list(recovery["forbidden"]),
        },
        "classification": classification,
        "vertical_bias": result.get("vertical_bias"),
        "surface_risk": result.get("surface_risk"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def evaluate_against_chrome(
    *,
    target_id: str,
    mode: str,
    observed_x: int,
    observed_y: int,
    client_width: int,
    client_height: int,
    profile: Optional[str] = None,
    chrome_cfg: Optional[dict] = None,
    eval_cfg: Optional[dict] = None,
) -> dict:
    """Resolve a named chrome target, score the observed click, decide recovery."""
    eval_cfg = eval_cfg or load_contract_eval()
    try:
        resolved = resolve_target(
            target_id,
            mode=mode,
            profile=profile,
            client_width=client_width,
            client_height=client_height,
            cfg=chrome_cfg or load_contract(),
        )
    except UIChromeError as exc:
        raise ClickErrorEvalError("CHROME_RESOLVE_FAILED:" + str(exc)) from exc
    if "x" not in resolved or "y" not in resolved:
        raise ClickErrorEvalError("CHROME_TARGET_PIXELS_REQUIRED")
    scored = evaluate_click(
        intended_x=int(resolved["x"]),
        intended_y=int(resolved["y"]),
        observed_x=observed_x,
        observed_y=observed_y,
        client_width=client_width,
        client_height=client_height,
        target_id=target_id,
        mode=mode,
        cfg=eval_cfg,
    )
    scored["resolved_target"] = {
        "nx": resolved["nx"],
        "ny": resolved["ny"],
        "shared_ref": resolved["shared_ref"],
        "status": resolved.get("status"),
    }
    scored["post_click"] = decide_post_click(scored, cfg=eval_cfg)
    return scored


def evaluate_session(
    trials: Sequence[Mapping],
    *,
    eval_cfg: Optional[dict] = None,
) -> dict:
    """Aggregate multiple click trials into miss/bias/recovery rates."""
    eval_cfg = eval_cfg or load_contract_eval()
    if not isinstance(trials, (list, tuple)) or not trials:
        raise ClickErrorEvalError("TRIALS_REQUIRED")
    if len(trials) > 256:
        raise ClickErrorEvalError("TOO_MANY_TRIALS")
    results = []
    for raw in trials:
        if not isinstance(raw, Mapping):
            raise ClickErrorEvalError("TRIAL_MUST_BE_OBJECT")
        if "target_id" in raw and "mode" in raw:
            results.append(
                evaluate_against_chrome(
                    target_id=str(raw["target_id"]),
                    mode=str(raw["mode"]),
                    observed_x=int(raw["observed_x"]),
                    observed_y=int(raw["observed_y"]),
                    client_width=int(raw["client_width"]),
                    client_height=int(raw["client_height"]),
                    profile=raw.get("profile"),
                    eval_cfg=eval_cfg,
                )
            )
        else:
            scored = evaluate_click(
                intended_x=int(raw["intended_x"]),
                intended_y=int(raw["intended_y"]),
                observed_x=int(raw["observed_x"]),
                observed_y=int(raw["observed_y"]),
                client_width=int(raw["client_width"]),
                client_height=int(raw["client_height"]),
                target_id=raw.get("target_id"),
                mode=raw.get("mode"),
                cfg=eval_cfg,
            )
            scored["post_click"] = decide_post_click(scored, cfg=eval_cfg)
            results.append(scored)

    errors = [float(r["error_px"]["euclidean"]) for r in results]
    errors_sorted = sorted(errors)
    n = len(errors_sorted)
    p95 = errors_sorted[min(n - 1, max(0, int(math.ceil(0.95 * n) - 1)))]
    counts = {"HIT": 0, "NEAR_MISS": 0, "MISS": 0}
    bias = {"NONE": 0, "ABOVE_TARGET": 0, "BELOW_TARGET": 0}
    lot_risk = 0
    escape_cancels = 0
    for r in results:
        counts[r["classification"]] += 1
        bias[r["vertical_bias"]] += 1
        if r["surface_risk"] == "LOT_PUNCH_THROUGH_RISK":
            lot_risk += 1
        if r.get("post_click", {}).get("decision") == "ESCAPE_CANCEL":
            escape_cancels += 1

    return {
        "schema": "betterinstincts.click-error-eval.session/v1",
        "trial_count": n,
        "classifications": counts,
        "vertical_bias": bias,
        "lot_punch_through_risk_count": lot_risk,
        "escape_cancel_count": escape_cancels,
        "error_px": {
            "mean": round(sum(errors) / n, 3),
            "max": round(max(errors), 3),
            "p95": round(p95, 3),
        },
        "hit_rate": round(counts["HIT"] / n, 4),
        "miss_rate": round(counts["MISS"] / n, 4),
        "above_target_rate": round(bias["ABOVE_TARGET"] / n, 4),
        "trials": results,
        "execute_allowed": False,
        "proof_ceiling": eval_cfg["proof_ceiling"],
    }
