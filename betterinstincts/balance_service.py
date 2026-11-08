"""Balance/Imbalance microsystem — sticky wellness beside need services.

Evaluate-only peer to need_services / gardening / career / aspiration.
Tracks supplied Enchanted by Nature balance meter + ailments. Reuses
survival_critical (P124) — never invents meter readings, never daemons,
never claims pack certification.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

from betterinstincts.teen_homework import TeenHomeworkError, survival_critical

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "balance-service.v1.json"
ACTIVE_STATES = frozenset(
    {
        "TRACKING",
        "RECOVERING_NATURE",
        "AILMENT_ACTIVE",
        "READY_HOLISTIC_CURE",
        "READY_NATUROPATH",
        "SUSPENDED_FOR_SURVIVAL",
        "YIELDED",
    }
)
POSITIVE_EMOTIONS = frozenset(
    {"HAPPY", "PLAYFUL", "CONFIDENT", "FOCUSED", "INSPIRED", "FLIRTY", "ENERGIZED"}
)
NEGATIVE_EMOTIONS = frozenset(
    {"SAD", "ANGRY", "UNCOMFORTABLE", "TENSE", "STRESSED", "EMBARRASSED", "SCARED"}
)


class BalanceServiceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise BalanceServiceError("UNSAFE_BALANCE_SERVICE_CONTRACT")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BalanceServiceError("INVALID_BALANCE_SERVICE_JSON") from exc
    if data.get("schema") != "betterinstincts.balance-service/v1":
        raise BalanceServiceError("INVALID_BALANCE_SERVICE_SCHEMA")
    if "balance_levels" not in data or "ailments" not in data:
        raise BalanceServiceError("BALANCE_CATALOG_MISSING")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    return re.sub(r"_+", "_", s).strip("_")


def resolve_balance_level(raw: Optional[str], cfg: Optional[dict] = None) -> Optional[str]:
    """Map a supplied HUD/operator label to a catalogued balance level."""
    if raw is None or str(raw).strip() == "":
        return None
    cfg = cfg or load_contract()
    key = _norm(raw)
    levels = cfg.get("balance_levels") or {}
    if key in levels:
        return key
    for level_id, row in levels.items():
        aliases = {_norm(a) for a in (row.get("aliases") or [])}
        aliases.add(_norm(level_id))
        if key in aliases:
            return level_id
    return None


def resolve_ailment(raw: Optional[str], cfg: Optional[dict] = None) -> Optional[str]:
    """Map a supplied ailment label. Unknown tokens fail closed (None)."""
    if raw is None or str(raw).strip() == "":
        return None
    cfg = cfg or load_contract()
    key = _norm(raw)
    ailments = cfg.get("ailments") or {}
    if key in ailments:
        return key
    for ailment_id, row in ailments.items():
        aliases = {_norm(a) for a in (row.get("aliases") or [])}
        aliases.add(_norm(ailment_id))
        if key in aliases:
            return ailment_id
    return None


def should_attach_balance_service(
    *,
    balance_level: Optional[str] = None,
    ailment: Optional[str] = None,
    prior_state: Optional[Mapping[str, object]] = None,
    force: bool = False,
) -> bool:
    if force:
        return True
    prior = prior_state or {}
    if prior.get("condition_held") and prior.get("microsystem_state") in ACTIVE_STATES:
        return True
    cfg = load_contract()
    level = resolve_balance_level(balance_level, cfg)
    if level in {"imbalanced", "very_imbalanced"}:
        return True
    if resolve_ailment(ailment, cfg) is not None:
        return True
    return False


def _prior_condition(prior_state: Optional[Mapping[str, object]]) -> Optional[dict]:
    if not isinstance(prior_state, Mapping):
        return None
    if not prior_state.get("condition_held"):
        return None
    condition = prior_state.get("condition")
    if not isinstance(condition, Mapping):
        return None
    return {
        "balance_level": str(condition.get("balance_level") or ""),
        "ailment": (
            str(condition["ailment"]) if condition.get("ailment") else None
        ),
        "source": str(condition.get("source") or "prior_balance_service"),
        "resume_condition": str(
            condition.get("resume_condition") or "FRESH_SURVIVAL_GREEN_REVALIDATION"
        ),
    }


def _mood_bias(emotion: Optional[str]) -> str:
    if not emotion:
        return "UNKNOWN"
    key = str(emotion).strip().upper().replace(" ", "_").replace("-", "_")
    if key in POSITIVE_EMOTIONS:
        return "POSITIVE"
    if key in NEGATIVE_EMOTIONS:
        return "NEGATIVE"
    compact = key.replace("_", "")
    for name in POSITIVE_EMOTIONS:
        if name.replace("_", "") == compact:
            return "POSITIVE"
    for name in NEGATIVE_EMOTIONS:
        if name.replace("_", "") == compact:
            return "NEGATIVE"
    return "UNKNOWN"


def compact_balance_service(report: dict, *, max_actions: int = 4) -> dict:
    """Listener/tandem-safe summary."""
    return {
        "schema": report.get("schema"),
        "state": report.get("state"),
        "capture_ref": report.get("capture_ref"),
        "gate": report.get("gate"),
        "action": report.get("action"),
        "microsystem_state": report.get("microsystem_state"),
        "condition_held": report.get("condition_held"),
        "condition": report.get("condition"),
        "balance_level": report.get("balance_level"),
        "ailment": report.get("ailment"),
        "primary_route": report.get("primary_route"),
        "preferred_routes": list(report.get("preferred_routes") or [])[:8],
        "next_actions": list(report.get("next_actions") or [])[:max_actions],
        "findings": list(report.get("findings") or []),
        "mood_bias": report.get("mood_bias"),
        "architecture": report.get("architecture"),
        "proof_ceiling": report.get("proof_ceiling"),
        "compacted": True,
    }


def evaluate_balance_service(
    needs: Mapping[str, float],
    *,
    balance_level: Optional[str] = None,
    ailment: Optional[str] = None,
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    inventory_has_holistic_cure: Optional[bool] = None,
    apothecary_stall_available: bool = False,
    apothecary_skill_level: Optional[int] = None,
    natural_living_meditate_available: bool = False,
    houseplants_available: bool = False,
    available_objects: Sequence[str] = (),
    player_directed: bool = False,
    already_busy: bool = False,
    prior_state: Optional[Mapping[str, object]] = None,
    capture_ref: str = "capture:balance-service",
) -> dict:
    """Evaluate balance microsystem for one observation; preserve sticky condition.

    balance_level and ailment must be supplied (or carried from prior). Moodlets
    never invent a meter stage.
    """
    cfg = load_contract()
    findings: list[str] = []
    prior = _prior_condition(prior_state)
    level = resolve_balance_level(balance_level, cfg)
    ailment_id = resolve_ailment(ailment, cfg)
    mood_bias = _mood_bias(emotion)

    if level is None and prior is not None:
        level = resolve_balance_level(prior.get("balance_level"), cfg)
        findings.append("BALANCE_LEVEL_CARRIED_FROM_PRIOR")
    if ailment_id is None and prior is not None and prior.get("ailment"):
        ailment_id = resolve_ailment(str(prior.get("ailment")), cfg)
        if ailment_id:
            findings.append("BALANCE_AILMENT_CARRIED_FROM_PRIOR")

    # Explicit restore: Balanced (or missing) with no ailment clears sticky.
    if (level in {None, "balanced"}) and ailment_id is None:
        if prior is not None:
            findings.append("BALANCE_CONDITION_CLEARED_RESTORED")
            return {
                "schema": "betterinstincts.balance-service-result/v1",
                "state": "BALANCE_SERVICE_EVALUATED",
                "capture_ref": capture_ref,
                "gate": "BALANCE_RESTORED",
                "action": cfg["call_stack"]["gates"]["BALANCE_RESTORED"]["action"],
                "microsystem_state": "RESTORED",
                "condition_held": False,
                "condition": None,
                "balance_level": "balanced",
                "ailment": None,
                "primary_route": None,
                "preferred_routes": [],
                "next_actions": [],
                "findings": sorted(set(findings)),
                "mood_bias": mood_bias,
                "architecture": "BALANCE_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
                "proof_ceiling": cfg["proof_ceiling"],
                "resume_condition": None,
            }
        return {
            "schema": "betterinstincts.balance-service-result/v1",
            "state": "BALANCE_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "BALANCE_IDLE",
            "action": cfg["call_stack"]["gates"]["BALANCE_IDLE"]["action"],
            "microsystem_state": "IDLE",
            "condition_held": False,
            "condition": None,
            "balance_level": level,
            "ailment": None,
            "primary_route": None,
            "preferred_routes": [],
            "next_actions": [],
            "findings": ["BALANCE_IDLE_NO_CONDITION"],
            "mood_bias": mood_bias,
            "architecture": "BALANCE_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
            "resume_condition": None,
        }

    if level is None and ailment_id is not None:
        # Ailment without meter: treat as very_imbalanced per game rule.
        level = "very_imbalanced"
        findings.append("AILMENT_IMPLIES_VERY_IMBALANCED")

    assert level in {"imbalanced", "very_imbalanced"}
    if level == "very_imbalanced" and ailment_id is None:
        findings.append("VERY_IMBALANCED_WITHOUT_OBSERVED_AILMENT")
    if ailment_id and level != "very_imbalanced":
        # Catalog says physical ailments belong to Very Imbalanced.
        level = "very_imbalanced"
        findings.append("AILMENT_PROMOTES_VERY_IMBALANCED")

    condition = {
        "balance_level": level,
        "ailment": ailment_id,
        "source": "observation" if balance_level or ailment else "prior_balance_service",
        "resume_condition": "FRESH_SURVIVAL_GREEN_REVALIDATION",
    }
    findings.append("BALANCE_CONDITION_HELD")
    if mood_bias == "NEGATIVE":
        findings.append("NEGATIVE_MOOD_PRESSURES_IMBALANCE")
    elif mood_bias == "POSITIVE":
        findings.append("POSITIVE_MOOD_SUPPORTS_BALANCE")
    if moodlets:
        findings.append("MOODLETS_SUPPLIED_FOR_BALANCE_BIAS")

    plants = houseplants_available or any(
        "plant" in _norm(obj) or "flower" in _norm(obj) for obj in available_objects
    )
    skill_ok = (
        isinstance(apothecary_skill_level, int) and apothecary_skill_level >= 10
    )
    preferred: list[str] = []
    next_actions: list[dict] = []

    def _add_route(route: str, **extra: object) -> None:
        if route not in preferred:
            preferred.append(route)
        next_actions.append({"action": route, **extra})

    if inventory_has_holistic_cure is True:
        _add_route("CONSUME_HOLISTIC_CURE", inventory=True)
    if level == "very_imbalanced":
        _add_route("VISIT_NATUROPATH", panel="phone_home")
        if apothecary_stall_available:
            _add_route("PURCHASE_HOLISTIC_CURE", venue="sprucederry_grove")
        if skill_ok:
            _add_route("CRAFT_HOLISTIC_CURE", skill="apothecary", level=10)
    if plants:
        _add_route("WATER_OR_MAINTAIN_HOUSEPLANTS", peer="gardening_service")
    if natural_living_meditate_available:
        _add_route("MEDITATE_IN_NATURE", skill="natural_living")
    _add_route("SEEK_POSITIVE_MOOD", mood_bias=mood_bias)

    try:
        survival = survival_critical(needs)
    except TeenHomeworkError as exc:
        raise BalanceServiceError(str(exc)) from exc

    if player_directed or already_busy:
        microsystem_state = "YIELDED"
        gate = "PLAYER_FIRST_OR_BUSY"
        action = cfg["call_stack"]["gates"]["PLAYER_FIRST_OR_BUSY"]["action"]
        findings.append("PLAYER_FIRST_PRESERVES_BALANCE_TRACKING")
        primary = None
        preferred = []
        next_actions = []
    elif survival:
        microsystem_state = "SUSPENDED_FOR_SURVIVAL"
        gate = "SUSPENDED_FOR_SURVIVAL"
        action = cfg["call_stack"]["gates"]["SUSPENDED_FOR_SURVIVAL"]["action"]
        findings.append("SURVIVAL_SUSPENDS_BALANCE_ACTION_NOT_CONDITION")
        primary = None
        preferred = []
        next_actions = []
    elif inventory_has_holistic_cure is True and (
        level == "very_imbalanced" or ailment_id
    ):
        microsystem_state = "READY_HOLISTIC_CURE"
        gate = "READY_HOLISTIC_CURE"
        action = cfg["call_stack"]["gates"]["READY_HOLISTIC_CURE"]["action"]
        findings.append("HOLISTIC_CURE_READY")
        primary = "CONSUME_HOLISTIC_CURE"
    elif level == "very_imbalanced" and ailment_id:
        # Gate escalates to Naturopath; state records the active ailment.
        microsystem_state = "AILMENT_ACTIVE"
        gate = "READY_NATUROPATH"
        action = cfg["call_stack"]["gates"]["READY_NATUROPATH"]["action"]
        findings.append("AILMENT_ACTIVE_ESCALATE_NATUROPATH")
        if prior is not None:
            findings.append("BALANCE_RESUMED_AFTER_SURVIVAL_OR_CONTINUITY")
        primary = "VISIT_NATUROPATH"
    else:
        # Imbalanced, or Very Imbalanced without an observed ailment.
        microsystem_state = "RECOVERING_NATURE"
        gate = "RECOVERING_NATURE"
        action = cfg["call_stack"]["gates"]["RECOVERING_NATURE"]["action"]
        findings.append("NATURE_AND_MOOD_RECOVERY")
        if plants:
            primary = "WATER_OR_MAINTAIN_HOUSEPLANTS"
        elif natural_living_meditate_available:
            primary = "MEDITATE_IN_NATURE"
        else:
            primary = "SEEK_POSITIVE_MOOD"
        if level == "very_imbalanced" and not ailment_id:
            # Prefer Naturopath as a secondary without inventing an ailment.
            if "VISIT_NATUROPATH" not in preferred:
                preferred.insert(0, "VISIT_NATUROPATH")
                next_actions.insert(
                    0, {"action": "VISIT_NATUROPATH", "panel": "phone_home"}
                )

    condition_held = microsystem_state not in {"IDLE", "RESTORED", "COMPLETE"}
    return {
        "schema": "betterinstincts.balance-service-result/v1",
        "state": "BALANCE_SERVICE_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "microsystem_state": microsystem_state,
        "condition_held": condition_held,
        "condition": condition if condition_held else None,
        "balance_level": level if condition_held else None,
        "ailment": ailment_id if condition_held else None,
        "primary_route": primary,
        "preferred_routes": preferred,
        "next_actions": next_actions,
        "findings": sorted(set(findings)),
        "mood_bias": mood_bias,
        "survival_critical": list(survival),
        "architecture": "BALANCE_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
        "proof_ceiling": cfg["proof_ceiling"],
        "resume_condition": (
            condition.get("resume_condition") if condition_held else None
        ),
    }
