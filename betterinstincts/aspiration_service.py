"""Aspiration microsystem — sticky dialog judgment beside need/career services.

Evaluate-only peer. Judges OK/Cancel for aspiration and life-state prompts.
When aspiration_completion_enabled is false (lab default), always Cancel.
Never mutates life state, never daemons, never claims occult certification.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "aspiration-service.v1.json"
ACTIVE_STATES = frozenset(
    {
        "TRACKING",
        "DISABLED_REFUSE",
        "JUDGING",
        "READY_CANCEL",
        "READY_OK",
        "YIELDED",
    }
)
LIFE_STATE_CLASSES = frozenset({"life_state_mutation", "timed_charm_initiation"})


class AspirationServiceError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise AspirationServiceError("UNSAFE_ASPIRATION_SERVICE_CONTRACT")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AspirationServiceError("INVALID_ASPIRATION_SERVICE_JSON") from exc
    if data.get("schema") != "betterinstincts.aspiration-service/v1":
        raise AspirationServiceError("INVALID_ASPIRATION_SERVICE_SCHEMA")
    if "catalogued_prompts" not in data:
        raise AspirationServiceError("ASPIRATION_CATALOG_MISSING")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_prompt(
    *,
    prompt_id: Optional[str] = None,
    prompt_text: str = "",
    cfg: Optional[dict] = None,
) -> Optional[dict]:
    """Match a catalogued aspiration / life-state prompt. Fail closed on unknown."""
    cfg = cfg or load_contract()
    catalog = cfg.get("catalogued_prompts") or {}
    if prompt_id and prompt_id in catalog:
        row = dict(catalog[prompt_id])
        row["prompt_id"] = prompt_id
        return row
    hay = _norm(prompt_text)
    if not hay:
        return None
    for pid, row in catalog.items():
        tokens = [_norm(t) for t in (row.get("narrative_tokens") or [])]
        hits = sum(1 for t in tokens if t and t in hay)
        # Require at least two independent narrative cues (scene intelligence).
        if hits >= 2:
            matched = dict(row)
            matched["prompt_id"] = pid
            matched["token_hits"] = hits
            return matched
    return None


def should_attach_aspiration_service(
    *,
    aspiration_prompt_active: bool = False,
    prompt_id: Optional[str] = None,
    prompt_text: str = "",
    prior_state: Optional[Mapping[str, object]] = None,
    force: bool = False,
) -> bool:
    if force:
        return True
    prior = prior_state or {}
    if prior.get("prompt_held") and prior.get("microsystem_state") in ACTIVE_STATES:
        return True
    if aspiration_prompt_active:
        return True
    if prompt_id or prompt_text:
        return match_prompt(prompt_id=prompt_id, prompt_text=prompt_text) is not None
    return False


def _prior_prompt(prior_state: Optional[Mapping[str, object]]) -> Optional[dict]:
    if not isinstance(prior_state, Mapping):
        return None
    if not prior_state.get("prompt_held"):
        return None
    prompt = prior_state.get("prompt")
    if not isinstance(prompt, Mapping):
        return None
    return {
        "prompt_id": str(prompt.get("prompt_id") or ""),
        "prompt_class": str(prompt.get("prompt_class") or "aspiration_milestone"),
        "title": str(prompt.get("title") or ""),
        "source": str(prompt.get("source") or "prior_aspiration_service"),
    }


def compact_aspiration_service(report: dict, *, max_actions: int = 4) -> dict:
    """Listener/tandem-safe summary."""
    return {
        "schema": report.get("schema"),
        "state": report.get("state"),
        "capture_ref": report.get("capture_ref"),
        "gate": report.get("gate"),
        "action": report.get("action"),
        "microsystem_state": report.get("microsystem_state"),
        "prompt_held": report.get("prompt_held"),
        "prompt": report.get("prompt"),
        "dialog_choice": report.get("dialog_choice"),
        "press_ok_allowed": report.get("press_ok_allowed"),
        "aspiration_completion_enabled": report.get("aspiration_completion_enabled"),
        "primary_route": report.get("primary_route"),
        "next_actions": list(report.get("next_actions") or [])[:max_actions],
        "findings": list(report.get("findings") or []),
        "architecture": report.get("architecture"),
        "proof_ceiling": report.get("proof_ceiling"),
        "compacted": True,
    }


def evaluate_aspiration_service(
    *,
    aspiration_prompt_active: bool = False,
    prompt_id: Optional[str] = None,
    prompt_text: str = "",
    aspiration_completion_enabled: bool = False,
    occult_needs_engine_ready: bool = False,
    player_directed: bool = False,
    already_busy: bool = False,
    operator_prefers_ok: Optional[bool] = None,
    prior_state: Optional[Mapping[str, object]] = None,
    capture_ref: str = "capture:aspiration-service",
) -> dict:
    """Evaluate aspiration microsystem for one observation; preserve sticky prompt.

    Lab/host default: aspiration_completion_enabled=False (Cancel life-state).
    Product default documented in contract as True for end users.
    """
    cfg = load_contract()
    findings: list[str] = []
    prior_prompt = _prior_prompt(prior_state)
    matched = match_prompt(prompt_id=prompt_id, prompt_text=prompt_text, cfg=cfg)

    if not aspiration_prompt_active and matched is None and prior_prompt is None:
        return {
            "schema": "betterinstincts.aspiration-service-result/v1",
            "state": "ASPIRATION_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "ASPIRATION_IDLE",
            "action": cfg["call_stack"]["gates"]["ASPIRATION_IDLE"]["action"],
            "microsystem_state": "IDLE",
            "prompt_held": False,
            "prompt": None,
            "dialog_choice": None,
            "press_ok_allowed": False,
            "aspiration_completion_enabled": bool(aspiration_completion_enabled),
            "primary_route": None,
            "next_actions": [],
            "findings": ["ASPIRATION_IDLE_NO_PROMPT"],
            "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
        }

    # Explicit clear: dialog no longer active and no match.
    if (
        not aspiration_prompt_active
        and matched is None
        and prior_prompt is not None
        and prior_state
        and prior_state.get("prompt_held")
    ):
        findings.append("ASPIRATION_PROMPT_CLEARED_EXPLICIT_COMPLETE")
        return {
            "schema": "betterinstincts.aspiration-service-result/v1",
            "state": "ASPIRATION_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "ASPIRATION_COMPLETE",
            "action": cfg["call_stack"]["gates"]["ASPIRATION_COMPLETE"]["action"],
            "microsystem_state": "COMPLETE",
            "prompt_held": False,
            "prompt": None,
            "dialog_choice": None,
            "press_ok_allowed": False,
            "aspiration_completion_enabled": bool(aspiration_completion_enabled),
            "primary_route": None,
            "next_actions": [],
            "findings": sorted(set(findings)),
            "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
        }

    if matched is None and prior_prompt is not None:
        # Carry sticky identity; class from prior.
        matched = {
            "prompt_id": prior_prompt["prompt_id"],
            "prompt_class": prior_prompt["prompt_class"],
            "title": prior_prompt.get("title") or "",
            "default_when_disabled": "cancel",
            "default_when_unknown": "cancel",
        }
        findings.append("ASPIRATION_PROMPT_CARRIED_FROM_PRIOR")
    elif matched is None and aspiration_prompt_active:
        # Active but uncatalogued — fail closed for life-state risk.
        findings.append("ASPIRATION_PROMPT_UNKNOWN_FAIL_CLOSED")
        findings.append("ASPIRATION_PROMPT_HELD")
        unknown_prompt = {
            "prompt_id": prompt_id or "unknown.aspiration.dialog",
            "prompt_class": "life_state_mutation",
            "title": "Unknown aspiration dialog",
            "source": "unknown",
            "life_state_mutation": True,
        }
        if player_directed or already_busy:
            return {
                "schema": "betterinstincts.aspiration-service-result/v1",
                "state": "ASPIRATION_SERVICE_EVALUATED",
                "capture_ref": capture_ref,
                "gate": "PLAYER_FIRST_OR_BUSY",
                "action": cfg["call_stack"]["gates"]["PLAYER_FIRST_OR_BUSY"]["action"],
                "microsystem_state": "YIELDED",
                "prompt_held": True,
                "prompt": unknown_prompt,
                "dialog_choice": None,
                "press_ok_allowed": False,
                "aspiration_completion_enabled": bool(aspiration_completion_enabled),
                "primary_route": None,
                "next_actions": [],
                "findings": sorted(
                    set(findings + ["PLAYER_FIRST_PRESERVES_ASPIRATION_TRACKING"])
                ),
                "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
                "proof_ceiling": cfg["proof_ceiling"],
            }
        return _cancel_result(
            cfg,
            capture_ref=capture_ref,
            prompt=unknown_prompt,
            enabled=bool(aspiration_completion_enabled),
            microsystem_state="READY_CANCEL",
            gate="ASPIRATION_JUDGE_CANCEL",
            findings=findings,
            action_key="ASPIRATION_JUDGE_CANCEL",
        )

    assert matched is not None
    prompt_class = str(matched.get("prompt_class") or "aspiration_milestone")
    classes = cfg.get("prompt_classes") or {}
    class_meta = classes.get(prompt_class) or {}
    is_life_state = bool(
        class_meta.get("life_state_mutation")
        or prompt_class in LIFE_STATE_CLASSES
    )
    prompt = {
        "prompt_id": matched.get("prompt_id"),
        "prompt_class": prompt_class,
        "title": matched.get("title") or "",
        "source": "catalog" if matched.get("narrative_tokens") else "observation",
        "life_state_mutation": is_life_state,
    }
    findings.append("ASPIRATION_PROMPT_HELD")

    if player_directed or already_busy:
        return {
            "schema": "betterinstincts.aspiration-service-result/v1",
            "state": "ASPIRATION_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "PLAYER_FIRST_OR_BUSY",
            "action": cfg["call_stack"]["gates"]["PLAYER_FIRST_OR_BUSY"]["action"],
            "microsystem_state": "YIELDED",
            "prompt_held": True,
            "prompt": prompt,
            "dialog_choice": None,
            "press_ok_allowed": False,
            "aspiration_completion_enabled": bool(aspiration_completion_enabled),
            "primary_route": None,
            "next_actions": [],
            "findings": sorted(set(findings + ["PLAYER_FIRST_PRESERVES_ASPIRATION_TRACKING"])),
            "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
        }

    if not aspiration_completion_enabled:
        findings.append("ASPIRATION_COMPLETION_DISABLED_CANCEL")
        return _cancel_result(
            cfg,
            capture_ref=capture_ref,
            prompt=prompt,
            enabled=False,
            microsystem_state="DISABLED_REFUSE",
            gate="ASPIRATION_COMPLETION_DISABLED",
            findings=findings,
        )

    if is_life_state and not occult_needs_engine_ready:
        findings.append("OCCULT_NEEDS_ENGINE_NOT_READY_CANCEL")
        return _cancel_result(
            cfg,
            capture_ref=capture_ref,
            prompt=prompt,
            enabled=True,
            microsystem_state="READY_CANCEL",
            gate="OCCULT_NEEDS_NOT_READY",
            findings=findings,
            action_key="OCCULT_NEEDS_NOT_READY",
        )

    # Enabled judgment: life-state OK only when operator explicitly prefers OK
    # and occult readiness already passed above. Ordinary milestones may OK.
    prefer_ok = operator_prefers_ok
    if prefer_ok is None:
        prefer_ok = not is_life_state
    if prefer_ok and not is_life_state:
        findings.append("ASPIRATION_MILESTONE_OK_ALLOWED")
        return {
            "schema": "betterinstincts.aspiration-service-result/v1",
            "state": "ASPIRATION_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "ASPIRATION_JUDGE_OK",
            "action": cfg["call_stack"]["gates"]["ASPIRATION_JUDGE_OK"]["action"],
            "microsystem_state": "READY_OK",
            "prompt_held": True,
            "prompt": prompt,
            "dialog_choice": "OK",
            "press_ok_allowed": True,
            "aspiration_completion_enabled": True,
            "primary_route": "PRESS_OK",
            "next_actions": [
                {
                    "action": "PRESS_OK",
                    "dialog_choice": "OK",
                    "prompt_id": prompt.get("prompt_id"),
                }
            ],
            "findings": sorted(set(findings)),
            "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
        }
    if prefer_ok and is_life_state and occult_needs_engine_ready:
        findings.append("LIFE_STATE_OK_WITH_OCCULT_READY")
        return {
            "schema": "betterinstincts.aspiration-service-result/v1",
            "state": "ASPIRATION_SERVICE_EVALUATED",
            "capture_ref": capture_ref,
            "gate": "ASPIRATION_JUDGE_OK",
            "action": cfg["call_stack"]["gates"]["ASPIRATION_JUDGE_OK"]["action"],
            "microsystem_state": "READY_OK",
            "prompt_held": True,
            "prompt": prompt,
            "dialog_choice": "OK",
            "press_ok_allowed": True,
            "aspiration_completion_enabled": True,
            "primary_route": "PRESS_OK",
            "next_actions": [
                {
                    "action": "PRESS_OK",
                    "dialog_choice": "OK",
                    "prompt_id": prompt.get("prompt_id"),
                }
            ],
            "findings": sorted(set(findings)),
            "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
            "proof_ceiling": cfg["proof_ceiling"],
        }

    findings.append("ASPIRATION_JUDGMENT_CANCEL")
    return _cancel_result(
        cfg,
        capture_ref=capture_ref,
        prompt=prompt,
        enabled=True,
        microsystem_state="READY_CANCEL",
        gate="ASPIRATION_JUDGE_CANCEL",
        findings=findings,
        action_key="ASPIRATION_JUDGE_CANCEL",
    )


def _cancel_result(
    cfg: dict,
    *,
    capture_ref: str,
    prompt: dict,
    enabled: bool,
    microsystem_state: str,
    gate: str,
    findings: Sequence[str],
    action_key: Optional[str] = None,
) -> dict:
    key = action_key or gate
    action = cfg["call_stack"]["gates"][key]["action"]
    return {
        "schema": "betterinstincts.aspiration-service-result/v1",
        "state": "ASPIRATION_SERVICE_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "microsystem_state": microsystem_state,
        "prompt_held": True,
        "prompt": prompt,
        "dialog_choice": "CANCEL",
        "press_ok_allowed": False,
        "aspiration_completion_enabled": bool(enabled),
        "primary_route": "PRESS_CANCEL",
        "next_actions": [
            {
                "action": "PRESS_CANCEL",
                "dialog_choice": "CANCEL",
                "prompt_id": prompt.get("prompt_id"),
            }
        ],
        "findings": sorted(set(findings)),
        "architecture": "ASPIRATION_MICROSYSTEM_TANDEM_BESIDE_NEEDS",
        "proof_ceiling": cfg["proof_ceiling"],
    }
