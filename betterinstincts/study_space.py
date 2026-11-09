"""Read-only homework study-location ranking over the canonical revisioned room census.

Unknown layout is a request for observation, not an excuse to start homework
on a sidewalk or kneeling on the floor. A selected room is not a click permit.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from betterinstincts.room_census import RoomCensusError, scan_lot_model

SURFACES = {"desk": 4, "dining_table": 3}
SEATS = {"dining_chair", "living_chair"}


def evaluate_study_space(
    lot_model: Optional[Mapping] = None,
    *,
    emotion: Optional[str] = None,
    lot_traits: Sequence[str] = (),
) -> dict:
    if not isinstance(lot_traits, (list, tuple)) or len(lot_traits) > 16 or any(
        not isinstance(x, str) or len(x) > 80 for x in lot_traits
    ):
        raise ValueError("LOT_TRAITS_OBSERVATION_INVALID")
    result = {
        "state": "STUDY_SCAN_REQUIRED",
        "room_id": None,
        "surface_id": None,
        "seat_id": None,
        "lot_model_revision": None,
        "candidates": [],
        "focused_emotion_observed": str(emotion or "").strip().lower() in {"focused", "very focused"},
        "study_spot_trait_observed": any(
            x.strip().lower().replace("_", " ") == "study spot" for x in lot_traits
        ),
        "execute_allowed": False,
        "forbidden": ["HOMEWORK_ON_SIDEWALK", "HOMEWORK_ON_FLOOR", "ASSUME_SEAT", "BLIND_MOVE"],
        "proof_ceiling": "ATTESTED_LOT_ROOM_ADVISORY_NOT_GAME_TARGET_CERT",
    }
    if lot_model is None:
        result["reason"] = "NO_LOT_MODEL_OBSERVED"
        return result
    try:
        census = scan_lot_model(lot_model)
    except (RoomCensusError, KeyError, TypeError, ValueError):
        result["reason"] = "LOT_MODEL_UNVERIFIED"
        return result
    result["lot_model_revision"] = census["model_revision"]
    candidates = []
    for room in census["rooms"].values():
        if room["room_evidence"] != "STRUCTURE_ATTESTED" or room["enclosure"] != "INSIDE":
            continue
        items = room["items"]
        seats = sorted((x for x in items if x["category"] in SEATS), key=lambda x: x["id"])
        surfaces = sorted(
            (x for x in items if x["category"] in SURFACES),
            key=lambda x: (-SURFACES[x["category"]], x["id"]),
        )
        if not seats or not surfaces:
            continue
        surface = surfaces[0]
        score = SURFACES[surface["category"]] + (1 if "office" in room["function_labels"] else 0)
        candidates.append({
            "room_id": room["room_id"], "surface_id": surface["id"], "seat_id": seats[0]["id"],
            "score": score,
            "reason": "ATTESTED_INDOOR_DESK_AND_SEAT" if surface["category"] == "desk"
                      else "ATTESTED_INDOOR_TABLE_AND_SEAT",
        })
    candidates.sort(key=lambda x: (-x["score"], x["room_id"], x["surface_id"]))
    result["candidates"] = candidates[:8]
    if not candidates:
        result["reason"] = "NO_ATTESTED_INDOOR_SURFACE_AND_SEAT"
        return result
    selected = candidates[0]
    result.update({
        "state": "STUDY_LOCATION_CANDIDATE",
        "room_id": selected["room_id"],
        "surface_id": selected["surface_id"],
        "seat_id": selected["seat_id"],
        "reason": selected["reason"],
    })
    return result
