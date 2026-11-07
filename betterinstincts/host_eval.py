"""Deterministic read-only Sims game-host journey and autonomy evaluator.

Supplied observations are not a Sims API. No game, save or desktop mutation.
"""
from __future__ import annotations

import json
import re
from math import isfinite
from pathlib import Path

from betterinstincts.decision_eval import measure_need_deltas
from betterinstincts.host_stack import evaluate_turn
from betterinstincts.instincts_host import NeedSnapshot, all_green

ROOT = Path(__file__).resolve().parents[1]
CASE_FILE = ROOT / "tests" / "fixtures" / "host-eval.v1.json"
EXPECTED = ("launch", "main_menu", "save_selected", "map", "live_mode")
SIX = frozenset(("hunger", "bladder", "energy", "hygiene", "fun", "social"))
BLACK = frozenset(("FULL_CLIENT_BLACK", "VIEWPORT_NEAR_BLACK", "VIEWPORT_BLACK_HUD_ALIVE", "VOID_LOT_PLATFORM_WIREFRAME"))
FORBIDDEN = frozenset(("RESUME", "DELETE_SAVE", "OVERWRITE_SAVE", "TOUCH_USER_SAVE"))
LAB = re.compile(r"BI_(TMP|CONT)_[A-Z0-9_]{4,48}$")


class HostEvalError(ValueError):
    pass


def read_cases(path: Path = CASE_FILE) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise HostEvalError("UNSAFE_CASE_FILE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise HostEvalError("INVALID_CASE_JSON") from exc
    if not isinstance(data, dict) or data.get("schema") != "betterinstincts.host-eval-suite/v1":
        raise HostEvalError("INVALID_CASE_SCHEMA")
    return data


def _needs(raw: object) -> dict:
    if not isinstance(raw, dict) or set(raw) != SIX:
        raise HostEvalError("SIX_NEEDS_REQUIRED")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v < 0 or v > 1 for v in raw.values()):
        raise HostEvalError("INVALID_NEED_VALUE")
    return dict(raw)


def _surface(raw: object, kind: str) -> dict:
    if raw is None:
        return {"state": "SENSOR_NOT_SUPPLIED", "deltas": {}, "count": 0}
    if not isinstance(raw, dict) or not isinstance(raw.get("before"), dict) or not isinstance(raw.get("after"), dict):
        raise HostEvalError("INVALID_" + kind)
    before, after = raw["before"], raw["after"]
    if set(before) != set(after) or len(before) > 32 or any(not isinstance(k, str) or not k or len(k) > 80 for k in before):
        raise HostEvalError("INVALID_" + kind + "_IDENTITIES")
    for v in list(before.values()) + list(after.values()):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v < 0 or (kind == "WHIMS" and v > 1):
            raise HostEvalError("INVALID_" + kind + "_VALUE")
    return {"state": "SUPPLIED_NOT_GAME_API", "count": len(before),
            "deltas": {k: round(after[k] - before[k], 6) for k in sorted(before)}}


def evaluate_case(case: dict) -> dict:
    if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
        raise HostEvalError("INVALID_CASE")
    findings = set()
    patch = json.loads((ROOT / "contracts" / "game-scenes.v1.json").read_text(encoding="utf-8"))["game_version"]
    if case.get("game_version") != patch:
        findings.add("UNKNOWN_GAME_PATCH")
    save = case.get("save", {})
    if not isinstance(save, dict) or save.get("origin") != "LAB_CREATED" or save.get("registry_confirmed") is not True or not isinstance(save.get("alias"), str) or not LAB.fullmatch(save["alias"]):
        findings.add("UNSAFE_SAVE_SELECTION")
    phases = case.get("events", [])
    if not isinstance(phases, list) or len(phases) > 20 or any(not isinstance(e, dict) for e in phases):
        raise HostEvalError("INVALID_BOOT_EVENTS")
    mode = save.get("mode")
    expected = EXPECTED if mode == "chosen" else ("launch", "main_menu", "cas", "placement", "map", "live_mode") if mode == "new" else ()
    stamps = [e.get("time_ms") for e in phases]
    if not stamps or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in stamps):
        raise HostEvalError("INVALID_BOOT_TIMESTAMPS")
    if tuple(e.get("phase") for e in phases) != expected or stamps != sorted(stamps):
        findings.add("BOOT_PATH_INVALID")
    for e in phases:
        if e.get("phase") in ("map", "live_mode"):
            cues = e.get("cues")
            if not isinstance(cues, dict) or not all(isinstance(cues.get(k), str) and cues[k].strip() for k in ("visual", "operator")):
                findings.add("SCENE_TWO_CUES_MISSING")
    actions = case.get("host_actions", [])
    if not isinstance(actions, list) or len(actions) > 32 or any(not isinstance(x, str) for x in actions):
        raise HostEvalError("INVALID_HOST_ACTIONS")
    if FORBIDDEN.intersection(actions):
        findings.add("FORBIDDEN_SAVE_ACTION")
    if "AUTHORIZED_GAME_RESTART" in actions and not case.get("restart_authorized"):
        findings.add("RESTART_NOT_AUTHORIZED")
    if "AUTHORIZED_GAME_RESTART" in actions and not {"DISPOSABLE_RELAUNCH", "PRINTWINDOW_RECHECK"}.issubset(actions):
        findings.add("RESTART_RECEIPT_INCOMPLETE")
    context = case.get("context", {})
    if not isinstance(context, dict):
        raise HostEvalError("INVALID_CONTEXT")
    if context.get("after_cas_abort") and "EMPTY_LOT_CAS_PLAY" in actions:
        findings.add("CAS_ABORT_TRAP_REPLAY")
    view = case.get("viewport", {})
    if not isinstance(view, dict) or view.get("method") != "PrintWindow" or not isinstance(view.get("capture_ref"), str) or not view["capture_ref"].strip():
        findings.add("VIEWPORT_EVIDENCE_MISSING")
    prior = view.get("before")
    after = view.get("after")
    if prior not in BLACK | {"CONTENT_PRESENT"} or after not in BLACK | {"CONTENT_PRESENT"}:
        findings.add("VIEWPORT_UNKNOWN")
    elif after != "CONTENT_PRESENT":
        findings.add("BLACK_VIEWPORT_STILL_ACTIVE")
    if prior in BLACK and after == "CONTENT_PRESENT" and "PRINTWINDOW_RECHECK" not in actions:
        findings.add("RECOVERY_RECHECK_MISSING")
    raw = case.get("needs")
    influence = None
    if raw is not None:
        if not isinstance(raw, dict) or not isinstance(raw.get("host_action_id"), str) or not raw["host_action_id"]:
            raise HostEvalError("INVALID_NEEDS_ACTION_ID")
        before, after_needs = _needs(raw.get("before")), _needs(raw.get("after"))
        influence = measure_need_deltas(before, after_needs, host_action=raw["host_action_id"])
        if influence["worsened"]:
            findings.add("NEED_REGRESSION")
        if context.get("school_choice") == "join" and any(v < .35 for v in before.values()):
            findings.add("JOIN_WITH_CRITICAL_NEEDS")
        if "SAVE_AS" in actions and not all_green(NeedSnapshot(after_needs)):
            findings.add("PREMATURE_CONTINUATION_SAVE")
    else:
        findings.add("NEEDS_NOT_OBSERVED")
    if context.get("school_choice") == "join" and raw is None:
        findings.add("JOIN_NEEDS_UNKNOWN")
    host = None
    if influence is not None and not findings.intersection(("UNKNOWN_GAME_PATCH", "UNSAFE_SAVE_SELECTION", "BOOT_PATH_INVALID", "SCENE_TWO_CUES_MISSING", "VIEWPORT_EVIDENCE_MISSING", "VIEWPORT_UNKNOWN", "BLACK_VIEWPORT_STILL_ACTIVE")):
        viewport_state = {"state": "VIEWPORT_OK", "classification": "CONTENT_PRESENT"}
        host = evaluate_turn(after_needs, available_objects=tuple(case.get("available_objects", ())),
                             capture_ref=view["capture_ref"], viewport=viewport_state,
                             sim_absent=context.get("sim_absent") is True,
                             player_directed=context.get("player_directed") is True,
                             already_busy=context.get("already_busy") is True)
        if (context.get("sim_absent") or context.get("player_directed") or context.get("already_busy")) and host["next_gate"] in ("EXECUTE_INSTINCTS_PLAN", "LAB_SAVE_AS_BI_CONT_WHEN_AUTHORIZED"):
            findings.add("CONTROL_PRECEDENCE_BROKEN")
    blocked = sorted(findings - {"NEEDS_NOT_OBSERVED", "NEED_REGRESSION"})
    verdict = "BLOCKED" if blocked else "READY_FOR_NEEDS" if influence is None else "NEEDS_GREEN" if all_green(NeedSnapshot(after_needs)) else "NEEDS_RECOVERY"
    return {"schema": "betterinstincts.host-eval-result/v1", "case_id": case["case_id"],
            "verdict": verdict, "findings": sorted(findings), "blocked_by": blocked,
            "boot_duration_ms": stamps[-1] - stamps[0],
            "viewport": {"before": prior, "after": view.get("after")},
            "needs": influence,
            "whims": _surface(case.get("whims"), "WHIMS"),
            "skills": _surface(case.get("skills"), "SKILLS"),
            "host": {"next_gate": host["next_gate"], "next_action": host["instincts"]["next_action"]} if host else None,
            "next_upgrades": sorted(findings),
            "proof_ceiling": "OFFLINE_SUPPLIED_DATA_NOT_GAME_CERTIFICATION"}


def evaluate_suite(data: dict) -> dict:
    cases = data.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        raise HostEvalError("INVALID_SUITE_SIZE")
    ids = [c.get("case_id") for c in cases if isinstance(c, dict)]
    if len(ids) != len(cases) or len(set(ids)) != len(ids):
        raise HostEvalError("DUPLICATE_CASES")
    reports = [evaluate_case(case) for case in cases]
    mismatches = [{"case_id": r["case_id"], "expected": c["expect"], "actual": r["verdict"], "findings": r["findings"]}
                  for c, r in zip(cases, reports)
                  if r["verdict"] != c["expect"]["verdict"] or not set(c["expect"].get("findings", [])).issubset(r["findings"])]
    return {"schema": "betterinstincts.host-eval-suite-result/v1", "total": len(reports),
            "matched": len(reports) - len(mismatches), "mismatches": mismatches,
            "reports": reports, "proof_ceiling": "SYNTHETIC_OFFLINE_FIXTURES"}
