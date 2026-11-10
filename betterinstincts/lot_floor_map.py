"""Per-installation-profile lot floor object map (computers, workstations, paths).

Private local store only. Never SendInput. Build-mode auto-ensure is evaluate/
seed only. Preferred growth path: opportunistic mapping when host needs logic
investigates a world object (natural interact), plus Build T census for unknowns.
Memorialized nodes update only on change evidence.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.installation_profiles import (
    InstallationProfileError,
    settings_path,
    view,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "lot-floor-map.v1.json"
MAX_BYTES = 512_000
LOT_KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class LotFloorMapError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise LotFloorMapError("LOT_FLOOR_MAP_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.lot-floor-map/v1":
        raise LotFloorMapError("BAD_LOT_FLOOR_MAP_SCHEMA")
    if cfg.get("execute_allowed_default") is not False:
        raise LotFloorMapError("LOT_FLOOR_MAP_MUST_DEFAULT_EXECUTE_FALSE")
    return cfg


def floor_map_path(
    *,
    profile_id: str,
    lot_key: str,
    settings_file: Path | None = None,
) -> Path:
    """Canonical private path for one profile + lot floor map."""
    if not LOT_KEY.fullmatch(str(lot_key or "")):
        raise LotFloorMapError("LOT_KEY_INVALID")
    settings_file = settings_path() if settings_file is None else Path(settings_file)
    view(settings_file, profile_id=profile_id)
    # Refuse writing into a repo checkout if settings_file was pointed there.
    resolved = settings_file.resolve()
    if (ROOT / ".git").exists() and ROOT.resolve() in resolved.parents:
        raise LotFloorMapError("REPO_CHECKOUT_FORBIDDEN_AS_FLOOR_ROOT")
    return settings_file.parent / "households" / profile_id / "floors" / f"{lot_key}.json"


def empty_floor_map(*, profile_id: str, lot_key: str, cfg: Optional[dict] = None) -> dict:
    cfg = cfg or load_contract()
    objects = {
        kind: {
            "object_id": kind.lower(),
            "kind": kind,
            "status": "SKELETON",
            "client_xy": None,
            "capture_ref": None,
            "camera_revision": None,
            "path_ids": [],
            "notes": "",
            "attempts": 0,
            "hits": 0,
            "misses": 0,
        }
        for kind in (cfg.get("seed_kinds_on_ensure") or [])
    }
    return {
        "schema": "betterinstincts.lot-floor-map-doc/v1",
        "profile_id": profile_id,
        "lot_key": lot_key,
        "revision": 0,
        "objects": objects,
        "graph": {"nodes": {}, "edges": []},
        "paths": {
            pid: {"path_id": pid, "status": "SKELETON", "steps": [], "notes": ""}
            for pid in (cfg.get("paths") or [])
        },
        "triggers": [],
        "note": "Private per-profile floor map. Camera-revision bound coords only.",
    }


def load_floor_map(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise LotFloorMapError("FLOOR_MAP_MISSING")
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise LotFloorMapError("FLOOR_MAP_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.lot-floor-map-doc/v1":
        raise LotFloorMapError("BAD_FLOOR_MAP_DOC_SCHEMA")
    return data


def save_floor_map(doc: Mapping[str, object], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(doc), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def auto_enabled(*, settings_file: Path | None = None, profile_id: str | None = None) -> bool:
    cfg = load_contract()
    key = str((cfg.get("auto_on_build") or {}).get("setting_key") or "learning.lot_floor_map_auto")
    effective = view(settings_file, profile_id=profile_id)["settings"]
    return bool(effective.get(key, True))


def ensure_floor_map(
    *,
    profile_id: str,
    lot_key: str,
    settings_file: Path | None = None,
    trigger: str = "ENSURE",
    cfg: Optional[dict] = None,
) -> dict:
    """Create skeleton floor map if absent; append trigger receipt."""
    cfg = cfg or load_contract()
    path = floor_map_path(profile_id=profile_id, lot_key=lot_key, settings_file=settings_file)
    if path.is_file():
        doc = load_floor_map(path)
    else:
        doc = empty_floor_map(profile_id=profile_id, lot_key=lot_key, cfg=cfg)
    triggers = list(doc.get("triggers") or [])
    triggers.append(
        {
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "trigger": str(trigger),
            "proof_ceiling": cfg["proof_ceiling"],
        }
    )
    doc["triggers"] = triggers[-64:]
    doc["revision"] = int(doc.get("revision") or 0) + 1
    save_floor_map(doc, path)
    return {
        "state": "FLOOR_MAP_ENSURED",
        "path": str(path),
        "profile_id": profile_id,
        "lot_key": lot_key,
        "revision": doc["revision"],
        "object_count": len(doc.get("objects") or {}),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def on_build_mode_entered(
    *,
    profile_id: str,
    lot_key: str,
    settings_file: Path | None = None,
) -> dict:
    """Host Build/Buy observation → auto-ensure floor map when preference allows."""
    cfg = load_contract()
    if not auto_enabled(settings_file=settings_file, profile_id=profile_id):
        return {
            "state": "FLOOR_MAP_AUTO_SKIPPED",
            "reason": "learning.lot_floor_map_auto_false",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="BUILD_MODE_ENTERED",
        cfg=cfg,
    )


def upsert_object(
    doc: dict,
    *,
    kind: str,
    object_id: str | None = None,
    client_xy: Sequence[int] | None = None,
    status: str = "OBSERVED",
    capture_ref: str = "",
    camera_revision: str | None = None,
    path_ids: Sequence[str] | None = None,
    note: str = "",
    miss_cause: str = "",
    expected_interactions: Sequence[str] | None = None,
    force_remap: bool = False,
    cfg: Optional[dict] = None,
) -> dict:
    """Upsert one floor object observation (camera-revision bound).

    MEMORIALIZED rows refuse blind durable overwrites unless force_remap or the
    incoming status is an explicit invalidation/remap pathway.
    """
    cfg = cfg or load_contract()
    kinds = set(cfg.get("object_kinds") or [])
    statuses = set(cfg.get("object_statuses") or [])
    memorial = dict(cfg.get("memorialization") or {})
    frozen = set(memorial.get("frozen_fields") or [])
    kind = str(kind)
    if kind not in kinds:
        raise LotFloorMapError("UNKNOWN_OBJECT_KIND:" + kind)
    status = str(status)
    if status not in statuses:
        raise LotFloorMapError("UNKNOWN_OBJECT_STATUS:" + status)
    oid = str(object_id or kind.lower())
    objects = dict(doc.get("objects") or {})
    row = dict(objects.get(oid) or {"object_id": oid, "kind": kind, "attempts": 0, "hits": 0, "misses": 0})
    prior_status = str(row.get("status") or "")
    memorialized = prior_status == "MEMORIALIZED" and not force_remap
    if memorialized and status in {"CANDIDATE", "OBSERVED", "SKELETON"}:
        # Noise must not unseat a memorial; annotate only.
        row["last_observation_status"] = status
        if note:
            row["last_observation_note"] = str(note)
        if client_xy is not None:
            if (
                not isinstance(client_xy, (list, tuple))
                or len(client_xy) != 2
                or any(type(v) is not int for v in client_xy)
            ):
                raise LotFloorMapError("CLIENT_XY_MUST_BE_TWO_INTS")
            row["last_client_xy"] = [int(client_xy[0]), int(client_xy[1])]
        row["attempts"] = int(row.get("attempts") or 0) + 1
        objects[oid] = row
        doc["objects"] = objects
        doc["revision"] = int(doc.get("revision") or 0) + 1
        return row
    if memorialized and status not in {
        "MEMORIALIZED",
        "STALE_NEEDS_REMAP",
        "HIT_ATTESTED",
        "MISS",
        "WRONG_CONTROL",
    }:
        raise LotFloorMapError("MEMORIALIZED_REFUSES_STATUS:" + status)

    if not (memorialized and "kind" in frozen):
        row["kind"] = kind
    row["status"] = status
    if note and not (memorialized and status in {"MISS", "WRONG_CONTROL"} and not force_remap):
        row["notes"] = str(note or row.get("notes") or "")
    elif note:
        row["notes"] = str(note or row.get("notes") or "")
    if miss_cause:
        row["last_miss_cause"] = str(miss_cause)
    if capture_ref and not (memorialized and "capture_ref" in frozen and status != "HIT_ATTESTED"):
        row["capture_ref"] = str(capture_ref)
    if camera_revision is not None:
        row["camera_revision"] = camera_revision
    if path_ids is not None and not (memorialized and "path_ids" in frozen and not force_remap):
        row["path_ids"] = [str(p) for p in path_ids]
    if expected_interactions is not None and not (
        memorialized and "expected_interactions" in frozen and not force_remap
    ):
        row["expected_interactions"] = [str(x) for x in expected_interactions]
    if client_xy is not None:
        if (
            not isinstance(client_xy, (list, tuple))
            or len(client_xy) != 2
            or any(type(v) is not int for v in client_xy)
        ):
            raise LotFloorMapError("CLIENT_XY_MUST_BE_TWO_INTS")
        # Durable xy: MEMORIALIZED/HIT_ATTESTED rewrite; else first-fill or annotate.
        if force_remap or status in {"HIT_ATTESTED", "MEMORIALIZED"} or row.get("client_xy") is None:
            if not (memorialized and "client_xy" in frozen and not force_remap and status != "MEMORIALIZED"):
                row["client_xy"] = [int(client_xy[0]), int(client_xy[1])]
        elif status in {"CANDIDATE", "OBSERVED", "STALE_NEEDS_REMAP"}:
            row["last_client_xy"] = [int(client_xy[0]), int(client_xy[1])]
    row["attempts"] = int(row.get("attempts") or 0) + 1
    if status in {"HIT_ATTESTED", "MEMORIALIZED"}:
        row["hits"] = int(row.get("hits") or 0) + (1 if status == "HIT_ATTESTED" else 0)
    if status in {"MISS", "WRONG_CONTROL"}:
        row["misses"] = int(row.get("misses") or 0) + 1
    objects[oid] = row
    doc["objects"] = objects
    doc["revision"] = int(doc.get("revision") or 0) + 1
    return row


def memorialize_object(
    doc: dict,
    *,
    object_id: str,
    expected_interactions: Sequence[str],
    note: str = "",
    cfg: Optional[dict] = None,
) -> dict:
    """Freeze a mapped object until interaction evidence says it changed."""
    cfg = cfg or load_contract()
    memorial = dict(cfg.get("memorialization") or {})
    objects = dict(doc.get("objects") or {})
    oid = str(object_id)
    if oid not in objects:
        raise LotFloorMapError("MEMORIALIZE_TARGET_MISSING:" + oid)
    row = dict(objects[oid])
    prior = str(row.get("status") or "")
    promote_from = set(memorial.get("promote_from") or ["HIT_ATTESTED", "OBSERVED"])
    if prior == "MEMORIALIZED":
        return row
    if prior not in promote_from and prior != "STALE_NEEDS_REMAP":
        raise LotFloorMapError("MEMORIALIZE_STATUS_NOT_ELIGIBLE:" + prior)
    if not expected_interactions:
        raise LotFloorMapError("EXPECTED_INTERACTIONS_REQUIRED")
    interactions = [str(x) for x in expected_interactions if str(x).strip()]
    if not interactions:
        raise LotFloorMapError("EXPECTED_INTERACTIONS_REQUIRED")
    row["status"] = "MEMORIALIZED"
    row["expected_interactions"] = interactions
    row["memorialized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if note:
        row["notes"] = str(note)
    row.pop("stale_reason", None)
    objects[oid] = row
    doc["objects"] = objects
    # Mirror graph node status when present.
    g = _graph(doc)
    for nid, node in list((g.get("nodes") or {}).items()):
        if isinstance(node, dict) and (
            node.get("object_id") == oid or node.get("node_id") == oid
        ):
            node = dict(node)
            node["status"] = "MEMORIALIZED"
            g["nodes"][nid] = node
    doc["revision"] = int(doc.get("revision") or 0) + 1
    return row


def invalidate_memorial(
    doc: dict,
    *,
    object_id: str,
    reason: str,
    observed_interactions: Sequence[str] | None = None,
    note: str = "",
    cfg: Optional[dict] = None,
) -> dict:
    """Mark memorialized object STALE_NEEDS_REMAP (continuous remap trigger)."""
    cfg = cfg or load_contract()
    memorial = dict(cfg.get("memorialization") or {})
    allowed = set(memorial.get("update_when") or [])
    reason = str(reason)
    if reason not in allowed:
        raise LotFloorMapError("UNKNOWN_INVALIDATION_REASON:" + reason)
    objects = dict(doc.get("objects") or {})
    oid = str(object_id)
    if oid not in objects:
        raise LotFloorMapError("INVALIDATE_TARGET_MISSING:" + oid)
    row = dict(objects[oid])
    if str(row.get("status") or "") not in {"MEMORIALIZED", "STALE_NEEDS_REMAP", "HIT_ATTESTED"}:
        raise LotFloorMapError("INVALIDATE_REQUIRES_MEMORIAL_OR_HIT")
    expected = [str(x) for x in (row.get("expected_interactions") or [])]
    observed = [str(x) for x in (observed_interactions or [])]
    if reason == "EXPECTED_INTERACTION_MISSING" and expected:
        missing = [e for e in expected if e not in observed]
        if not missing and observed:
            # All expected labels present — not an invalidation.
            raise LotFloorMapError("EXPECTED_INTERACTIONS_STILL_PRESENT")
        row["missing_interactions"] = missing or list(expected)
    row["status"] = str(memorial.get("on_invalidation_status") or "STALE_NEEDS_REMAP")
    row["stale_reason"] = reason
    row["stale_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if observed:
        row["last_observed_interactions"] = observed
    if note:
        row["notes"] = str(note)
    row["misses"] = int(row.get("misses") or 0) + 1
    objects[oid] = row
    doc["objects"] = objects
    g = _graph(doc)
    for nid, node in list((g.get("nodes") or {}).items()):
        if isinstance(node, dict) and (
            node.get("object_id") == oid or node.get("node_id") == oid
        ):
            node = dict(node)
            node["status"] = "STALE_NEEDS_REMAP"
            g["nodes"][nid] = node
    doc["revision"] = int(doc.get("revision") or 0) + 1
    return row


def assess_interaction_against_memorial(
    doc: dict,
    *,
    object_id: str,
    observed_interactions: Sequence[str],
    cfg: Optional[dict] = None,
) -> dict:
    """Continuous gate: keep memorial or invalidate when expected pie is absent."""
    cfg = cfg or load_contract()
    objects = dict(doc.get("objects") or {})
    oid = str(object_id)
    row = objects.get(oid)
    if not isinstance(row, Mapping):
        return {
            "state": "OBJECT_UNKNOWN",
            "object_id": oid,
            "action": "MAP_FIRST",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    status = str(row.get("status") or "")
    expected = [str(x) for x in (row.get("expected_interactions") or [])]
    observed = [str(x) for x in observed_interactions]
    if status != "MEMORIALIZED":
        return {
            "state": "NOT_MEMORIALIZED",
            "object_id": oid,
            "status": status,
            "action": "MAP_OR_MEMORIALIZE",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    missing = [e for e in expected if e not in observed]
    if missing:
        invalidate_memorial(
            doc,
            object_id=oid,
            reason="EXPECTED_INTERACTION_MISSING",
            observed_interactions=observed,
            note="expected interaction absent at interact time",
            cfg=cfg,
        )
        return {
            "state": "INVALIDATED_NEEDS_REMAP",
            "object_id": oid,
            "missing_interactions": missing,
            "action": "REMAP_NODE",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    return {
        "state": "MEMORIAL_STILL_VALID",
        "object_id": oid,
        "action": "KEEP",
        "expected_interactions": expected,
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def list_remap_targets(doc: Mapping[str, object]) -> list[str]:
    """Object ids that continuous mapping must refresh."""
    out = []
    for oid, row in (doc.get("objects") or {}).items():
        if isinstance(row, Mapping) and str(row.get("status") or "") == "STALE_NEEDS_REMAP":
            out.append(str(oid))
    return sorted(out)


_NEED_KIND_HINTS = (
    ("computer", "COMPUTER_DESKTOP"),
    ("desktop", "COMPUTER_DESKTOP"),
    ("laptop", "COMPUTER_LAPTOP"),
    ("robotics", "ROBOTICS_WORKSTATION"),
    ("workbench", "ROBOTICS_WORKSTATION"),
    ("workstation", "ROBOTICS_WORKSTATION"),
    ("phone", "PHONE_HUD"),
    ("dining", "LANDMARK_DINING_TABLE"),
    ("table", "LANDMARK_DINING_TABLE"),
    ("rug", "LANDMARK_RUG_CLUSTER"),
)


def infer_object_kind(target_id: str, *, need_id: str | None = None) -> str | None:
    """Best-effort kind from target/need tokens; None if unknown (no invent)."""
    blob = f"{target_id} {need_id or ''}".lower()
    for token, kind in _NEED_KIND_HINTS:
        if token in blob:
            return kind
    return None


def client_center_from_bbox(bbox_client: Sequence[int]) -> list[int]:
    """Measured item center from [left, top, right, bottom] client pixels.

    Agent census/placement clicks must use this center — not a corner guess.
    """
    if (
        not isinstance(bbox_client, (list, tuple))
        or len(bbox_client) != 4
        or any(type(v) is not int for v in bbox_client)
    ):
        raise LotFloorMapError("BBOX_CLIENT_MUST_BE_FOUR_INTS")
    left, top, right, bottom = (
        int(bbox_client[0]),
        int(bbox_client[1]),
        int(bbox_client[2]),
        int(bbox_client[3]),
    )
    if right <= left or bottom <= top:
        raise LotFloorMapError("BBOX_CLIENT_EMPTY")
    return [(left + right) // 2, (top + bottom) // 2]


def _client_xy_from_observation(observation: Mapping[str, object]) -> list[int] | None:
    bbox = observation.get("bbox_client")
    if bbox is not None:
        try:
            return client_center_from_bbox(bbox)  # type: ignore[arg-type]
        except LotFloorMapError:
            return None
    xy = observation.get("client_xy")
    if (
        isinstance(xy, (list, tuple))
        and len(xy) == 2
        and all(type(v) is int for v in xy)
    ):
        return [int(xy[0]), int(xy[1])]
    return None


def placement_auto_enabled(
    *, settings_file: Path | None = None, profile_id: str | None = None
) -> bool:
    """True when builder placement auto-map may run (default on)."""
    cfg = load_contract()
    key = str(
        (cfg.get("builder_placement_auto_map") or {}).get("setting_key")
        or "learning.build_placement_auto_map"
    )
    settings_file = settings_path() if settings_file is None else Path(settings_file)
    try:
        effective = view(settings_file, profile_id=profile_id)["settings"]
        return bool(effective.get(key, True))
    except InstallationProfileError:
        return True


def record_builder_placement(
    *,
    profile_id: str,
    lot_key: str,
    catalog_name: str,
    bbox_client: Sequence[int],
    capture_ref: str,
    camera_revision: str,
    object_id: str | None = None,
    kind: str = "BUILD_CENSUS_ITEM",
    parent_object_id: str | None = None,
    link_relation: str = "ON_TOP_OF",
    linked_object_ids: Sequence[str] | None = None,
    price: str | None = None,
    category: str | None = None,
    note: str = "",
    settings_file: Path | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Record a builder LMB place into the floor graph (host tick / observe only).

    Placement is the natural builder confirm — not Escape. Linked furniture
    (chair on desk) becomes graph edges. Requires bbox center. Never SendInput.
    Runtime is cooperative host_listener while BI is installed — not OS cron.
    """
    cfg = cfg or load_contract()
    place_cfg = dict(cfg.get("builder_placement_auto_map") or {})
    if not placement_auto_enabled(settings_file=settings_file, profile_id=profile_id):
        return {
            "state": "BUILD_PLACEMENT_AUTO_SKIPPED",
            "reason": "learning.build_placement_auto_map_false",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "runtime": place_cfg.get("runtime"),
        }
    if not isinstance(catalog_name, str) or not 1 <= len(catalog_name.strip()) <= 128:
        raise LotFloorMapError("BUILD_PLACEMENT_CATALOG_NAME_REQUIRED")
    if not isinstance(capture_ref, str) or not capture_ref:
        raise LotFloorMapError("CAPTURE_REF_REQUIRED")
    if not isinstance(camera_revision, str) or not camera_revision:
        raise LotFloorMapError("CAMERA_REVISION_REQUIRED")
    center = client_center_from_bbox(bbox_client)
    oid = object_id or re.sub(
        r"[^a-z0-9_]+", "_", catalog_name.strip().lower()
    ).strip("_")[:64]
    if not oid:
        oid = "placed_item"
    allowed_links = set(place_cfg.get("graph_links") or [])
    relation = str(link_relation)
    if parent_object_id is not None and relation not in allowed_links:
        raise LotFloorMapError("UNKNOWN_PLACEMENT_LINK_RELATION:" + relation)

    ensured = ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="BUILD_PLACEMENT_LMB",
        cfg=cfg,
    )
    path = Path(ensured["path"])
    doc = load_floor_map(path)
    role = "SLOTTED_CHILD" if parent_object_id else "TARGET"
    if kind in {"LANDMARK_DINING_TABLE", "LANDMARK_RUG_CLUSTER"}:
        role = "LANDMARK"
    node = upsert_graph_node(
        doc,
        node_id=oid,
        kind=kind,
        role=role,
        object_id=oid,
        client_xy=center,
        status="OBSERVED",
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note=note or f"builder_place:{catalog_name.strip()}",
        cfg=cfg,
    )
    objects = dict(doc.get("objects") or {})
    row = dict(objects.get(oid) or {})
    row["catalog_name"] = catalog_name.strip()
    row["bbox_client"] = [int(v) for v in bbox_client]
    row["client_xy"] = center
    row["census_method"] = "BUILD_PLACEMENT_LMB"
    row["zoom_mode"] = "BUILD_TOP_DOWN_MAP"
    if price is not None:
        row["price"] = str(price)
    if category is not None:
        row["category"] = str(category)
    if parent_object_id:
        row["parent_object_id"] = str(parent_object_id)
    objects[oid] = row
    doc["objects"] = objects

    edges_written = []
    if parent_object_id:
        parent = str(parent_object_id)
        if parent not in (_graph(doc).get("nodes") or {}):
            upsert_graph_node(
                doc,
                node_id=parent,
                kind="BUILD_CENSUS_ITEM",
                role="SURFACE",
                object_id=parent,
                status="CANDIDATE",
                capture_ref=capture_ref,
                camera_revision=camera_revision,
                note="inferred_parent_surface",
                cfg=cfg,
            )
        edge = upsert_graph_edge(
            doc,
            from_id=oid,
            to_id=parent,
            direction="ON",
            relation=relation,
            note=f"{catalog_name.strip()} -> {parent}",
            cfg=cfg,
        )
        edges_written.append(edge)
    for linked in linked_object_ids or ():
        lid = str(linked)
        if not lid or lid == oid:
            continue
        if lid not in (_graph(doc).get("nodes") or {}):
            upsert_graph_node(
                doc,
                node_id=lid,
                kind="BUILD_CENSUS_ITEM",
                role="TARGET",
                object_id=lid,
                status="CANDIDATE",
                capture_ref=capture_ref,
                camera_revision=camera_revision,
                note="linked_peer",
                cfg=cfg,
            )
        edges_written.append(
            upsert_graph_edge(
                doc,
                from_id=oid,
                to_id=lid,
                direction="LINK",
                relation="LINKED_WITH",
                note="builder_linked",
                cfg=cfg,
            )
        )

    doc["census_zoom"] = {
        "mode": "BUILD_TOP_DOWN_MAP",
        "room_fit_attested": True,
        "preserve_operator_centered_frame": True,
        "camera_revision": camera_revision,
        "capture_ref": capture_ref,
        "source": "BUILD_PLACEMENT_AUTO_MAP",
    }
    save_floor_map(doc, path)
    return {
        "state": "BUILD_PLACEMENT_RECORDED",
        "object_id": oid,
        "catalog_name": catalog_name.strip(),
        "client_xy": center,
        "bbox_client": [int(v) for v in bbox_client],
        "graph_node": node.get("node_id"),
        "edges": edges_written,
        "path": str(path),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "runtime": place_cfg.get("runtime") or "HOST_LISTENER_COOPERATIVE_TICK",
        "not_runtime": list(place_cfg.get("not_runtime") or []),
    }


def record_build_select_inspect(
    *,
    profile_id: str,
    lot_key: str,
    catalog_name: str,
    capture_ref: str,
    camera_revision: str,
    client_xy: Sequence[int] | None = None,
    bbox_client: Sequence[int] | None = None,
    object_id: str | None = None,
    kind: str = "BUILD_CENSUS_ITEM",
    price: str | None = None,
    category: str | None = None,
    params: Mapping[str, object] | None = None,
    note: str = "",
    memorialized: bool = False,
    settings_file: Path | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Record one Build Select-inspect → Escape census observation.

    Caller must click the measured bbox center, then Escape. Prefer bbox_client;
    guessed corner clicks are rejected when bbox is present but center missing.
    """
    cfg = cfg or load_contract()
    inspect_cfg = dict(cfg.get("build_select_inspect") or {})
    if not isinstance(catalog_name, str) or not 1 <= len(catalog_name.strip()) <= 128:
        raise LotFloorMapError("BUILD_CENSUS_CATALOG_NAME_REQUIRED")
    if bbox_client is not None:
        center = client_center_from_bbox(bbox_client)
    elif (
        isinstance(client_xy, (list, tuple))
        and len(client_xy) == 2
        and all(type(v) is int for v in client_xy)
    ):
        center = [int(client_xy[0]), int(client_xy[1])]
    else:
        raise LotFloorMapError("BBOX_CENTER_OR_CLIENT_XY_REQUIRED")
    if not isinstance(capture_ref, str) or not capture_ref:
        raise LotFloorMapError("CAPTURE_REF_REQUIRED")
    if not isinstance(camera_revision, str) or not camera_revision:
        raise LotFloorMapError("CAMERA_REVISION_REQUIRED")
    oid = object_id or re.sub(
        r"[^a-z0-9_]+", "_", catalog_name.strip().lower()
    ).strip("_")[:64]
    if not oid:
        oid = "build_census_item"
    ensured = ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="BUILD_SELECT_INSPECT_ESCAPE",
        cfg=cfg,
    )
    path = Path(ensured["path"])
    doc = load_floor_map(path)
    note_bits = [note] if note else []
    if price:
        note_bits.append(f"price={price}")
    if category:
        note_bits.append(f"category={category}")
    row = upsert_object(
        doc,
        kind=kind,
        object_id=oid,
        client_xy=center,
        status="OBSERVED",
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note="; ".join(x for x in note_bits if x),
        cfg=cfg,
    )
    row["catalog_name"] = catalog_name.strip()
    if bbox_client is not None:
        row["bbox_client"] = [int(v) for v in bbox_client]
    if price is not None:
        row["price"] = str(price)
    if category is not None:
        row["category"] = str(category)
    if params is not None:
        if not isinstance(params, Mapping):
            raise LotFloorMapError("BUILD_CENSUS_PARAMS_MUST_BE_MAPPING")
        row["build_params"] = dict(params)
    row["census_method"] = "BUILD_SELECT_INSPECT_ESCAPE"
    row["zoom_mode"] = inspect_cfg.get("zoom_mode") or "BUILD_TOP_DOWN_MAP"
    row["escape_required_after_inspect"] = True
    objects = dict(doc.get("objects") or {})
    objects[oid] = row
    doc["objects"] = objects
    doc["census_zoom"] = {
        "mode": "BUILD_TOP_DOWN_MAP",
        "room_fit_attested": True,
        "preserve_operator_centered_frame": True,
        "camera_revision": camera_revision,
        "capture_ref": capture_ref,
    }
    if memorialized:
        memorialize_object(
            doc,
            object_id=oid,
            expected_interactions=[],
            note="build_select_inspect",
            cfg=cfg,
        )
        row = (doc.get("objects") or {}).get(oid) or row
    save_floor_map(doc, path)
    return {
        "state": "BUILD_CENSUS_RECORDED",
        "object_id": oid,
        "catalog_name": catalog_name.strip(),
        "client_xy": center,
        "path": str(path),
        "status": row.get("status"),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "next": "ESCAPE_THEN_NEXT_OBJECT",
        "zoom_mode": "BUILD_TOP_DOWN_MAP",
        "click_target": "BBOX_CENTER",
    }


def opportunistic_needs_map(
    *,
    profile_id: str,
    lot_key: str,
    target_id: str,
    observation: Mapping[str, object] | None,
    need_id: str | None = None,
    kind: str | None = None,
    expected_interactions: Sequence[str] | None = None,
    observed_interactions: Sequence[str] | None = None,
    settings_file: Path | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Map/assess a floor object while host investigates it for needs.

    Preferred continuous path vs Build T sampling sprints. Observe/store only —
    never SendInput. Memorialized targets are assessed; missing expected
    interactions invalidate for remap.
    """
    cfg = cfg or load_contract()
    opportunity = dict((cfg.get("memorialization") or {}).get("needs_opportunity") or {})
    if not isinstance(target_id, str) or not 1 <= len(target_id) <= 96:
        raise LotFloorMapError("NEEDS_MAP_TARGET_ID_REQUIRED")
    if not isinstance(observation, Mapping):
        return {
            "state": "NEEDS_MAP_HOLD",
            "reason": "HOST_OBSERVATION_REQUIRED",
            "action": "REOBSERVE",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "opportunity": opportunity.get("id"),
        }
    resolved_kind = kind or infer_object_kind(target_id, need_id=need_id)
    if resolved_kind is None:
        return {
            "state": "NEEDS_MAP_KIND_UNKNOWN",
            "target_id": target_id,
            "need_id": need_id,
            "action": "SKIP_OR_BUILD_T_FALLBACK",
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "opportunity": opportunity.get("id"),
        }
    ensured = ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="NEEDS_INVESTIGATION_OPPORTUNITY",
        cfg=cfg,
    )
    path = Path(ensured["path"])
    doc = load_floor_map(path)
    oid = re.sub(r"[^a-z0-9_]+", "_", target_id.strip().lower()).strip("_")[:64] or resolved_kind.lower()
    existing = (doc.get("objects") or {}).get(oid)
    if isinstance(existing, Mapping) and str(existing.get("status") or "") == "MEMORIALIZED":
        if observed_interactions is not None:
            assessed = assess_interaction_against_memorial(
                doc,
                object_id=oid,
                observed_interactions=observed_interactions,
                cfg=cfg,
            )
            if assessed.get("state") == "INVALIDATED_NEEDS_REMAP":
                save_floor_map(doc, path)
            assessed = dict(assessed)
            assessed["path"] = str(path)
            assessed["opportunity"] = opportunity.get("id")
            assessed["source"] = "NEEDS_INVESTIGATION"
            return assessed
        return {
            "state": "MEMORIAL_REUSED",
            "object_id": oid,
            "action": "KEEP",
            "path": str(path),
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
            "opportunity": opportunity.get("id"),
            "source": "NEEDS_INVESTIGATION",
        }
    xy = _client_xy_from_observation(observation)
    row = upsert_object(
        doc,
        kind=resolved_kind,
        object_id=oid,
        client_xy=xy,
        status="OBSERVED" if xy else "CANDIDATE",
        capture_ref=str(observation.get("capture_ref") or ""),
        camera_revision=(
            str(observation["camera_revision"])
            if observation.get("camera_revision") is not None
            else None
        ),
        note=f"needs_opportunity need={need_id or 'unknown'} target={target_id}",
        expected_interactions=expected_interactions,
        cfg=cfg,
    )
    upsert_graph_node(
        doc,
        node_id=oid,
        kind=resolved_kind,
        role="TARGET",
        object_id=oid,
        client_xy=xy,
        status=str(row.get("status") or "OBSERVED"),
        capture_ref=str(observation.get("capture_ref") or ""),
        camera_revision=(
            str(observation["camera_revision"])
            if observation.get("camera_revision") is not None
            else None
        ),
        note=f"opportunistic needs map:{need_id or ''}",
        cfg=cfg,
    )
    save_floor_map(doc, path)
    return {
        "state": "NEEDS_MAP_OBSERVED",
        "object_id": oid,
        "kind": resolved_kind,
        "status": row.get("status"),
        "client_xy": row.get("client_xy"),
        "path": str(path),
        "revision": doc["revision"],
        "action": "MEMORIALIZE_AFTER_HIT_OR_STABLE_INTERACT",
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "opportunity": opportunity.get("id"),
        "source": "NEEDS_INVESTIGATION",
    }


def ingest_parts_buy_observations(
    ledger: Mapping[str, object],
    *,
    profile_id: str,
    lot_key: str,
    settings_file: Path | None = None,
) -> dict:
    """Seed profile floor map from a parts-buy click ledger (local observations)."""
    cfg = load_contract()
    ensured = ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="INGEST_PARTS_BUY_LEDGER",
        cfg=cfg,
    )
    path = Path(ensured["path"])
    doc = load_floor_map(path)
    targets = ledger.get("targets") if isinstance(ledger.get("targets"), Mapping) else {}
    # Phone HUD
    phone = targets.get("live.phone") if isinstance(targets, Mapping) else None
    if isinstance(phone, Mapping) and phone.get("client_xy"):
        upsert_object(
            doc,
            kind="PHONE_HUD",
            object_id="phone_hud",
            client_xy=list(phone["client_xy"]),
            status="OBSERVED",
            capture_ref="parts-buy/phone",
            path_ids=["phone_order_upgrade_parts"],
            note="Fixed HUD; zoom does not help",
            cfg=cfg,
        )
    bag = targets.get("phone.shopping_bag") if isinstance(targets, Mapping) else None
    if isinstance(bag, Mapping) and "WRONG_CONTROL" in str(bag.get("status") or ""):
        upsert_object(
            doc,
            kind="PHONE_HUD",
            object_id="phone_shopping_bag",
            client_xy=list(bag.get("client_xy") or [216, 857]),
            status="WRONG_CONTROL",
            note=str(bag.get("note") or "gifts/Plopsy not upgrade parts"),
            miss_cause="WRONG_CONTROL",
            path_ids=["phone_order_upgrade_parts"],
            cfg=cfg,
        )
    desk = targets.get("live.desk_computer") if isinstance(targets, Mapping) else None
    if isinstance(desk, Mapping):
        xy = desk.get("client_xy")
        if isinstance(xy, list) and len(xy) == 2:
            upsert_object(
                doc,
                kind="COMPUTER_DESKTOP",
                object_id="desk_computer_primary",
                client_xy=[int(xy[0]), int(xy[1])],
                status="CANDIDATE",
                path_ids=["computer_order_upgrade_parts"],
                note="Zoomed OBJECT_PICK_IDENTIFY; avoid lamps/servo",
                cfg=cfg,
            )
    lap = targets.get("live.desk_laptop") if isinstance(targets, Mapping) else None
    if isinstance(lap, Mapping) and lap.get("client_xy"):
        upsert_object(
            doc,
            kind="COMPUTER_LAPTOP",
            object_id="desk_laptop_primary",
            client_xy=list(lap["client_xy"]),
            status="CANDIDATE",
            path_ids=["computer_order_upgrade_parts"],
            cfg=cfg,
        )
    # Path notes from known miss patterns
    upsert_object(
        doc,
        kind="AVOID_LIGHT_DECO",
        object_id="avoid_plumbob_lamps",
        status="OBSERVED",
        note="Plumbob lamps open light pie (Turn On/Auto-Lights) — not Order",
        miss_cause="WRONG_CONTROL",
        cfg=cfg,
    )
    upsert_object(
        doc,
        kind="AVOID_SERVO_BODY",
        object_id="avoid_servo_body",
        status="OBSERVED",
        note="Servo body steals clicks meant for desk computers",
        miss_cause="WRONG_CONTROL",
        cfg=cfg,
    )
    upsert_object(
        doc,
        kind="ROBOTICS_WORKSTATION",
        object_id="robotics_workstation_primary",
        status="SKELETON",
        path_ids=["spawn_crafting_supplies"],
        note=(
            "GRAY body (not blue water generator); Gardener-Bot needs fix; "
            "Servo pending activation — DO NOT Activate. "
            "Cardinal fallback: ~90° from front door. "
            "Shift+click Spawn Crafting Supplies after testingcheats."
        ),
        cfg=cfg,
    )
    # Record computer HIT from live 20261110 if ledger notes it
    for step in ledger.get("steps") or []:
        if not isinstance(step, Mapping):
            continue
        if step.get("target_id") == "live.desk_computer" and "ZOOMED" in str(step.get("note") or ""):
            xy = step.get("client_xy")
            if isinstance(xy, list) and len(xy) == 2:
                upsert_object(
                    doc,
                    kind="COMPUTER_DESKTOP",
                    object_id="desk_computer_progress_bar",
                    client_xy=[int(xy[0]), int(xy[1])],
                    status="OBSERVED",
                    capture_ref=str(step.get("capture") or ""),
                    path_ids=["computer_order_upgrade_parts"],
                    note=str(step.get("note") or ""),
                    cfg=cfg,
                )
    save_floor_map(doc, path)
    return {
        "state": "FLOOR_MAP_INGESTED",
        "path": str(path),
        "revision": doc["revision"],
        "objects": sorted((doc.get("objects") or {}).keys()),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def _graph(doc: dict) -> dict:
    g = doc.get("graph")
    if not isinstance(g, dict):
        g = {"nodes": {}, "edges": []}
        doc["graph"] = g
    g.setdefault("nodes", {})
    g.setdefault("edges", [])
    if not isinstance(g["nodes"], dict):
        g["nodes"] = {}
    if not isinstance(g["edges"], list):
        g["edges"] = []
    return g


def upsert_graph_node(
    doc: dict,
    *,
    node_id: str,
    kind: str,
    role: str = "LANDMARK",
    object_id: str | None = None,
    client_xy: Sequence[int] | None = None,
    status: str = "OBSERVED",
    capture_ref: str = "",
    camera_revision: str | None = None,
    note: str = "",
    cfg: Optional[dict] = None,
) -> dict:
    """Upsert a room-map graph node and mirror into objects when kind known."""
    cfg = cfg or load_contract()
    roles = set(((cfg.get("graph") or {}).get("node_roles")) or [])
    if role not in roles:
        raise LotFloorMapError("UNKNOWN_GRAPH_NODE_ROLE:" + str(role))
    nid = str(node_id)
    if not 1 <= len(nid) <= 96:
        raise LotFloorMapError("GRAPH_NODE_ID_INVALID")
    row = upsert_object(
        doc,
        kind=kind,
        object_id=object_id or nid,
        client_xy=client_xy,
        status=status,
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note=note,
        cfg=cfg,
    )
    g = _graph(doc)
    g["nodes"][nid] = {
        "node_id": nid,
        "object_id": row["object_id"],
        "kind": kind,
        "role": role,
        "status": status,
        "client_xy": row.get("client_xy"),
        "camera_revision": row.get("camera_revision"),
        "notes": row.get("notes") or note,
    }
    doc["revision"] = int(doc.get("revision") or 0) + 1
    return g["nodes"][nid]


def upsert_graph_edge(
    doc: dict,
    *,
    from_id: str,
    to_id: str,
    direction: str = "ADJACENT",
    relation: str = "ADJACENT",
    pan_hint: Sequence[str] | None = None,
    note: str = "",
    cfg: Optional[dict] = None,
) -> dict:
    """Upsert a relative edge between two graph nodes (endpoints required)."""
    cfg = cfg or load_contract()
    relations = set(((cfg.get("graph") or {}).get("edge_relations")) or [])
    if relation not in relations:
        raise LotFloorMapError("UNKNOWN_GRAPH_EDGE_RELATION:" + str(relation))
    g = _graph(doc)
    nodes = g["nodes"]
    if from_id not in nodes or to_id not in nodes:
        raise LotFloorMapError("GRAPH_EDGE_ENDPOINTS_REQUIRED")
    edge = {
        "from": str(from_id),
        "to": str(to_id),
        "direction": str(direction),
        "relation": str(relation),
        "pan_hint": [str(p) for p in (pan_hint or [])],
        "notes": str(note or ""),
    }
    edges = [
        e
        for e in g["edges"]
        if not (
            isinstance(e, Mapping)
            and e.get("from") == edge["from"]
            and e.get("to") == edge["to"]
            and e.get("relation") == edge["relation"]
        )
    ]
    edges.append(edge)
    g["edges"] = edges[-128:]
    doc["revision"] = int(doc.get("revision") or 0) + 1
    return edge


def record_room_landmarks(
    *,
    profile_id: str,
    lot_key: str,
    workbench_xy: Sequence[int] | None = None,
    dining_xy: Sequence[int] | None = None,
    rug_xy: Sequence[int] | None = None,
    capture_ref: str = "",
    camera_revision: str | None = None,
    settings_file: Path | None = None,
) -> dict:
    """Record dining/rugs → corner workbench graph from a live room traverse."""
    cfg = load_contract()
    ensured = ensure_floor_map(
        profile_id=profile_id,
        lot_key=lot_key,
        settings_file=settings_file,
        trigger="ROOM_MAP_TRAVERSE_LIVE",
        cfg=cfg,
    )
    path = Path(ensured["path"])
    doc = load_floor_map(path)
    upsert_graph_node(
        doc,
        node_id="landmark_dining_table",
        kind="LANDMARK_DINING_TABLE",
        role="LANDMARK",
        client_xy=dining_xy,
        status="OBSERVED" if dining_xy else "OBSERVED",
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note="Glass-top dining table; ornate high-back chairs",
        cfg=cfg,
    )
    upsert_graph_node(
        doc,
        node_id="landmark_rug_cluster",
        kind="LANDMARK_RUG_CLUSTER",
        role="LANDMARK",
        client_xy=rug_xy,
        status="OBSERVED",
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note="Overlapping dark damask rugs under dining + toward corner",
        cfg=cfg,
    )
    upsert_graph_node(
        doc,
        node_id="robotics_workstation_primary",
        kind="ROBOTICS_WORKSTATION",
        role="TARGET",
        object_id="robotics_workstation_primary",
        client_xy=workbench_xy,
        status="OBSERVED" if workbench_xy else "OBSERVED",
        capture_ref=capture_ref,
        camera_revision=camera_revision,
        note=(
            "Corner workbench / robotics station: yellow-black hazard strip; "
            "E of dining+rugs; Servo often docked"
        ),
        cfg=cfg,
    )
    upsert_graph_edge(
        doc,
        from_id="landmark_dining_table",
        to_id="landmark_rug_cluster",
        direction="OVERLAP",
        relation="COLOCATED_LANDMARK",
        note="Table sits on overlapping rugs",
        cfg=cfg,
    )
    upsert_graph_edge(
        doc,
        from_id="landmark_rug_cluster",
        to_id="robotics_workstation_primary",
        direction="E",
        relation="CORNER_OF",
        pan_hint=["E", "SE"],
        note="Workbench at corner where rugs meet stone tile",
        cfg=cfg,
    )
    save_floor_map(doc, path)
    return {
        "state": "ROOM_LANDMARKS_RECORDED",
        "path": str(path),
        "revision": doc["revision"],
        "graph_nodes": sorted((_graph(doc)["nodes"]).keys()),
        "graph_edges": len(_graph(doc)["edges"]),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
    }


# Re-export for callers that already import InstallationProfileError patterns.
__all__ = [
    "LotFloorMapError",
    "InstallationProfileError",
    "load_contract",
    "floor_map_path",
    "ensure_floor_map",
    "on_build_mode_entered",
    "upsert_object",
    "memorialize_object",
    "invalidate_memorial",
    "assess_interaction_against_memorial",
    "list_remap_targets",
    "infer_object_kind",
    "opportunistic_needs_map",
    "record_build_select_inspect",
    "record_builder_placement",
    "client_center_from_bbox",
    "placement_auto_enabled",
    "upsert_graph_node",
    "upsert_graph_edge",
    "record_room_landmarks",
    "ingest_parts_buy_observations",
    "auto_enabled",
    "load_floor_map",
    "save_floor_map",
]
