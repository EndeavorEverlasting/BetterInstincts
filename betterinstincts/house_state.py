"""Recursive lot environment model + mutation admission (P95).

Accumulates house/lot understanding across observations and actions.
Checkpoints persist the current model revision — they do not wipe it
or force a blank-slate reassessment. No SendInput, no save-folder access.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "house-state.v1.json"
MAX_CONTRACT_BYTES = 64_000
MODEL_SCHEMA = "betterinstincts.lot-environment-model/v1"
CHECKPOINT_SCHEMA = "betterinstincts.house-state-checkpoint/v1"
LEASE_SCHEMA = "betterinstincts.house-state-lease/v1"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
LOT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{1,79}$")
ENTITY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,79}$")
CAPTURE_RE = re.compile(r"^capture:[A-Za-z0-9_./:-]{3,160}$")


class HouseStateError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONTRACT_BYTES:
        raise HouseStateError("HOUSE_STATE_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.house-state/v1":
        raise HouseStateError("INVALID_HOUSE_STATE_SCHEMA")
    if data.get("architecture", {}).get("selected") != "RECURSIVE_LOT_MODEL":
        raise HouseStateError("RECURSIVE_LOT_MODEL_REQUIRED")
    forbidden = set(data.get("forbidden", []))
    if not {
        "BLANK_SLATE_REASSESS",
        "DISCARD_MODEL_AFTER_ACTION",
        "MUTATE_WITHOUT_MODEL_REVISION",
        "BULK_SWEEP_WITHOUT_ENTITY_TARGETS",
        "TREAT_OUTDOOR_AS_INDOOR",
        "MUTATE_WITHOUT_BUILD_INTEGRITY",
    }.issubset(forbidden):
        raise HouseStateError("ANTI_BLANK_SLATE_GUARDS_MISSING")
    if not data.get("mutating_actions"):
        raise HouseStateError("MUTATING_ACTIONS_MISSING")
    return data


def _storage_root(contract: Mapping[str, Any] | None = None) -> Path:
    cfg = contract if contract is not None else load_contract()
    rel = str(cfg.get("storage", {}).get("root", "dist/house-state/")).strip().strip("/\\")
    root = (ROOT / rel).resolve()
    if not str(root).startswith(str((ROOT / "dist").resolve())):
        raise HouseStateError("HOUSE_STATE_ROOT_OUTSIDE_DIST")
    return root


def model_path(run_id: str, lot_id: str, *, contract: Mapping[str, Any] | None = None) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise HouseStateError("INVALID_RUN_ID")
    if not LOT_ID_RE.fullmatch(lot_id):
        raise HouseStateError("INVALID_LOT_ID")
    safe_lot = re.sub(r"[^A-Za-z0-9_.-]+", "_", lot_id.strip())[:80]
    return _storage_root(contract) / run_id / f"{safe_lot}.model.json"


def create_model(run_id: str, lot_id: str, *, seed_captures: Sequence[str] | None = None) -> dict:
    """Start a durable lot model. Revision 0 until first observe."""
    if not RUN_ID_RE.fullmatch(run_id):
        raise HouseStateError("INVALID_RUN_ID")
    if not LOT_ID_RE.fullmatch(lot_id):
        raise HouseStateError("INVALID_LOT_ID")
    captures = list(seed_captures or [])
    for cap in captures:
        if not isinstance(cap, str) or not CAPTURE_RE.fullmatch(cap):
            raise HouseStateError("INVALID_CAPTURE_REF")
    return {
        "schema": MODEL_SCHEMA,
        "run_id": run_id,
        "lot_id": lot_id,
        "revision": 0,
        "entities": {},
        "relations": [],
        "open_goals": [],
        "last_action": None,
        "captures": captures,
        "save_as_attestation": None,
        "unknowns": [],
        "history": [],
    }


def load_model(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise HouseStateError("LOT_MODEL_MISSING")
    max_bytes = int(load_contract()["storage"]["max_model_bytes"])
    if path.stat().st_size > max_bytes:
        raise HouseStateError("LOT_MODEL_TOO_LARGE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HouseStateError("INVALID_LOT_MODEL_JSON") from exc
    if not isinstance(data, dict) or data.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    if not isinstance(data.get("entities"), dict) or not isinstance(data.get("revision"), int):
        raise HouseStateError("INVALID_LOT_MODEL_BODY")
    if data["revision"] < 0:
        raise HouseStateError("INVALID_LOT_MODEL_REVISION")
    return data


def save_model(model: Mapping[str, Any], path: Path | None = None) -> Path:
    if model.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    dest = Path(path) if path is not None else model_path(str(model["run_id"]), str(model["lot_id"]))
    if not str(dest.resolve()).startswith(str(_storage_root().resolve())):
        raise HouseStateError("LOT_MODEL_PATH_OUTSIDE_ROOT")
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(model), indent=2, sort_keys=True) + "\n"
    if len(text.encode("utf-8")) > int(load_contract()["storage"]["max_model_bytes"]):
        raise HouseStateError("LOT_MODEL_TOO_LARGE")
    dest.write_text(text, encoding="utf-8")
    return dest


def load_or_create(run_id: str, lot_id: str, *, seed_captures: Sequence[str] | None = None) -> dict:
    path = model_path(run_id, lot_id)
    if path.is_file():
        return load_model(path)
    model = create_model(run_id, lot_id, seed_captures=seed_captures)
    save_model(model, path)
    return model


def _validate_entity(entity_id: str, claim: Mapping[str, Any], kinds: set[str]) -> dict:
    if not ENTITY_ID_RE.fullmatch(entity_id):
        raise HouseStateError("INVALID_ENTITY_ID")
    kind = claim.get("kind")
    if kind not in kinds:
        raise HouseStateError("INVALID_ENTITY_KIND")
    conf = claim.get("confidence", "OPERATOR_ATTESTED")
    if conf not in {"OPERATOR_ATTESTED", "LOCAL_OBSERVED", "HYPOTHESIS", "UNKNOWN"}:
        raise HouseStateError("INVALID_ENTITY_CONFIDENCE")
    if conf == "UNKNOWN":
        raise HouseStateError("ENTITY_CONFIDENCE_UNKNOWN_FORBIDDEN")
    out = {
        "id": entity_id,
        "kind": kind,
        "confidence": conf,
        "label": str(claim.get("label") or kind)[:120],
        "slot": claim.get("slot"),
        "status": str(claim.get("status") or "PRESENT")[:40],
        "evidence": [],
    }
    # Spatial integrity fields (build_integrity / build_spatial).
    domain = claim.get("domain") or claim.get("spatial_domain")
    if domain is not None:
        out["domain"] = str(domain).upper()[:40]
    zone = claim.get("zone")
    if zone is not None:
        out["zone"] = str(zone).upper()[:40]
    enclosure = claim.get("enclosure")
    if enclosure is not None:
        out["enclosure"] = str(enclosure).upper()[:40]
    story = claim.get("story") or claim.get("floor_level") or claim.get("level")
    if story is not None:
        out["story"] = str(story).upper()[:40]
        out["floor_level"] = out["story"]
    for key in ("notes", "pose", "region"):
        if key in claim and claim[key] is not None:
            out[key] = claim[key]
    evidence = claim.get("evidence") or []
    if isinstance(evidence, list):
        for item in evidence[:12]:
            if isinstance(item, str) and CAPTURE_RE.fullmatch(item):
                out["evidence"].append(item)
    return out


def observe(
    model: Mapping[str, Any],
    *,
    entities: Mapping[str, Mapping[str, Any]] | None = None,
    relations: Sequence[Mapping[str, Any]] | None = None,
    open_goals: Sequence[str] | None = None,
    captures: Sequence[str] | None = None,
    unknowns: Sequence[str] | None = None,
    note: str | None = None,
    replace_goals: bool = False,
) -> dict:
    """Merge observations into the same model (recursive). Never wipes entities."""
    cfg = load_contract()
    kinds = set(cfg["model"]["entity_kinds"])
    if model.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    out = json.loads(json.dumps(dict(model)))  # deep copy via JSON
    entity_map: dict[str, Any] = dict(out.get("entities") or {})
    for entity_id, claim in (entities or {}).items():
        if not isinstance(claim, Mapping):
            raise HouseStateError("INVALID_ENTITY_CLAIM")
        merged = _validate_entity(entity_id, claim, kinds)
        prior = entity_map.get(entity_id)
        if isinstance(prior, dict):
            evid = list(dict.fromkeys(list(prior.get("evidence") or []) + list(merged["evidence"])))
            merged["evidence"] = evid[:24]
            if prior.get("slot") and not merged.get("slot"):
                merged["slot"] = prior["slot"]
            if prior.get("domain") and not merged.get("domain"):
                merged["domain"] = prior["domain"]
            if prior.get("zone") and not merged.get("zone"):
                merged["zone"] = prior["zone"]
            if prior.get("enclosure") and not merged.get("enclosure"):
                merged["enclosure"] = prior["enclosure"]
            if prior.get("story") and not merged.get("story"):
                merged["story"] = prior["story"]
                merged["floor_level"] = prior.get("floor_level") or prior["story"]
        entity_map[entity_id] = merged
    out["entities"] = entity_map
    if relations:
        rels = list(out.get("relations") or [])
        for rel in relations:
            if not isinstance(rel, Mapping):
                raise HouseStateError("INVALID_RELATION")
            rels.append({
                "type": str(rel.get("type") or "RELATED")[:40],
                "a": str(rel.get("a") or "")[:80],
                "b": str(rel.get("b") or "")[:80],
            })
        out["relations"] = rels[-200:]
    if open_goals is not None:
        goals = [str(g)[:120] for g in open_goals if str(g).strip()]
        out["open_goals"] = goals if replace_goals else list(dict.fromkeys(list(out.get("open_goals") or []) + goals))[:40]
    if captures:
        caps = list(out.get("captures") or [])
        for cap in captures:
            if not isinstance(cap, str) or not CAPTURE_RE.fullmatch(cap):
                raise HouseStateError("INVALID_CAPTURE_REF")
            if cap not in caps:
                caps.append(cap)
        out["captures"] = caps[-40:]
    if unknowns:
        unk = list(out.get("unknowns") or [])
        for item in unknowns:
            text = str(item).strip()[:160]
            if text and text not in unk:
                unk.append(text)
        out["unknowns"] = unk[-40:]
    out["revision"] = int(out.get("revision") or 0) + 1
    hist = list(out.get("history") or [])
    hist.append({
        "op": "OBSERVE",
        "revision": out["revision"],
        "note": (note or "merge")[:160],
        "entity_count": len(entity_map),
    })
    out["history"] = hist[-100:]
    return out


def attest_save_as(
    model: Mapping[str, Any],
    *,
    alias: str,
    capture_ref: str,
    operator_confirmed: bool,
) -> dict:
    """Record operator Save As attestation on the model (no filesystem save access)."""
    if not operator_confirmed:
        raise HouseStateError("SAVE_AS_REQUIRES_OPERATOR_CONFIRMATION")
    if not isinstance(alias, str) or not re.fullmatch(r"^BI_(TMP|CONT)_[A-Z0-9_]{4,48}$", alias):
        raise HouseStateError("SAVE_AS_ALIAS_MUST_BE_LAB")
    if not isinstance(capture_ref, str) or not CAPTURE_RE.fullmatch(capture_ref):
        raise HouseStateError("INVALID_CAPTURE_REF")
    out = observe(model, note="save_as_attestation")
    out["save_as_attestation"] = {
        "alias": alias,
        "capture_ref": capture_ref,
        "operator_confirmed": True,
        "model_revision": out["revision"],
    }
    return out


def plan_next(model: Mapping[str, Any]) -> dict:
    """Pick one next action from accumulated model — never from a blank slate."""
    load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    revision = int(model.get("revision") or 0)
    entities = model.get("entities") or {}
    goals = list(model.get("open_goals") or [])
    if revision <= 0 or not entities:
        return {
            "state": "MODEL_EMPTY",
            "gate": "ACCUMULATE_LOT_MODEL",
            "action": None,
            "reason": "NEED_FIRST_OBSERVE_MERGE",
            "forbidden": ["BLANK_SLATE_REASSESS", "MUTATE_WITHOUT_MODEL_REVISION"],
            "model_revision": revision,
        }
    # Enclosure + story axes first (inside/outside, F1/F2), then integrity restore.
    from betterinstincts.build_spatial import build_order_plan
    from betterinstincts.build_integrity import structure_restore_plan

    spatial = build_order_plan(model)
    if spatial.get("steps"):
        primary = spatial.get("primary") or {}
        return {
            "state": "MODEL_ACTIVE",
            "gate": spatial.get("gate") or "BUILD_ORDER_FLOOR1_BEFORE_FLOOR2",
            "action": primary.get("action"),
            "reason": "SPATIAL_BUILD_ORDER_" + str(primary.get("step") or "NEXT"),
            "model_revision": revision,
            "targets": list(primary.get("targets") or []),
            "open_goals": goals,
            "enclosure": primary.get("enclosure"),
            "story": primary.get("story"),
            "build_spatial": spatial,
            "forbidden": [
                "TREAT_OUTSIDE_AS_INSIDE",
                "BUILD_F2_BEFORE_F1",
                "PLACE_INDOOR_ON_GRASS",
                "STRIP_KITCHEN_AESTHETIC",
            ],
        }
    restore = structure_restore_plan(model)
    if restore.get("state") == "STRUCTURE_RESTORE_REQUIRED":
        primary = restore.get("primary") or {}
        return {
            "state": "MODEL_ACTIVE",
            "gate": restore.get("gate") or "RESTORE_FLOOR_BEFORE_FURNITURE",
            "action": primary.get("action"),
            "reason": "STRUCTURE_FIRST_" + str(primary.get("step") or "RESTORE"),
            "model_revision": revision,
            "targets": [],
            "open_goals": goals,
            "structure_restore": restore,
            "forbidden": ["TREAT_OUTDOOR_AS_INDOOR", "PLACE_INDOOR_ON_GRASS", "STRIP_KITCHEN_AESTHETIC"],
        }
    floaters = [e for e in entities.values() if isinstance(e, dict) and e.get("kind") == "FLOATER"]
    chairs = [e for e in entities.values() if isinstance(e, dict) and e.get("kind") == "DINING_CHAIR"]
    tables = [e for e in entities.values() if isinstance(e, dict) and e.get("kind") == "DINING_TABLE"]
    empty_slots = [
        e for e in chairs
        if str(e.get("status") or "").upper() in {"MISSING", "EMPTY_SLOT", "ABSENT"}
    ]
    if any(g.upper() == "LOAD_LAST_KNOWN_GOOD_SAVE" for g in goals):
        advice = recovery_advice(has_known_good_save=True)
        return {
            "state": "RECOVERY_ADVICE",
            "gate": "LOAD_LAST_KNOWN_GOOD_SAVE",
            "action": "LOAD_LAST_KNOWN_GOOD_SAVE",
            "reason": "OPERATOR_MARKED_LOAD_GOAL",
            "recovery": advice,
            "model_revision": revision,
            "targets": [],
        }
    if empty_slots and tables:
        return {
            "state": "MODEL_ACTIVE",
            "gate": "PLAN_FROM_MODEL",
            "action": "PLACE_FROM_CATALOG",
            "reason": "MISSING_DINING_CHAIR_SLOT",
            "model_revision": revision,
            "targets": [empty_slots[0]["id"], tables[0]["id"]],
            "open_goals": goals,
            "place_domain": "INDOOR_FLOOR",
        }
    if floaters:
        # Targeted inventory of known floaters — never blind bulk sweep.
        # Only outdoor/unknown floaters; never structure kinds.
        safe = [
            f for f in floaters
            if str(f.get("domain") or "OUTDOOR_LOT").upper() in {"OUTDOOR_LOT", "UNKNOWN_DOMAIN"}
        ]
        if safe:
            return {
                "state": "MODEL_ACTIVE",
                "gate": "PLAN_FROM_MODEL",
                "action": "BACKSPACE_TO_INVENTORY",
                "reason": "TARGETED_FLOATER_CLEAR",
                "model_revision": revision,
                "targets": [f["id"] for f in safe[:8]],
                "open_goals": goals,
                "forbidden": ["BULK_SWEEP_WITHOUT_ENTITY_TARGETS", "TREAT_OUTDOOR_AS_INDOOR"],
            }
    if goals:
        return {
            "state": "MODEL_ACTIVE",
            "gate": "PLAN_FROM_MODEL",
            "action": "OBSERVE_ONLY",
            "reason": "GOALS_REMAIN_BUT_NO_MATCHED_ENTITY_ACTION",
            "model_revision": revision,
            "targets": [],
            "open_goals": goals,
        }
    return {
        "state": "MODEL_ACTIVE",
        "gate": "PLAN_FROM_MODEL",
        "action": None,
        "reason": "NO_OPEN_MUTATION",
        "model_revision": revision,
        "targets": [],
    }


def admit_mutation(
    model: Mapping[str, Any],
    action: str,
    *,
    targets: Sequence[str] | None = None,
    expected_revision: int | None = None,
    place_kind: str | None = None,
    place_domain: str | None = None,
    place_enclosure: str | None = None,
    place_story: str | None = None,
    nest_risk: bool = False,
    strips_zone: str | None = None,
) -> dict:
    """Admit one mutation only against the current accumulated model revision.

    Always runs build_integrity before issuing a lease (structure-first spatial gate).
    """
    cfg = load_contract()
    mutating = set(cfg["mutating_actions"])
    non_mut = set(cfg["non_mutating_allowed_without_lease"])
    destructive = set(cfg["destructive_actions_require_save_as"])
    if model.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    revision = int(model.get("revision") or 0)
    entities = model.get("entities") or {}
    if action in non_mut:
        return {
            "state": "MUTATION_ADMITTED",
            "gate": "HOUSE_STATE_MUTATION_LEASE",
            "lease": None,
            "action": action,
            "reason": "NON_MUTATING",
            "model_revision": revision,
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if action not in mutating:
        return {
            "state": "MUTATION_DENIED",
            "gate": "HOUSE_STATE_MUTATION_LEASE",
            "reason": "UNKNOWN_OR_FORBIDDEN_ACTION",
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
        }
    if revision <= 0 or not entities:
        return {
            "state": "MUTATION_DENIED",
            "gate": "ACCUMULATE_LOT_MODEL",
            "reason": "MUTATE_WITHOUT_MODEL_REVISION",
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
            "forbidden": ["BLANK_SLATE_REASSESS", "MUTATE_WITHOUT_MODEL_REVISION"],
        }
    if expected_revision is not None and int(expected_revision) != revision:
        return {
            "state": "MUTATION_DENIED",
            "gate": "HOUSE_STATE_MUTATION_LEASE",
            "reason": "STALE_MODEL_REVISION",
            "action": action,
            "model_revision": revision,
            "expected_revision": int(expected_revision),
            "execute_allowed": False,
        }
    target_list = [str(t) for t in (targets or []) if str(t).strip()]
    if action in {"BACKSPACE_TO_INVENTORY", "HAND_MOVE", "SLEDGE", "EYEDROPPER_PLACE"} and not target_list:
        return {
            "state": "MUTATION_DENIED",
            "gate": "PLAN_FROM_MODEL",
            "reason": "TARGETS_REQUIRED",
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
        }
    if action == "BULK_INVENTORY_SWEEP":
        return {
            "state": "MUTATION_DENIED",
            "gate": "PLAN_FROM_MODEL",
            "reason": "BULK_SWEEP_WITHOUT_ENTITY_TARGETS",
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
            "hint": "Use BACKSPACE_TO_INVENTORY with explicit floater entity ids from the model",
        }
    for tid in target_list:
        if tid not in entities:
            return {
                "state": "MUTATION_DENIED",
                "gate": "PLAN_FROM_MODEL",
                "reason": "TARGET_NOT_IN_MODEL",
                "action": action,
                "missing_target": tid,
                "model_revision": revision,
                "execute_allowed": False,
            }
    if action in destructive and not (model.get("save_as_attestation") or {}).get("operator_confirmed"):
        return {
            "state": "MUTATION_DENIED",
            "gate": "PERSIST_MODEL_CHECKPOINT",
            "reason": "DESTRUCTIVE_REQUIRES_SAVE_AS_ATTESTATION",
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
        }

    from betterinstincts.build_integrity import evaluate_integrity
    from betterinstincts.build_spatial import admit_spatial_placement

    indoor_actions = {
        "PLACE_FROM_CATALOG",
        "PLACE_FROM_INVENTORY",
        "EYEDROPPER_PLACE",
        "HAND_MOVE",
    }
    spatial = None
    if action in indoor_actions:
        kind = place_kind
        if kind is None and target_list and target_list[0] in entities:
            kind = str((entities.get(target_list[0]) or {}).get("kind") or "")
        indoor_required = kind in {
            "DINING_TABLE", "DINING_CHAIR", "BED", "SLEEP_POD", "APPLIANCE",
            "COUNTER", "CABINET", "SOFA", "DESK", "FLOOR_TILE", "WALL_SEGMENT",
        } or place_enclosure == "INSIDE" or (
            place_domain or ""
        ).upper() in {"INDOOR_FLOOR", "WALL"}
        if indoor_required or place_enclosure or place_story:
            spatial = admit_spatial_placement(
                model,
                place_enclosure=place_enclosure or (
                    "INSIDE" if (place_domain or "").upper() in {"INDOOR_FLOOR", "WALL"} else place_domain
                ),
                place_story=place_story or "FLOOR_1",
                place_domain=place_domain,
                indoor_required=bool(indoor_required),
            )
            if spatial.get("state") == "SPATIAL_DENY":
                return {
                    "state": "MUTATION_DENIED",
                    "gate": spatial.get("gate") or "CLASSIFY_ENCLOSURE_AND_STORY",
                    "reason": "MUTATE_WITHOUT_SPATIAL_AXES",
                    "violation": spatial.get("violation"),
                    "spatial": spatial,
                    "action": action,
                    "model_revision": revision,
                    "execute_allowed": False,
                    "forbidden": [
                        "TREAT_OUTSIDE_AS_INSIDE",
                        "BUILD_F2_BEFORE_F1",
                        "PLACE_WITH_UNKNOWN_AXES",
                    ],
                }

    integrity = evaluate_integrity(
        model,
        action=action,
        targets=target_list,
        place_kind=place_kind,
        place_domain=place_domain,
        nest_risk=nest_risk,
        strips_zone=strips_zone,
    )
    if integrity.get("state") != "INTEGRITY_ADMIT":
        return {
            "state": "MUTATION_DENIED",
            "gate": integrity.get("gate") or "BUILD_INTEGRITY_ADMIT",
            "reason": "MUTATE_WITHOUT_BUILD_INTEGRITY",
            "violation": integrity.get("violation"),
            "detail": integrity.get("detail"),
            "integrity": integrity,
            "spatial": spatial,
            "action": action,
            "model_revision": revision,
            "execute_allowed": False,
            "forbidden": ["MUTATE_WITHOUT_BUILD_INTEGRITY", "TREAT_OUTDOOR_AS_INDOOR", "NEST_OBJECTS"],
        }

    lease = {
        "schema": LEASE_SCHEMA,
        "run_id": model["run_id"],
        "lot_id": model["lot_id"],
        "model_revision": revision,
        "action": action,
        "targets": target_list,
        "place_domain": place_domain,
        "place_kind": place_kind,
        "place_enclosure": place_enclosure,
        "place_story": place_story,
        "integrity_gate": integrity.get("gate"),
        "spatial_gate": (spatial or {}).get("gate"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }
    return {
        "state": "MUTATION_ADMITTED",
        "gate": "HOUSE_STATE_MUTATION_LEASE",
        "lease": lease,
        "action": action,
        "reason": "MODEL_SPATIAL_AND_INTEGRITY_BACKED_MUTATION",
        "model_revision": revision,
        "integrity": integrity,
        "spatial": spatial,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "next": "OBSERVE_OUTCOME_INTO_SAME_MODEL",
        "forbidden": [
            "BLANK_SLATE_REASSESS",
            "DISCARD_MODEL_AFTER_ACTION",
            "TREAT_OUTDOOR_AS_INDOOR",
            "NEST_OBJECTS",
        ],
    }


def record_mutation_outcome(
    model: Mapping[str, Any],
    *,
    action: str,
    targets: Sequence[str] | None = None,
    entity_updates: Mapping[str, Mapping[str, Any]] | None = None,
    note: str | None = None,
) -> dict:
    """Fold an action outcome into the same model (recursive continuity)."""
    out = observe(
        model,
        entities=entity_updates,
        note=note or f"outcome:{action}",
    )
    out["last_action"] = {
        "action": action,
        "targets": [str(t) for t in (targets or [])],
        "at_revision": out["revision"],
    }
    hist = list(out.get("history") or [])
    if hist and hist[-1].get("op") == "OBSERVE":
        hist[-1]["op"] = "MUTATION_OUTCOME"
        hist[-1]["action"] = action
    out["history"] = hist
    return out


def persist_checkpoint(model: Mapping[str, Any], *, label: str = "auto") -> dict:
    """Persist current model revision as continuity — does not create a new blank model."""
    cfg = load_contract()
    if model.get("schema") != MODEL_SCHEMA:
        raise HouseStateError("INVALID_LOT_MODEL_SCHEMA")
    revision = int(model.get("revision") or 0)
    if revision <= 0:
        raise HouseStateError("CHECKPOINT_REQUIRES_ACTIVE_MODEL")
    path = save_model(model)
    safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", label)[:40] or "auto"
    receipt_path = path.parent / f"checkpoint-r{revision}-{safe_label}.json"
    receipt = {
        "schema": CHECKPOINT_SCHEMA,
        "run_id": model["run_id"],
        "lot_id": model["lot_id"],
        "model_revision": revision,
        "model_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "entity_count": len(model.get("entities") or {}),
        "open_goals": list(model.get("open_goals") or []),
        "captures": list(model.get("captures") or []),
        "save_as_attestation": model.get("save_as_attestation"),
        "continuity": "SAME_MODEL_PERSISTED_NOT_BLANK_SLATE",
        "proof_ceiling": cfg["proof_ceiling"],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {
        "state": "CHECKPOINT_PERSISTED",
        "gate": "PERSIST_MODEL_CHECKPOINT",
        "receipt": receipt,
        "receipt_path": str(receipt_path.relative_to(ROOT)).replace("\\", "/"),
        "model_path": receipt["model_path"],
        "model_revision": revision,
    }


def reject_blank_slate(attempt: Mapping[str, Any]) -> dict:
    """Fail closed when an agent tries the discarded checkpoint-from-scratch loop."""
    pattern = str(attempt.get("pattern") or "")
    if pattern in {
        "BLANK_SLATE_REASSESS",
        "DISCARD_MODEL_AFTER_ACTION",
        "CHECKPOINT_FROM_SCRATCH",
        "REASSESS_AS_IF_UNKNOWN",
    }:
        return {
            "state": "BLANK_SLATE_REJECTED",
            "gate": "ACCUMULATE_LOT_MODEL",
            "reason": pattern,
            "required": "load_or_create -> observe merge -> plan_from_model -> admit -> observe outcome",
            "forbidden": ["BLANK_SLATE_REASSESS", "DISCARD_MODEL_AFTER_ACTION"],
        }
    return {
        "state": "MODEL_ACTIVE",
        "gate": "ACCUMULATE_LOT_MODEL",
        "reason": "PATTERN_NOT_BLANK_SLATE",
    }


def recovery_advice(*, has_known_good_save: bool, wreckage_only: bool = False) -> dict:
    cfg = load_contract()
    policy = cfg["recovery_policy"]
    if has_known_good_save and not wreckage_only:
        return {
            "state": "RECOVERY_ADVICE",
            "gate": "LOAD_LAST_KNOWN_GOOD_SAVE",
            "do": policy["if_lot_destroyed_and_good_save_exists"],
            "do_not": policy["never"],
            "model_after_load": policy["model_after_load"],
        }
    return {
        "state": "RECOVERY_ADVICE",
        "gate": "DO_NOT_OVERWRITE_GOOD_SAVE_WITH_WRECKAGE",
        "do": policy["if_only_wreckage_loaded"],
        "do_not": policy["never"],
        "model_after_load": policy["model_after_load"],
    }
