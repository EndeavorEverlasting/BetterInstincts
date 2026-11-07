"""Deterministic Build/Buy catalog ranking (P95 call-stack prototype).

Ranks wall coverings and Buy objects by Lot Environment Gain and Eco Footprint
objectives. Library is evaluate-only — never SendInput, never mutates saves.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "build-optimize.v1.json"
MAX_BYTES = 256_000
OBJECTIVES = frozenset({
    "MAXIMIZE_ENV",
    "MAXIMIZE_GREEN",
    "MAXIMIZE_INDUSTRIAL",
    "BALANCED_ENV_GREEN",
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


def _stat(row: Mapping[str, object], key: str) -> int:
    raw = row.get(key, 0)
    if raw is None:
        return 0
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise BuildOptimizeError("INVALID_STAT:" + key)
    return int(raw)


def _primary_score(row: Mapping[str, object], objective: str, cfg: Mapping[str, object]) -> int:
    obj = cfg["objectives"][objective]
    primary = obj["primary"]
    if primary == "combined_env_green":
        return _stat(row, "lot_environment_gain") + 2 * _stat(row, "eco_footprint_green")
    return _stat(row, primary)


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
        pack = str(item.get("pack") or "base")
        if packs is not None and pack not in packs:
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
        if score <= 0:
            continue
        candidates.append((score, _cost_key(row), str(row["name"]), row))
    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
    ranked = []
    for score, _cost, _name, row in candidates[:limit]:
        entry = dict(row)
        entry["objective_score"] = score
        entry["projected_panels"] = None
        ranked.append(entry)
    return ranked


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
    primary = _primary_score(item, objective, cfg) * panels
    return {
        "item_id": item.get("id"),
        "panels": panels,
        "lot_environment_gain_total": env,
        "eco_footprint_green_total": green,
        "eco_footprint_industrial_total": industrial,
        "objective_score_total": primary,
        "stacking": cfg["policies"]["stacking"],
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
    capture_ref: str = "capture:build-optimize",
) -> dict:
    """Evaluate-only plan: best catalog picks + stacking projection."""
    cfg = load_contract()
    obj = objective or cfg["policies"]["default_household_objective"]
    if player_directed:
        return {
            "schema": "betterinstincts.build-optimize-result/v1",
            "state": "YIELD_TO_PLAYER",
            "objective": obj,
            "picks": [],
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
            "plan": None,
            "gate": "ENTER_BUILD_OR_BUY",
            "disposition": "EMULATE",
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }

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
        ],
    }
    return {
        "schema": "betterinstincts.build-optimize-result/v1",
        "state": "BUILD_OPTIMIZE_PLAN_READY",
        "objective": obj,
        "picks": ranked,
        "best": {
            "id": best["id"],
            "name": best["name"],
            "objective_score": best["objective_score"],
            "lot_environment_gain": _stat(best, "lot_environment_gain"),
            "eco_footprint_green": _stat(best, "eco_footprint_green"),
            "eco_footprint_industrial": _stat(best, "eco_footprint_industrial"),
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
