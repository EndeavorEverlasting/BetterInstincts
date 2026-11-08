"""Build/Buy yield microsystem — per-category best-value pools (P95 + P124).

Deterministic ranking of attested catalog items by environment, neighborhood
eco footprint, and bill (power/water) axes. Evaluate-only — never SendInput,
never mutates saves. Aesthetics never rank.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-optimize.v1.json"
MAX_BYTES = 512_000
OBJECTIVES = frozenset({
    "MAXIMIZE_ENV",
    "MAXIMIZE_GREEN",
    "MAXIMIZE_INDUSTRIAL",
    "BALANCED_ENV_GREEN",
    "MAXIMIZE_YIELD",
    "MAXIMIZE_BILL_SAVINGS",
})
ATTESTED = frozenset({"LOCAL_OBSERVED", "OPERATOR_ATTESTED"})
AXIS_FIELDS = frozenset({
    "lot_environment_gain",
    "eco_footprint_green",
    "eco_footprint_industrial",
    "bill_power",
    "bill_water",
})


class BuildOptimizeError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise BuildOptimizeError("BUILD_OPTIMIZE_CONTRACT_UNSAFE")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.build-optimize/v1":
        raise BuildOptimizeError("INVALID_BUILD_OPTIMIZE_SCHEMA")
    if not isinstance(data.get("catalog"), list) or not data["catalog"]:
        raise BuildOptimizeError("EMPTY_BUILD_CATALOG")
    if not OBJECTIVES.issubset(data.get("objectives", {})):
        raise BuildOptimizeError("OBJECTIVES_INCOMPLETE")
    if not isinstance(data.get("value_axes"), dict) or not data["value_axes"]:
        raise BuildOptimizeError("VALUE_AXES_MISSING")
    if not isinstance(data.get("categories"), dict) or not data["categories"]:
        raise BuildOptimizeError("CATEGORIES_MISSING")
    return data


def _norm(token: str) -> str:
    return (
        token.strip()
        .lower()
        .replace("&", "and")
        .replace(" ", "_")
        .replace("-", "_")
    )


def resolve_item(token: str, catalog: Sequence[Mapping[str, object]]) -> Optional[dict]:
    key = _norm(token)
    for row in catalog:
        rid = _norm(str(row["id"]))
        name = _norm(str(row["name"]))
        aliases = {_norm(str(a)) for a in row.get("aliases", [])}
        short = rid.split(".", 1)[-1]
        if key in {rid, name, short} | aliases:
            return dict(row)
    return None


def _has_axis(row: Mapping[str, object], axis: str) -> bool:
    return axis in row and row[axis] is not None


def _stat(row: Mapping[str, object], key: str, *, require: bool = False) -> int:
    if not _has_axis(row, key):
        if require:
            raise BuildOptimizeError("AXIS_NOT_PRESENT:" + key)
        return 0
    raw = row[key]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise BuildOptimizeError("INVALID_STAT:" + key)
    return int(raw)


def _combined_env_green(row: Mapping[str, object]) -> int:
    env = _stat(row, "lot_environment_gain")
    green = _stat(row, "eco_footprint_green")
    return env + green + (env * green)


def _combined_bill_burden(row: Mapping[str, object]) -> Optional[int]:
    """Sum of declared bill axes; None if neither power nor water is declared."""
    has_p = _has_axis(row, "bill_power")
    has_w = _has_axis(row, "bill_water")
    if not has_p and not has_w:
        return None
    return _stat(row, "bill_power") + _stat(row, "bill_water")


def _primary_score(
    row: Mapping[str, object], objective: str, cfg: Mapping[str, object]
) -> Optional[int]:
    primary = cfg["objectives"][objective]["primary"]
    if primary == "combined_env_green":
        return _combined_env_green(row)
    if primary == "combined_bill_burden":
        return _combined_bill_burden(row)
    if primary in AXIS_FIELDS:
        if not _has_axis(row, primary):
            return None
        return _stat(row, primary, require=True)
    raise BuildOptimizeError("UNKNOWN_PRIMARY:" + str(primary))


def _axis_sort_value(row: Mapping[str, object], axis: str, cfg: Mapping[str, object]) -> Optional[int]:
    """Return comparable score for an axis (higher always better after transform)."""
    axes = cfg["value_axes"]
    if axis == "combined_env_green":
        return _combined_env_green(row)
    if axis == "combined_bill_burden":
        burden = _combined_bill_burden(row)
        if burden is None:
            return None
        return -burden
    if axis not in axes:
        raise BuildOptimizeError("UNKNOWN_AXIS:" + axis)
    if not _has_axis(row, axis):
        return None
    raw = _stat(row, axis, require=True)
    direction = axes[axis].get("direction", "higher")
    if direction == "higher":
        return raw
    if direction == "lower":
        return -raw
    raise BuildOptimizeError("UNKNOWN_AXIS_DIRECTION:" + str(direction))


def _excluded(row: Mapping[str, object], objective: str, cfg: Mapping[str, object]) -> bool:
    exclude = cfg["objectives"][objective].get("exclude_eco")
    if exclude == "industrial" and _stat(row, "eco_footprint_industrial") > 0:
        return True
    if exclude == "green" and _stat(row, "eco_footprint_green") > 0:
        return True
    return False


def _cost_key(row: Mapping[str, object]) -> int:
    cost = row.get("cost")
    if cost is None:
        return 10**9
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
        raise BuildOptimizeError("INVALID_COST:" + str(row.get("id")))
    return int(cost)


def _secondary_tuple(
    row: Mapping[str, object], objective: str, cfg: Mapping[str, object]
) -> tuple:
    keys: list = []
    for token in cfg["objectives"][objective].get("secondary", []):
        if token == "cost_asc":
            keys.append(_cost_key(row))
        elif token == "name_asc":
            keys.append(str(row.get("name") or ""))
        elif token == "bill_power_asc":
            keys.append(_stat(row, "bill_power") if _has_axis(row, "bill_power") else 10**9)
        elif token == "bill_water_asc":
            keys.append(_stat(row, "bill_water") if _has_axis(row, "bill_water") else 10**9)
        elif token in AXIS_FIELDS:
            keys.append(-_stat(row, token))
        else:
            raise BuildOptimizeError("UNKNOWN_SECONDARY:" + str(token))
    return tuple(keys)


def _pack_allowed(
    item: Mapping[str, object], packs: Optional[set], cfg: Mapping[str, object]
) -> bool:
    pack = str(item.get("pack") or "base")
    if packs is None:
        return True
    if pack in packs:
        return True
    if (
        cfg.get("policies", {}).get("include_unknown_pack_when_operator_attested")
        and pack == "unknown"
        and str(item.get("evidence_state") or "") in ATTESTED
    ):
        return True
    return False


def filter_catalog(
    *,
    category: Optional[str] = None,
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    cfg: Optional[dict] = None,
) -> list[dict]:
    cfg = cfg or load_contract()
    packs = set(owned_packs) if owned_packs is not None else None
    out: list[dict] = []
    for row in cfg["catalog"]:
        item = dict(row)
        if category and item.get("category") != category:
            continue
        if not _pack_allowed(item, packs, cfg):
            continue
        if budget is not None:
            if isinstance(budget, bool) or not isinstance(budget, (int, float)) or budget < 0:
                raise BuildOptimizeError("INVALID_BUDGET")
            cost = item.get("cost")
            if cost is not None and float(cost) > float(budget):
                continue
        out.append(item)
    return out


def rank_items(
    objective: str,
    *,
    category: Optional[str] = None,
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    limit: int = 5,
    cfg: Optional[dict] = None,
) -> list[dict]:
    """Return ranked catalog rows for an objective (best first)."""
    cfg = cfg or load_contract()
    if objective not in OBJECTIVES:
        raise BuildOptimizeError("UNKNOWN_OBJECTIVE:" + objective)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 50:
        raise BuildOptimizeError("INVALID_LIMIT")
    candidates = []
    for row in filter_catalog(
        category=category, owned_packs=owned_packs, budget=budget, cfg=cfg
    ):
        if _excluded(row, objective, cfg):
            continue
        score = _primary_score(row, objective, cfg)
        if score is None:
            continue
        # Bill savings: lower burden is better — rank by negated burden as score.
        if cfg["objectives"][objective]["primary"] == "combined_bill_burden":
            rank_score = -int(score)
        else:
            rank_score = int(score)
            if rank_score <= 0 and objective != "MAXIMIZE_BILL_SAVINGS":
                continue
        secondary = _secondary_tuple(row, objective, cfg)
        candidates.append((rank_score, secondary, row, score))
    candidates.sort(key=lambda t: (-t[0], t[1]))
    ranked = []
    for rank_score, _secondary, row, raw_score in candidates[:limit]:
        entry = dict(row)
        entry["objective_score"] = rank_score if cfg["objectives"][objective]["primary"] != "combined_bill_burden" else -int(raw_score)
        if cfg["objectives"][objective]["primary"] == "combined_bill_burden":
            entry["objective_score"] = -int(raw_score)  # higher = more savings
            entry["bill_burden"] = int(raw_score)
        entry["projected_panels"] = None
        ranked.append(entry)
    return ranked


def rank_axis(
    axis: str,
    *,
    category: Optional[str] = None,
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    limit: int = 3,
    exclude_industrial_from_green: bool = True,
    cfg: Optional[dict] = None,
) -> list[dict]:
    """Rank items on one value axis (higher transformed score first)."""
    cfg = cfg or load_contract()
    if axis not in cfg["value_axes"] and axis != "combined_bill_burden":
        raise BuildOptimizeError("UNKNOWN_AXIS:" + axis)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 50:
        raise BuildOptimizeError("INVALID_LIMIT")
    candidates = []
    for row in filter_catalog(
        category=category, owned_packs=owned_packs, budget=budget, cfg=cfg
    ):
        if exclude_industrial_from_green and axis in {
            "eco_footprint_green",
            "combined_env_green",
        }:
            if _stat(row, "eco_footprint_industrial") > 0:
                continue
        value = _axis_sort_value(row, axis, cfg)
        if value is None:
            continue
        # Yield-first tie breaks: prefer the other Env/Green contribution, then cost/name.
        tie_green = -_stat(row, "eco_footprint_green")
        tie_env = -_stat(row, "lot_environment_gain")
        candidates.append(
            (value, tie_green, tie_env, _cost_key(row), str(row.get("name") or ""), row)
        )
    candidates.sort(key=lambda t: (-t[0], t[1], t[2], t[3], t[4]))
    out = []
    for value, _g, _e, _cost, _name, row in candidates[:limit]:
        entry = dict(row)
        entry["axis"] = axis
        entry["axis_score"] = value
        out.append(entry)
    return out


def best_pools(
    *,
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    pool_size: Optional[int] = None,
    categories: Optional[Sequence[str]] = None,
    axes: Optional[Sequence[str]] = None,
    cfg: Optional[dict] = None,
) -> dict:
    """Per-category pools of best items for each value axis.

    Terminal microsystem value: a chooser pool so host/automation can pick the
    highest-yield attested covering/object without aesthetic ranking.
    """
    cfg = cfg or load_contract()
    size = pool_size if pool_size is not None else int(cfg["policies"]["pool_size_default"])
    if not isinstance(size, int) or isinstance(size, bool) or size < 1 or size > 20:
        raise BuildOptimizeError("INVALID_POOL_SIZE")
    cat_ids = list(categories) if categories is not None else list(cfg["categories"].keys())
    axis_ids = list(axes) if axes is not None else list(cfg["policies"]["pool_axes_default"])
    pools: dict = {}
    for cat in cat_ids:
        if cat not in cfg["categories"]:
            raise BuildOptimizeError("UNKNOWN_CATEGORY:" + cat)
        cat_axes = axis_ids
        primary = cfg["categories"][cat].get("primary_axes") or axis_ids
        # Prefer category primary axes, still allow requested axes that apply.
        ordered_axes = []
        for a in list(primary) + [x for x in axis_ids if x not in primary]:
            if a in axis_ids and a not in ordered_axes:
                ordered_axes.append(a)
        cat_pool: dict = {}
        for axis in ordered_axes:
            ranked = rank_axis(
                axis,
                category=cat,
                owned_packs=owned_packs,
                budget=budget,
                limit=size,
                cfg=cfg,
            )
            if ranked:
                cat_pool[axis] = [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "axis_score": r["axis_score"],
                        "lot_environment_gain": r.get("lot_environment_gain"),
                        "eco_footprint_green": r.get("eco_footprint_green"),
                        "eco_footprint_industrial": r.get("eco_footprint_industrial"),
                        "bill_power": r.get("bill_power"),
                        "bill_water": r.get("bill_water"),
                        "evidence_state": r.get("evidence_state"),
                        "pack": r.get("pack"),
                    }
                    for r in ranked
                ]
        if cat_pool:
            pools[cat] = cat_pool
    return {
        "schema": "betterinstincts.build-yield-pools/v1",
        "pool_size": size,
        "ranking_priority": cfg["policies"]["ranking_priority"],
        "categories": pools,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def project_stack(
    item: Mapping[str, object],
    *,
    panels: int,
    objective: str,
    cfg: Optional[dict] = None,
) -> dict:
    """Project stacked contribution for wall panels (or placed instances)."""
    cfg = cfg or load_contract()
    if objective not in OBJECTIVES:
        raise BuildOptimizeError("UNKNOWN_OBJECTIVE:" + objective)
    if not isinstance(panels, int) or isinstance(panels, bool) or panels < 1 or panels > 10_000:
        raise BuildOptimizeError("INVALID_PANELS")
    env = _stat(item, "lot_environment_gain") * panels
    green = _stat(item, "eco_footprint_green") * panels
    industrial = _stat(item, "eco_footprint_industrial") * panels
    score = _primary_score(item, objective, cfg)
    primary_total = (score or 0) * panels
    return {
        "item_id": item.get("id"),
        "panels": panels,
        "lot_environment_gain_total": env,
        "eco_footprint_green_total": green,
        "eco_footprint_industrial_total": industrial,
        "objective_score_total": primary_total,
        "stacking": cfg["policies"]["stacking"],
    }


def evaluate_category_pools(
    *,
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    pool_size: Optional[int] = None,
    player_directed: bool = False,
    build_or_buy_mode: bool = True,
    capture_ref: str = "capture:build-yield-pools",
) -> dict:
    """Evaluate-only microsystem receipt: full per-category best pools."""
    cfg = load_contract()
    if player_directed:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "YIELD_TO_PLAYER",
            "pools": None,
            "gate": "PLAYER_FIRST",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if not build_or_buy_mode:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "BUILD_OR_BUY_REQUIRED",
            "pools": None,
            "gate": "ENTER_BUILD_OR_BUY",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    pools = best_pools(
        owned_packs=owned_packs,
        budget=budget,
        pool_size=pool_size,
        cfg=cfg,
    )
    if not pools["categories"]:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "ABSTAIN_NO_ELIGIBLE_ITEMS",
            "pools": pools,
            "plan": None,
            "gate": "EXPAND_PACKS_OR_CATALOG",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    # Summarize top yield pick per category for quick host consumption.
    summary = []
    for cat, axes in pools["categories"].items():
        preferred = axes.get("combined_env_green") or axes.get("lot_environment_gain") or next(
            iter(axes.values()), []
        )
        if preferred:
            summary.append({
                "category": cat,
                "best_id": preferred[0]["id"],
                "best_name": preferred[0]["name"],
                "axis": preferred[0].get("axis") or (
                    "combined_env_green" if "combined_env_green" in axes else next(iter(axes))
                ),
            })
    return {
        "schema": "betterinstincts.build-optimize-result/v1",
        "state": "BUILD_YIELD_POOLS_READY",
        "microsystem": "BUILD_YIELD",
        "pools": pools,
        "category_summary": summary,
        "plan": {
            "action": "SELECT_FROM_CATEGORY_BEST_POOLS",
            "execute_allowed": False,
            "steps": [
                "Confirm disposable lab lot and HOST_MAY_AUTOMATE",
                "For each needed category, open tray and pick from pool (yield over aesthetics)",
                "Prefer combined_env_green / bill-efficient heads of each pool",
                "Capture tooltip receipts to promote SYNTHETIC_FLOOR rows to LOCAL_OBSERVED",
            ],
            "forbidden": [
                "SENDINPUT_WITHOUT_SESSION",
                "TOUCH_USER_SAVES",
                "RESUME",
                "FORCE_MODE_WHILE_PLAYER_PLAYING",
                "RANK_BY_AESTHETICS",
            ],
        },
        "gate": "BUILD_OPTIMIZE_EVALUATE_ONLY",
        "disposition": "OPTIMIZE",
        "capture_ref": capture_ref,
        "proof_ceiling": cfg["proof_ceiling"],
    }


def evaluate_build_optimize(
    objective: Optional[str] = None,
    *,
    category: Optional[str] = "wall_covering",
    owned_packs: Optional[Sequence[str]] = None,
    budget: Optional[float] = None,
    panels: int = 1,
    limit: int = 5,
    player_directed: bool = False,
    build_or_buy_mode: bool = True,
    include_pools: bool = False,
    pool_size: Optional[int] = None,
    capture_ref: str = "capture:build-optimize",
) -> dict:
    """Evaluate-only plan: best catalog picks + optional category pools."""
    cfg = load_contract()
    obj = objective or cfg["policies"]["default_household_objective"]
    if player_directed:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "YIELD_TO_PLAYER",
            "objective": obj,
            "picks": [],
            "pools": None,
            "plan": None,
            "gate": "PLAYER_FIRST",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if not build_or_buy_mode:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "BUILD_OR_BUY_REQUIRED",
            "objective": obj,
            "picks": [],
            "pools": None,
            "plan": None,
            "gate": "ENTER_BUILD_OR_BUY",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    pools = None
    if include_pools:
        pools = best_pools(
            owned_packs=owned_packs,
            budget=budget,
            pool_size=pool_size,
            cfg=cfg,
        )

    ranked = rank_items(
        obj,
        category=category,
        owned_packs=owned_packs,
        budget=budget,
        limit=limit,
        cfg=cfg,
    )
    if not ranked:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "ABSTAIN_NO_ELIGIBLE_ITEMS",
            "objective": obj,
            "picks": [],
            "pools": pools,
            "plan": None,
            "gate": "EXPAND_PACKS_OR_CATALOG",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
            "benefit": cfg["objectives"][obj]["benefit"],
        }

    best = ranked[0]
    projection = project_stack(best, panels=panels, objective=obj, cfg=cfg)
    for row in ranked:
        row["projected"] = project_stack(row, panels=panels, objective=obj, cfg=cfg)

    plan = {
        "action": "SELECT_AND_APPLY_BEST_CATALOG_ITEM",
        "item_id": best["id"],
        "item_name": best["name"],
        "category": best["category"],
        "technique": cfg["policies"]["apply_technique_note"],
        "steps": [
            "Confirm disposable lab lot and HOST_MAY_AUTOMATE",
            "Enter Build/Buy if needed (do not Esc — opens MENU)",
            f"Open tray for category {best['category']}",
            f"Select catalog item {best['name']}",
            "Shift+click to apply whole room/exterior when wall_covering",
            "Capture tooltip/receipt proving applied stats",
        ],
        "execute_allowed": False,
        "forbidden": [
            "SENDINPUT_WITHOUT_SESSION",
            "TOUCH_USER_SAVES",
            "RESUME",
            "FORCE_MODE_WHILE_PLAYER_PLAYING",
            "RANK_BY_AESTHETICS",
        ],
    }
    return {
        "schema": "betterinstincts.build-optimize-result/v1",
        "state": "BUILD_OPTIMIZE_PLAN_READY",
        "microsystem": "BUILD_YIELD",
        "objective": obj,
        "picks": ranked,
        "pools": pools,
        "best": {
            "id": best["id"],
            "name": best["name"],
            "category": best.get("category"),
            "objective_score": best["objective_score"],
            "lot_environment_gain": _stat(best, "lot_environment_gain"),
            "eco_footprint_green": _stat(best, "eco_footprint_green"),
            "eco_footprint_industrial": _stat(best, "eco_footprint_industrial"),
            "bill_power": best.get("bill_power"),
            "bill_water": best.get("bill_water"),
            "pack": best.get("pack"),
            "evidence_state": best.get("evidence_state"),
        },
        "projection": projection,
        "plan": plan,
        "gate": "BUILD_OPTIMIZE_EVALUATE_ONLY",
        "disposition": "OPTIMIZE",
        "benefit": cfg["objectives"][obj]["benefit"],
        "capture_ref": capture_ref,
        "proof_ceiling": cfg["proof_ceiling"],
    }
