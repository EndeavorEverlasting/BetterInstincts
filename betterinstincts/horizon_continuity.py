"""Validate the North Star → Continuity opener contract (offline)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "horizon-continuity.v1.json"
REQUIRED_PROMPTS = (
    "north_star",
    "owner_objective",
    "product_contract",
    "non_negotiables",
    "horizon_trajectory",
    "first_win_proof_ceiling",
    "continuity_opener",
)
REQUIRED_MARKERS = (
    "community-native",
    "needs",
    "income",
    "career",
    "Player agency",
    "needs → income → skills → career",
    "BI-002",
    "CHANGED | PROVED | NEXT",
)


class ContinuityError(ValueError):
    pass


def load_continuity(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise ContinuityError("UNSAFE_CONTINUITY_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.horizon-continuity/v1":
        raise ContinuityError("INVALID_CONTINUITY_SCHEMA")
    return data


def validate(data: dict | None = None) -> dict:
    data = data if data is not None else load_continuity()
    prompts = data.get("parent_prompts")
    if not isinstance(prompts, dict):
        raise ContinuityError("MISSING_PARENT_PROMPTS")
    missing = [k for k in REQUIRED_PROMPTS if k not in prompts]
    if missing:
        raise ContinuityError("MISSING_PROMPT:" + ",".join(missing))
    nn = prompts["non_negotiables"]
    if not isinstance(nn, list) or len(nn) != 5:
        raise ContinuityError("NON_NEGOTIABLES_COUNT")
    blob = "\n".join(
        [prompts[k] if isinstance(prompts[k], str) else "\n".join(prompts[k]) for k in REQUIRED_PROMPTS]
    )
    absent = [m for m in REQUIRED_MARKERS if m not in blob]
    if absent:
        raise ContinuityError("CONTINUITY_MARKER_GAP:" + ",".join(absent))
    selected = data.get("selected_investigation") or {}
    if selected.get("name") != "BI-002 GAME-1" or selected.get("thesis") != "A":
        raise ContinuityError("SELECTED_INVESTIGATION_DRIFT")
    opens = data.get("open_items") or []
    funds = next((x for x in opens if isinstance(x, dict) and x.get("id") == "FUNDS_PREFERRED_NON_MOTHERLODE"), None)
    if not funds or funds.get("status") != "OPEN" or funds.get("blocks_bi002") is not False:
        raise ContinuityError("FUNDS_OPEN_ITEM_LOST")
    if not (ROOT / "docs" / "HORIZON_CONTINUITY.md").is_file():
        raise ContinuityError("CONTINUITY_DOC_MISSING")
    return {
        "state": "PASS",
        "selected_investigation": selected["name"],
        "open_items": [x["id"] for x in opens if isinstance(x, dict) and "id" in x],
        "proof_ceiling": data.get("proof_ceiling"),
        "game_certification": "NOT_PROVED",
    }
