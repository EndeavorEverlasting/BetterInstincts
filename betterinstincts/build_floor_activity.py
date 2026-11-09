"""Build Mode floor-activity census for the opt-in host listener.

P95 selected architecture: FLOOR_ACTIVITY_CENSUS.
Classifies SINGLE_FLOOR vs MULTI_FLOOR activity, active story, and per-floor
themes from attested item categories — never invents objects from pixels.
Advisory optimize hints only; no SendInput.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.build_spatial import normalize_story

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-floor-activity.v1.json"
MAX_BYTES = 96_000
KNOWN_STORIES = frozenset({"FLOOR_1", "FLOOR_2"})


class BuildFloorActivityError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BuildFloorActivityError("BUILD_FLOOR_ACTIVITY_CONTRACT_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.build-floor-activity/v1":
        raise BuildFloorActivityError("BAD_BUILD_FLOOR_ACTIVITY_SCHEMA")
    if cfg.get("architecture", {}).get("selected") != "FLOOR_ACTIVITY_CENSUS":
        raise BuildFloorActivityError("FLOOR_ACTIVITY_CENSUS_REQUIRED")
    if "PIXEL_ONLY_HEIGHT_HEURISTIC" not in {
        r.get("id") for r in (cfg.get("architecture", {}).get("rejected") or [])
    }:
        raise BuildFloorActivityError("PIXEL_HEURISTIC_MUST_STAY_REJECTED")
    themes = cfg.get("themes") or []
    if "unknown" not in themes or "kitchen" not in themes:
        raise BuildFloorActivityError("THEMES_INCOMPLETE")
    return cfg


def _story(raw: object) -> str:
    if raw is None or raw == "":
        return "UNKNOWN_STORY"
    return normalize_story(raw)


def _theme_for_category(category: str, cfg: dict) -> str:
    mapping = cfg.get("category_to_theme") or {}
    key = str(category or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key in mapping:
        return str(mapping[key])
    for needle, theme in mapping.items():
        if needle and needle in key:
            return str(theme)
    return "unknown"


def _normalize_items(raw_items: object) -> list[dict]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, (list, tuple)):
        raise BuildFloorActivityError("FLOOR_ITEMS_MUST_BE_LIST")
    out: list[dict] = []
    for row in raw_items:
        if not isinstance(row, Mapping):
            raise BuildFloorActivityError("FLOOR_ITEM_ROW_INVALID")
        item_id = str(row.get("id") or row.get("label") or "").strip()
        category = str(row.get("category") or "").strip()
        if not item_id and not category:
            raise BuildFloorActivityError("FLOOR_ITEM_MISSING_ID_OR_CATEGORY")
        out.append({
            "id": item_id or category,
            "category": category or "unknown",
            "story": _story(row.get("story")),
            "label": str(row.get("label") or item_id or category),
        })
    return out


def theme_from_categories(categories: Sequence[str], cfg: Optional[dict] = None) -> dict:
    """Majority theme from attested categories; ties → decor_mixed if mixed else unknown."""
    cfg = cfg or load_contract()
    counts: Counter[str] = Counter()
    for cat in categories:
        counts[_theme_for_category(cat, cfg)] += 1
    if not counts:
        return {
            "theme": "unknown",
            "confidence": "NONE",
            "histogram": {},
            "attested_item_count": 0,
        }
    # Drop pure unknown mass when other themes exist
    ranked = counts.most_common()
    top_theme, top_n = ranked[0]
    if top_theme == "unknown" and len(ranked) > 1:
        top_theme, top_n = ranked[1]
    distinct = [t for t, n in ranked if t != "unknown" and n > 0]
    if len(distinct) >= 3 and top_n < sum(counts.values()) * 0.5:
        top_theme = "decor_mixed"
    total = sum(counts.values())
    conf = "HIGH" if top_n >= 3 and top_n >= total * 0.5 else ("LOW" if total == 1 else "MEDIUM")
    return {
        "theme": top_theme,
        "confidence": conf,
        "histogram": dict(counts),
        "attested_item_count": total,
    }


def evaluate_floor_activity(
    *,
    build_or_buy_mode: bool = False,
    active_story: object = None,
    stories_touched: Sequence[object] | None = None,
    floor_items: Sequence[Mapping] | None = None,
    player_directed: bool = False,
    lot_model: Mapping | None = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Classify Build Mode floor activity. Library-only; execute_allowed false."""
    cfg = cfg or load_contract()
    if player_directed:
        return {
            "state": "YIELD_TO_PLAYER",
            "activity_span": "UNKNOWN_SPAN",
            "active_story": "UNKNOWN_STORY",
            "floors": {},
            "optimize_hints": [],
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if not build_or_buy_mode:
        return {
            "state": "BUILD_FLOOR_ACTIVITY_SKIPPED",
            "reason": "NOT_BUILD_OR_BUY_MODE",
            "activity_span": "UNKNOWN_SPAN",
            "active_story": "UNKNOWN_STORY",
            "floors": {},
            "optimize_hints": [],
            "execute_allowed": False,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    active = _story(active_story)
    items = _normalize_items(floor_items)
    touched = {_story(s) for s in (stories_touched or [])}
    touched.discard("UNKNOWN_STORY")
    for item in items:
        if item["story"] in KNOWN_STORIES:
            touched.add(item["story"])
    if active in KNOWN_STORIES:
        touched.add(active)

    if len(touched) >= 2:
        span = "MULTI_FLOOR"
    elif len(touched) == 1:
        span = "SINGLE_FLOOR"
    else:
        span = "UNKNOWN_SPAN"

    floors: dict[str, dict] = {}
    for story in sorted(touched | ({active} if active in KNOWN_STORIES else set())):
        cats = [i["category"] for i in items if i["story"] == story]
        theme_row = theme_from_categories(cats, cfg)
        hints = list((cfg.get("theme_optimize_hints") or {}).get(theme_row["theme"]) or [])
        floors[story] = {
            "story": story,
            "is_active": story == active,
            "item_ids": [i["id"] for i in items if i["story"] == story],
            **theme_row,
            "optimize_category_hints": hints,
        }

    active_floor = floors.get(active) if active in floors else None
    optimize_hints = list((active_floor or {}).get("optimize_category_hints") or [])

    result = {
        "state": "BUILD_FLOOR_ACTIVITY_EVALUATED",
        "architecture": "FLOOR_ACTIVITY_CENSUS",
        "activity_span": span,
        "active_story": active,
        "stories_touched": sorted(touched),
        "floors": floors,
        "active_theme": (active_floor or {}).get("theme", "unknown"),
        "optimize_hints": optimize_hints,
        "attested_item_count": len(items),
        "execute_allowed": False,
        "proof_ceiling": cfg["proof_ceiling"],
        "next": (
            "Advisory only — feed optimize_hints into build_optimize pools when operator requests; "
            "do not place or mutate without separate admission."
        ),
    }
    if lot_model is not None:
        # P124: attach a projection of the existing house_state owner, not a new scan daemon.
        from betterinstincts.room_census import (
            RoomCensusError, scan_lot_model, summarize_for_listener,
        )
        try:
            result["room_census"] = summarize_for_listener(scan_lot_model(lot_model))
        except RoomCensusError as exc:
            raise BuildFloorActivityError(str(exc)) from exc
    return result
