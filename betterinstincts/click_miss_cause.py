"""Classify click misses with durable causes + ML-ready feature vectors.

Evaluate/record only — never SendInput. RULE_V1 precedes any trained model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "click-miss-cause.v1.json"
MAX_BYTES = 256_000


class ClickMissCauseError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ClickMissCauseError("CLICK_MISS_CAUSE_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.click-miss-cause/v1":
        raise ClickMissCauseError("BAD_CLICK_MISS_CAUSE_SCHEMA")
    if cfg.get("execute_allowed_default") is not False:
        raise ClickMissCauseError("CLICK_MISS_CAUSE_MUST_DEFAULT_EXECUTE_FALSE")
    return cfg


def default_corpus_path(cfg: Optional[dict] = None) -> Path:
    cfg = cfg or load_contract()
    rel = str(cfg.get("corpus_path_default") or "dist/game-host/click-miss-cause-corpus.json")
    path = Path(rel)
    return path if path.is_absolute() else ROOT / path


def empty_corpus() -> dict:
    return {
        "schema": "betterinstincts.click-miss-cause-corpus/v1",
        "classifier_id": "RULE_V1",
        "rows": [],
        "note": "Append-only labeled click outcomes. Private captures stay under dist/.",
    }


def load_corpus(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else default_corpus_path()
    if not path.is_file():
        return empty_corpus()
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise ClickMissCauseError("CLICK_MISS_CAUSE_CORPUS_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.click-miss-cause-corpus/v1":
        raise ClickMissCauseError("BAD_CLICK_MISS_CAUSE_CORPUS_SCHEMA")
    if not isinstance(data.get("rows"), list):
        data["rows"] = []
    return data


def save_corpus(corpus: Mapping[str, object], path: Path | None = None) -> Path:
    path = Path(path) if path is not None else default_corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(corpus), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _bin(flag: object) -> float:
    return 1.0 if bool(flag) else 0.0


def _num(value: object, missing: float) -> float:
    if value is None:
        return missing
    try:
        return float(value)
    except (TypeError, ValueError):
        return missing


def feature_vector(
    *,
    geometry: str,
    error_px: float = 0.0,
    dx: float = 0.0,
    dy: float = 0.0,
    peer_hud_busy: bool = False,
    overlay_clear_during_peer_lease: bool = False,
    intended_surface_absent: bool = False,
    wrong_control: bool = False,
    zoom_fraction: float | None = None,
    object_pick_identify_used: bool = False,
    lot_punch_through_risk: bool = False,
    idle_ms_at_click: float | None = None,
    seconds_since_peer_lease: float | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Build ordered feature dict pinned by contract feature_schema."""
    cfg = cfg or load_contract()
    schema = cfg.get("feature_schema") or {}
    order = list(schema.get("order") or [])
    missing = float((schema.get("missing_numeric") if schema.get("missing_numeric") is not None else -1.0))
    geom = str(geometry or "").upper()
    values = {
        "error_px": float(error_px),
        "dx": float(dx),
        "dy": float(dy),
        "geom_HIT": _bin(geom == "HIT"),
        "geom_NEAR_MISS": _bin(geom == "NEAR_MISS"),
        "geom_MISS": _bin(geom == "MISS"),
        "geom_WRONG_CONTROL": _bin(geom == "WRONG_CONTROL" or wrong_control),
        "peer_hud_busy": _bin(peer_hud_busy),
        "overlay_clear_during_peer_lease": _bin(overlay_clear_during_peer_lease),
        "intended_surface_absent": _bin(intended_surface_absent),
        "wrong_control_flag": _bin(wrong_control or geom == "WRONG_CONTROL"),
        "zoom_fraction": _num(zoom_fraction, missing),
        "object_pick_identify_used": _bin(object_pick_identify_used),
        "lot_punch_through_risk": _bin(lot_punch_through_risk),
        "idle_ms_at_click": _num(idle_ms_at_click, missing),
        "seconds_since_peer_lease": _num(seconds_since_peer_lease, missing),
    }
    if not order:
        raise ClickMissCauseError("FEATURE_ORDER_REQUIRED")
    vector = [float(values[name]) for name in order]
    return {"names": order, "values": vector, "by_name": {n: values[n] for n in order}}


def classify_miss_cause(
    *,
    geometry: str,
    peer_hud_busy: bool = False,
    overlay_clear_during_peer_lease: bool = False,
    intended_surface_absent: bool = False,
    wrong_control: bool = False,
    zoom_fraction: float | None = None,
    object_pick_identify_used: bool = False,
    lot_punch_through_risk: bool = False,
    error_px: float = 0.0,
    dx: float = 0.0,
    dy: float = 0.0,
    idle_ms_at_click: float | None = None,
    seconds_since_peer_lease: float | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """RULE_V1: priority cause labels; HIT → NONE."""
    cfg = cfg or load_contract()
    allowed = set(cfg.get("miss_causes") or [])
    geom = str(geometry or "").upper()
    feats = feature_vector(
        geometry=geom,
        error_px=error_px,
        dx=dx,
        dy=dy,
        peer_hud_busy=peer_hud_busy,
        overlay_clear_during_peer_lease=overlay_clear_during_peer_lease,
        intended_surface_absent=intended_surface_absent,
        wrong_control=wrong_control,
        zoom_fraction=zoom_fraction,
        object_pick_identify_used=object_pick_identify_used,
        lot_punch_through_risk=lot_punch_through_risk,
        idle_ms_at_click=idle_ms_at_click,
        seconds_since_peer_lease=seconds_since_peer_lease,
        cfg=cfg,
    )
    if geom == "HIT":
        cause = "NONE"
        confidence = 1.0
        rationale = "Geometry HIT — no miss cause"
    elif peer_hud_busy:
        cause = "PEER_HUD_COLLISION"
        confidence = 0.95
        rationale = "Peer LIVE_HUD_SURFACE_LEASE busy during click"
    elif overlay_clear_during_peer_lease:
        cause = "OVERLAY_CLEAR_WIPE"
        confidence = 0.95
        rationale = "Overlay clear while peer HUD leased"
    elif intended_surface_absent:
        cause = "STALE_SURFACE"
        confidence = 0.9
        rationale = "Intended surface already closed/absent"
    elif wrong_control or geom == "WRONG_CONTROL":
        cause = "WRONG_CONTROL"
        confidence = 0.9
        rationale = "Different fixed control opened"
    elif (not object_pick_identify_used) and zoom_fraction is not None and float(zoom_fraction) < 0.7:
        cause = "ZOOM_INSUFFICIENT"
        confidence = 0.75
        rationale = "World/object click without OBJECT_PICK_IDENTIFY zoom-in"
    elif lot_punch_through_risk:
        cause = "LOT_PUNCH_THROUGH"
        confidence = 0.85
        rationale = "Above-target / lot punch-through risk"
    elif geom in {"NEAR_MISS", "MISS"}:
        cause = "HITBOX_DRIFT"
        confidence = 0.7
        rationale = "Geometry miss without interop/stale/wrong-control flags"
    else:
        cause = "UNKNOWN"
        confidence = 0.4
        rationale = "Insufficient signals"
    if cause not in allowed:
        raise ClickMissCauseError("UNKNOWN_MISS_CAUSE:" + cause)
    practice = (cfg.get("recommended_practice") or {}).get(cause, "")
    return {
        "schema": "betterinstincts.click-miss-cause-result/v1",
        "classifier_id": str((cfg.get("classifier") or {}).get("id") or "RULE_V1"),
        "geometry": geom,
        "miss_cause": cause,
        "confidence": confidence,
        "rationale": rationale,
        "recommended_practice": practice,
        "features": feats,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def record_miss_row(
    corpus: dict,
    *,
    target_id: str,
    client_xy: Sequence[int],
    geometry: str,
    miss_cause: str | None = None,
    classify_kwargs: Optional[Mapping[str, object]] = None,
    note: str = "",
    capture: str = "",
    session_id: str = "",
    label_source: str = "RULE_V1",
    cfg: Optional[dict] = None,
) -> dict:
    """Append one corpus row; auto-classify when miss_cause omitted."""
    cfg = cfg or load_contract()
    tid = str(target_id or "").strip()
    if not tid:
        raise ClickMissCauseError("TARGET_ID_REQUIRED")
    if (
        not isinstance(client_xy, (list, tuple))
        or len(client_xy) != 2
        or any(type(v) is not int for v in client_xy)
    ):
        raise ClickMissCauseError("CLIENT_XY_MUST_BE_TWO_INTS")
    kwargs = dict(classify_kwargs or {})
    kwargs.setdefault("geometry", geometry)
    result = classify_miss_cause(cfg=cfg, **kwargs)  # type: ignore[arg-type]
    cause = str(miss_cause or result["miss_cause"])
    if cause not in set(cfg.get("miss_causes") or []):
        raise ClickMissCauseError("UNKNOWN_MISS_CAUSE:" + cause)
    if cause != result["miss_cause"] and label_source == "RULE_V1":
        # Operator override must declare a non-rule label source.
        raise ClickMissCauseError("CAUSE_OVERRIDE_REQUIRES_LABEL_SOURCE")
    row = {
        "target_id": tid,
        "client_xy": [int(client_xy[0]), int(client_xy[1])],
        "geometry": str(geometry).upper(),
        "miss_cause": cause,
        "confidence": result["confidence"] if cause == result["miss_cause"] else 1.0,
        "features": result["features"],
        "recommended_practice": (cfg.get("recommended_practice") or {}).get(cause, ""),
        "note": str(note or ""),
        "capture": str(capture or ""),
        "session_id": str(session_id or ""),
        "label_source": str(label_source or "RULE_V1"),
        "classifier_id": result["classifier_id"],
    }
    book = dict(corpus) if isinstance(corpus, Mapping) else empty_corpus()
    rows = list(book.get("rows") or [])
    rows.append(row)
    book["rows"] = rows
    book["schema"] = "betterinstincts.click-miss-cause-corpus/v1"
    book["classifier_id"] = result["classifier_id"]
    corpus.clear()
    corpus.update(book)
    return row


def summarize_corpus(corpus: Mapping[str, object], *, cfg: Optional[dict] = None) -> dict:
    """Count causes and emit practice hints ranked by frequency."""
    cfg = cfg or load_contract()
    counts = {c: 0 for c in (cfg.get("miss_causes") or []) if c != "NONE"}
    counts["NONE"] = 0
    for row in corpus.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        cause = str(row.get("miss_cause") or "UNKNOWN")
        counts[cause] = int(counts.get(cause) or 0) + 1
    ranked = sorted(
        ((k, v) for k, v in counts.items() if k != "NONE" and v > 0),
        key=lambda kv: (-kv[1], kv[0]),
    )
    practices = [
        {
            "miss_cause": cause,
            "count": n,
            "practice": (cfg.get("recommended_practice") or {}).get(cause, ""),
        }
        for cause, n in ranked
    ]
    return {
        "schema": "betterinstincts.click-miss-cause-summary/v1",
        "total_rows": len(list(corpus.get("rows") or [])),
        "counts": counts,
        "ranked_practices": practices,
        "proof_ceiling": cfg["proof_ceiling"],
        "execute_allowed": False,
    }


def ingest_parts_buy_ledger(
    ledger: Mapping[str, object],
    *,
    corpus: dict | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Map known parts-buy click-ledger notes into labeled corpus rows."""
    cfg = cfg or load_contract()
    book = corpus if isinstance(corpus, dict) else empty_corpus()
    session_id = str(ledger.get("session_id") or "")
    op = "OPERATOR_PARTS_BUY_20261110"
    for step in ledger.get("steps") or []:
        if not isinstance(step, Mapping):
            continue
        note = str(step.get("note") or "")
        classification = str(step.get("classification") or "")
        target = str(step.get("target_id") or "")
        xy = step.get("client_xy")
        if classification == "MISS_STALE_PHONE" or "MISS_PHONE_ALREADY_CLOSED" in note:
            record_miss_row(
                book,
                target_id=target or "phone.shopping_bag",
                client_xy=list(xy) if isinstance(xy, list) and len(xy) == 2 else [216, 857],
                geometry="MISS",
                miss_cause="OVERLAY_CLEAR_WIPE",
                classify_kwargs={
                    "geometry": "MISS",
                    "intended_surface_absent": True,
                    "overlay_clear_during_peer_lease": True,
                    "error_px": 80.0,
                },
                note=note or classification,
                capture=str(step.get("capture") or ""),
                session_id=session_id,
                label_source=op,
                cfg=cfg,
            )
            continue
        if classification == "MISS" and "FLOOR_PIE" in note.upper():
            record_miss_row(
                book,
                target_id=target or "live.desk_computer",
                client_xy=list(xy) if isinstance(xy, list) and len(xy) == 2 else [980, 520],
                geometry="MISS",
                classify_kwargs={
                    "geometry": "MISS",
                    "object_pick_identify_used": False,
                    "zoom_fraction": 0.2,
                    "error_px": 120.0,
                    "dy": 40.0,
                },
                note=note,
                capture=str(step.get("capture") or ""),
                session_id=session_id,
                cfg=cfg,
            )
            continue
    targets = ledger.get("targets") if isinstance(ledger.get("targets"), Mapping) else {}
    bag = targets.get("phone.shopping_bag") if isinstance(targets, Mapping) else None
    if isinstance(bag, Mapping) and "WRONG_CONTROL" in str(bag.get("status") or ""):
        xy = bag.get("client_xy") or [216, 857]
        record_miss_row(
            book,
            target_id="phone.shopping_bag",
            client_xy=[int(xy[0]), int(xy[1])],
            geometry="WRONG_CONTROL",
            classify_kwargs={
                "geometry": "WRONG_CONTROL",
                "wrong_control": True,
                "error_px": 0.0,
            },
            note=str(bag.get("note") or "shopping bag opens gifts/Plopsy"),
            session_id=session_id,
            cfg=cfg,
        )
    prior = targets.get("live.desk_computer") if isinstance(targets, Mapping) else None
    if isinstance(prior, Mapping) and isinstance(prior.get("prior_miss"), Mapping):
        pm = prior["prior_miss"]
        pxy = pm.get("client_xy") or [980, 520]
        record_miss_row(
            book,
            target_id="live.desk_computer",
            client_xy=[int(pxy[0]), int(pxy[1])],
            geometry="MISS",
            miss_cause="PEER_HUD_COLLISION",
            classify_kwargs={
                "geometry": "MISS",
                "object_pick_identify_used": False,
                "zoom_fraction": 0.2,
                "error_px": 140.0,
                "peer_hud_busy": True,
            },
            note=str(pm.get("classification") or "prior computer miss"),
            session_id=session_id,
            label_source=op,
            cfg=cfg,
        )
    return book
