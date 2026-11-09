"""School Join vs Send Alone click planning and post-click verification.

Regression owner (2026-11-09 RCA): an agent intended Send Alone but clicked the
legacy point (960,600), which actually hit JOIN, and the Sim traveled to school.
Intent is never proof. This module is evaluate-only: it plans, scores and
verifies; it never sends input. Execution (optional, gated, default off) lives
in scripts/school_attend_click.py and reuses the detached SendInput helper in
scripts/cas_quiz_okay.py. Cursor computer-use overlay clicks never reach the
Sims UI and are forbidden as an executor.

Layout comes from contracts/decision-prompts.v1.json
(school.attend.join_or_send_alone -> hit_targets). Hit thresholds come from
click_error_eval so there is one owner of click-error policy.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence, Tuple

from betterinstincts.click_error_eval import ClickErrorEvalError, evaluate_click, load_contract_eval
from betterinstincts.decision_eval import SCHOOL_PROMPT_ID, DecisionEvalError, get_prompt

PASS_STATE = "SEND_ALONE_VERIFIED"
FAIL_STATE = "JOIN_MISCLICK_CONFIRMED"
LEGACY_STATE = "SUPERSEDED_FORBIDDEN_POINT"
CALIBRATION_SOURCES = frozenset({"PRINTWINDOW_MEASURED", "OPERATOR_MEASURED"})
FORBIDDEN_EXECUTORS = frozenset({
    "computer_use_overlay", "cursor_computer_use", "computer-use", "computer_use", "overlay",
})
REQUIRED_EXECUTOR = "native_sendinput_detached"
PROOF_CEILING = "OFFLINE_CLICK_VERIFY_POLICY_NOT_LIVE_SEND_ALONE_PASS"

Box = Tuple[int, int, int, int]  # left, top, right, bottom (inclusive)


class SchoolAttendClickError(ValueError):
    """Invalid layout, observation or request; never a live gameplay success."""


def _int(value, label: str, lo: int = 0, hi: int = 16_000) -> int:
    if type(value) is not int or not (lo <= value <= hi):
        raise SchoolAttendClickError("VALUE_OUT_OF_RANGE:" + label)
    return value


def load_hit_targets(catalog: Optional[dict] = None) -> dict:
    try:
        prompt = get_prompt(SCHOOL_PROMPT_ID, catalog)
    except DecisionEvalError as exc:  # pragma: no cover - catalog drift
        raise SchoolAttendClickError("SCHOOL_PROMPT_MISSING") from exc
    cfg = prompt.get("hit_targets")
    if not isinstance(cfg, dict):
        raise SchoolAttendClickError("HIT_TARGETS_MISSING")
    layout = cfg.get("layout_model") or {}
    if layout.get("order_top_to_bottom") != ["join", "send_alone"]:
        raise SchoolAttendClickError("LAYOUT_MUST_STACK_JOIN_ABOVE_SEND_ALONE")
    for key in ("modal_center_x", "provisional_join_y", "pill_half_width", "pill_half_height", "gap_px"):
        _int(layout.get(key), key)
    if layout["gap_px"] <= 2 * layout["pill_half_height"]:
        raise SchoolAttendClickError("PILLS_MUST_NOT_OVERLAP")
    legacy = cfg.get("legacy") or {}
    xy = legacy.get("send_alone_screen_xy")
    if (
        not isinstance(xy, list) or len(xy) != 2
        or not str(legacy.get("status", "")).startswith("SUPERSEDED")
    ):
        raise SchoolAttendClickError("LEGACY_POINT_MUST_BE_SUPERSEDED")
    if cfg.get("execute_allowed_default") is not False:
        raise SchoolAttendClickError("EXECUTE_MUST_DEFAULT_FALSE")
    policy = cfg.get("executor_policy") or {}
    if policy.get("required") != REQUIRED_EXECUTOR or "computer_use_overlay" not in set(policy.get("forbidden") or []):
        raise SchoolAttendClickError("EXECUTOR_POLICY_DRIFT")
    post = cfg.get("post_click") or {}
    if post.get("expected_lot_kind") != "home" or post.get("fail_state") != FAIL_STATE or post.get("pass_state") != PASS_STATE:
        raise SchoolAttendClickError("POST_CLICK_CONTRACT_DRIFT")
    return cfg


def resolve_layout(
    *,
    cfg: Optional[dict] = None,
    measured_join_y: Optional[int] = None,
    modal_center_x: Optional[int] = None,
) -> dict:
    """Relative stack: send_alone_y = join_y + gap. Returns both pill boxes."""
    cfg = cfg or load_hit_targets()
    layout = cfg["layout_model"]
    cx = _int(modal_center_x if modal_center_x is not None else layout["modal_center_x"], "modal_center_x")
    join_y = _int(measured_join_y if measured_join_y is not None else layout["provisional_join_y"], "join_y")
    hw, hh, gap = int(layout["pill_half_width"]), int(layout["pill_half_height"]), int(layout["gap_px"])
    send_y = join_y + gap
    join_box: Box = (cx - hw, join_y - hh, cx + hw, join_y + hh)
    send_box: Box = (cx - hw, send_y - hh, cx + hw, send_y + hh)
    if send_box[1] <= join_box[3]:
        raise SchoolAttendClickError("SEND_ALONE_NOT_STRICTLY_BELOW_JOIN")
    return {
        "modal_center_x": cx,
        "join_y": join_y,
        "send_alone_y": send_y,
        "join_center": [cx, join_y],
        "send_alone_center": [cx, send_y],
        "join_box": list(join_box),
        "send_alone_box": list(send_box),
        "measured": measured_join_y is not None,
    }


def _in_box(xy: Tuple[int, int], box: Sequence[int]) -> bool:
    return box[0] <= xy[0] <= box[2] and box[1] <= xy[1] <= box[3]


def _is_legacy(xy: Tuple[int, int], cfg: dict) -> bool:
    legacy = cfg["legacy"]["send_alone_screen_xy"]
    return xy[0] == int(legacy[0]) and xy[1] == int(legacy[1])


def score_option_hit(
    intended_option: str,
    observed_xy: Sequence[int],
    join_box: Sequence[int],
    send_alone_box: Sequence[int],
    *,
    client_width: int = 1920,
    client_height: int = 1080,
    eval_cfg: Optional[dict] = None,
) -> dict:
    """Which pill did a point land in, and was it the intended one?

    Pixel error against the intended pill center uses click_error_eval's
    thresholds; the pill box decides which option was actually hit.
    """
    if intended_option not in {"join", "send_alone"}:
        raise SchoolAttendClickError("UNKNOWN_INTENDED_OPTION")
    if len(observed_xy) != 2:
        raise SchoolAttendClickError("OBSERVED_XY_REQUIRED")
    xy = (_int(observed_xy[0], "observed_x"), _int(observed_xy[1], "observed_y"))
    for box in (join_box, send_alone_box):
        if len(box) != 4:
            raise SchoolAttendClickError("BOX_REQUIRED")
    if send_alone_box[1] <= join_box[3]:
        raise SchoolAttendClickError("SEND_ALONE_NOT_STRICTLY_BELOW_JOIN")
    if _in_box(xy, join_box):
        hit = "join"
    elif _in_box(xy, send_alone_box):
        hit = "send_alone"
    else:
        hit = "none"
    boxes = {"join": join_box, "send_alone": send_alone_box}
    ibox = boxes[intended_option]
    center = ((ibox[0] + ibox[2]) // 2, (ibox[1] + ibox[3]) // 2)
    try:
        err = evaluate_click(
            intended_x=center[0], intended_y=center[1], observed_x=xy[0], observed_y=xy[1],
            client_width=client_width, client_height=client_height,
            target_id=intended_option, cfg=eval_cfg or load_contract_eval(),
        )
    except ClickErrorEvalError as exc:
        raise SchoolAttendClickError("CLICK_ERROR_EVAL_FAILED:" + str(exc)) from exc
    if hit == intended_option:
        verdict = "INTENDED_OPTION_HIT"
    elif hit == "none":
        verdict = "MISS_BOTH_PILLS"
    else:
        verdict = "WRONG_OPTION_HIT"
    return {
        "schema": "betterinstincts.school-attend-click.score/v1",
        "intended_option": intended_option,
        "hit_option": hit,
        "intended_hit": hit == intended_option,
        "join_hit": hit == "join",
        "send_alone_hit": hit == "send_alone",
        "verdict": verdict,
        "classification": err["classification"],
        "error_px": err["error_px"],
        "join_misclick_suspected": intended_option == "send_alone" and hit == "join",
        "auto_reclick_allowed": False,
        "next": "VERIFY_POST_CLICK_OBSERVATION" if hit != "none" else "HALT_NO_CLICK_REGISTERED_ON_A_PILL",
        "execute_allowed": False,
        "proof_ceiling": PROOF_CEILING,
    }


def plan_send_alone_click(
    *,
    executor: str = REQUIRED_EXECUTOR,
    measured_join_y: Optional[int] = None,
    calibration_source: Optional[str] = None,
    dialog_observed: bool = False,
    candidate_xy: Optional[Sequence[int]] = None,
    client_width: int = 1920,
    client_height: int = 1080,
    execute: bool = False,
    catalog: Optional[dict] = None,
) -> dict:
    """Evaluate-only plan for a Send Alone click; ready only when calibrated.

    `execute` is a request flag only: this function never sends input, and
    `execute_allowed` stays False. `ready_to_execute` tells a gated executor
    whether every pre-click obligation holds.
    """
    cfg = load_hit_targets(catalog)
    blockers: list[str] = []
    layout = resolve_layout(cfg=cfg, measured_join_y=measured_join_y)
    norm_executor = str(executor).strip().lower()
    if norm_executor in FORBIDDEN_EXECUTORS:
        blockers.append("COMPUTER_USE_OVERLAY_EXECUTOR_FORBIDDEN")
    elif norm_executor != REQUIRED_EXECUTOR:
        blockers.append("EXECUTOR_MUST_BE_" + REQUIRED_EXECUTOR)
    if measured_join_y is None:
        blockers.append("LAYOUT_PROVISIONAL_UNCALIBRATED")
    elif calibration_source not in CALIBRATION_SOURCES:
        blockers.append("CALIBRATION_SOURCE_REQUIRED")
    if not dialog_observed:
        blockers.append("PRE_CLICK_DIALOG_OBSERVATION_REQUIRED")
    target = tuple(layout["send_alone_center"])
    if candidate_xy is not None:
        if len(candidate_xy) != 2:
            raise SchoolAttendClickError("CANDIDATE_XY_REQUIRED")
        target = (_int(candidate_xy[0], "candidate_x"), _int(candidate_xy[1], "candidate_y"))
        if _is_legacy(target, cfg):
            blockers.append(LEGACY_STATE)
    score = score_option_hit(
        "send_alone", target, layout["join_box"], layout["send_alone_box"],
        client_width=client_width, client_height=client_height,
    )
    if not score["intended_hit"]:
        blockers.append("TARGET_NOT_INSIDE_SEND_ALONE_BOX")
    if score["join_hit"]:
        blockers.append("TARGET_INSIDE_JOIN_BOX")
    if target[1] <= layout["join_box"][3]:
        blockers.append("SEND_ALONE_NOT_STRICTLY_BELOW_JOIN")
    blockers = sorted(set(blockers))
    return {
        "schema": "betterinstincts.school-attend-click.plan/v1",
        "intended_option": "send_alone",
        "target_xy": list(target),
        "layout": layout,
        "layout_status": (
            "MEASURED"
            if measured_join_y is not None and calibration_source in CALIBRATION_SOURCES
            else cfg["status"]
        ),
        "score_vs_layout": score,
        "executor": {
            "requested": executor,
            "required": REQUIRED_EXECUTOR,
            "reference": cfg["executor_policy"]["reference"],
            "forbidden": list(cfg["executor_policy"]["forbidden"]),
        },
        "legacy_forbidden_point": {
            "xy": list(cfg["legacy"]["send_alone_screen_xy"]),
            "status": cfg["legacy"]["status"],
            "actual_hit": cfg["legacy"]["actual_hit"],
        },
        "blockers": blockers,
        "ready_to_execute": not blockers,
        "execute_requested": bool(execute),
        "execute_allowed": False,
        "post_click_required": {
            "pass_state": PASS_STATE,
            "fail_state": FAIL_STATE,
            "expected_lot_kind": cfg["post_click"]["expected_lot_kind"],
            "claim_rule": cfg["post_click"]["rule"],
        },
        "proof_ceiling": PROOF_CEILING,
    }


def verify_post_click(
    observation: Mapping,
    *,
    catalog: Optional[dict] = None,
) -> dict:
    """PASS only when the Sim is still on the home lot with the dialog gone.

    Observation keys: lot_kind (home|school|unknown), school_hud_visible (bool),
    dialog_present (bool), text_cues (list[str]), source (PRINTWINDOW|OPERATOR_OBSERVED),
    age_s (seconds since capture). Any school cue is FAIL JOIN_MISCLICK_CONFIRMED,
    regardless of other fields. Missing/stale/unknown => HOLD (no verification claim).
    """
    post = load_hit_targets(catalog)["post_click"]
    if not isinstance(observation, Mapping):
        raise SchoolAttendClickError("OBSERVATION_MUST_BE_OBJECT")
    lot = str(observation.get("lot_kind", "unknown")).strip().lower()
    hud = observation.get("school_hud_visible")
    dialog = observation.get("dialog_present")
    cues = observation.get("text_cues") or []
    if isinstance(cues, str):
        cues = [cues]
    if not isinstance(cues, (list, tuple)):
        raise SchoolAttendClickError("TEXT_CUES_MUST_BE_LIST")
    text = " | ".join(str(c).lower() for c in cues)
    school_cues = sorted({c for c in post["school_text_cues"] if c in text})
    reasons: list[str] = []
    if lot == "school":
        reasons.append("LOT_KIND_SCHOOL")
    if hud is True:
        reasons.append("SCHOOL_HUD_VISIBLE")
    reasons.extend("SCHOOL_CUE:" + c.replace(" ", "_") for c in school_cues)
    base = {
        "schema": "betterinstincts.school-attend-click.verify/v1",
        "expected_lot_kind": post["expected_lot_kind"],
        "observed_lot_kind": lot,
        "school_cues": school_cues,
        "auto_reclick_allowed": False,
        "execute_allowed": False,
        "proof_ceiling": PROOF_CEILING,
    }
    if reasons:
        return {
            **base,
            "state": FAIL_STATE,
            "passed": False,
            "fail_closed": True,
            "reasons": reasons,
            "next": "HALT_NO_RECLICK_REPORT_OPERATOR_HOME_RETURN_OWNED_BY_OPERATOR",
        }
    holds: list[str] = []
    if observation.get("source") not in set(post["observation_sources"]):
        holds.append("OBSERVATION_SOURCE_UNTRUSTED")
    age = observation.get("age_s")
    if type(age) not in (int, float) or age < 0 or age > int(post["max_observation_age_s"]):
        holds.append("OBSERVATION_STALE_OR_UNDATED")
    if lot != post["expected_lot_kind"]:
        holds.append("LOT_KIND_NOT_CONFIRMED_HOME")
    if hud is not False:
        holds.append("SCHOOL_HUD_ABSENCE_NOT_OBSERVED")
    if dialog is not False:
        holds.append("DIALOG_GONE_NOT_OBSERVED")
    if holds:
        return {
            **base,
            "state": "SEND_ALONE_UNVERIFIED",
            "passed": False,
            "fail_closed": True,
            "reasons": holds,
            "next": "OBTAIN_FRESH_PRINTWINDOW_OBSERVATION_NO_SEND_ALONE_CLAIM",
        }
    return {
        **base,
        "state": PASS_STATE,
        "passed": True,
        "fail_closed": False,
        "reasons": ["HOME_LOT_DIALOG_GONE_SCHOOL_HUD_ABSENT"],
        "next": "OBSERVATION_ONLY_NOT_GAME_CERTIFIED",
    }
