"""Classify queued Sim behavior as GOOD/BAD and EMULATE/OPTIMIZE via matrix.

Read-only. Never clicks the game. Terms come from contracts/glossary.v1.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from betterinstincts.glossary import GlossaryError, load_glossary

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "contracts" / "behavior-matrix.v1.json"
NEEDS = ROOT / "contracts" / "needs.v1.json"
MAX_BYTES = 64_000
SIX = frozenset({"hunger", "bladder", "energy", "hygiene", "fun", "social"})


class BehaviorEvalError(ValueError):
    pass


def load_matrix(path: Path = MATRIX) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BehaviorEvalError("BEHAVIOR_MATRIX_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.behavior-matrix/v1":
        raise BehaviorEvalError("BAD_BEHAVIOR_MATRIX_SCHEMA")
    if not isinstance(cfg.get("rows"), list) or not cfg["rows"]:
        raise BehaviorEvalError("BEHAVIOR_MATRIX_ROWS_REQUIRED")
    # Glossary must resolve — prevents reinvented synonyms.
    try:
        load_glossary()
    except GlossaryError as exc:
        raise BehaviorEvalError("GLOSSARY_REQUIRED:" + str(exc)) from exc
    return cfg


def _urgency_threshold() -> float:
    cfg = json.loads(NEEDS.read_text(encoding="utf-8"))
    return float(cfg["urgency_threshold"])


def _norm_queue(queue: Sequence[str]) -> list[str]:
    if len(queue) > 16:
        raise BehaviorEvalError("QUEUE_TOO_LONG")
    out = []
    for item in queue:
        if not isinstance(item, str) or not item or len(item) > 80:
            raise BehaviorEvalError("INVALID_QUEUE_ITEM")
        out.append(item.strip().lower().replace(" ", "_"))
    return out


def _flags(
    needs: Mapping[str, float],
    queue: Sequence[str],
    *,
    player_directed: bool,
    objects_on_current_lot: bool,
    matrix: dict,
) -> dict:
    if set(needs) != SIX:
        raise BehaviorEvalError("SIX_NEEDS_REQUIRED")
    thr = _urgency_threshold()
    q = _norm_queue(queue)
    fluff = {str(x).lower() for x in matrix.get("fluff_actions", [])}
    critical_acts = {str(x).lower() for x in matrix.get("critical_actions", [])}
    walk = {str(x).lower() for x in matrix.get("walk_thrash_signals", [])}
    any_critical = any(float(needs[n]) < thr for n in ("bladder", "hunger", "energy"))
    qset = set(q)
    return {
        "player_directed": bool(player_directed),
        "any_critical_need": any_critical,
        "queue_empty": len(q) == 0,
        "queue_intersects_fluff": bool(qset & fluff),
        "queue_intersects_critical_actions": bool(qset & critical_acts),
        "queue_misses_critical_actions": not bool(qset & critical_acts),
        "queue_intersects_walk_thrash": bool(qset & walk),
        "objects_on_current_lot": bool(objects_on_current_lot),
        "normalized_queue": q,
    }


def _match(when: Mapping[str, object], flags: Mapping[str, object]) -> bool:
    for key, expected in when.items():
        if key not in flags or flags[key] != expected:
            return False
    return True


def evaluate_queue(
    needs: Mapping[str, float],
    queue: Sequence[str],
    *,
    player_directed: bool = False,
    objects_on_current_lot: bool = True,
    location_kind: str = "unknown",
    capture_ref: str = "capture:unspecified",
) -> dict:
    matrix = load_matrix()
    flags = _flags(
        needs, queue,
        player_directed=player_directed,
        objects_on_current_lot=objects_on_current_lot,
        matrix=matrix,
    )
    matched = None
    for row in matrix["rows"]:
        if not isinstance(row, dict):
            raise BehaviorEvalError("INVALID_MATRIX_ROW")
        when = row.get("when")
        if isinstance(when, dict) and _match(when, flags):
            matched = row
            break
    if matched is None:
        # Fail closed to optimize if critical else emulate leisure.
        disposition = "OPTIMIZE" if flags["any_critical_need"] else "EMULATE_THEN_OPTIMIZE"
        verdict = "BAD_BEHAVIOR" if flags["any_critical_need"] else "GOOD_BEHAVIOR"
        matched = {
            "id": "FALLBACK_UNMATCHED",
            "verdict": verdict,
            "disposition": disposition,
            "optimize_allowed": True,
            "preferred_route": "MAP_TRAVEL" if not flags["objects_on_current_lot"] else "LOCAL_OBJECT",
            "forbidden_routes": ["IN_FRAME_WALK_THRASH"],
            "reason": "No matrix row matched; fail closed with glossary dispositions.",
        }
    clarity = {
        "verdict": matched["verdict"],
        "disposition": matched["disposition"],
        "matched_row_id": matched["id"],
        "optimize_allowed": bool(matched.get("optimize_allowed")),
        "preferred_route": matched.get("preferred_route"),
        "forbidden_routes": list(matched.get("forbidden_routes") or ["IN_FRAME_WALK_THRASH"]),
        "reason": matched.get("reason"),
        "optimize_scope": matched.get("optimize_scope"),
    }
    for key in matrix.get("evaluator_clarity_required", []):
        if key not in clarity or clarity[key] is None and key in {
            "verdict", "disposition", "matched_row_id", "optimize_allowed", "reason"
        }:
            raise BehaviorEvalError("EVALUATOR_CLARITY_MISSING:" + key)
    return {
        "state": "BEHAVIOR_EVALUATED",
        "location_kind": location_kind,
        "capture_ref": capture_ref,
        "flags": flags,
        "clarity": clarity,
        "glossary_refs": ["EMULATE", "OPTIMIZE", "EMULATE_THEN_OPTIMIZE", "GOOD_BEHAVIOR", "BAD_BEHAVIOR"],
        "proof_ceiling": matrix.get("proof_ceiling"),
    }
