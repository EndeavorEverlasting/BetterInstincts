"""Social opportunity safety — Sims-library occult lookup before invite OK.

Offline / host planning only. Never invents occult status. Unique library match
required; ambiguous or missing matches fail closed to Cancel/Abstain.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "social-opportunity.v1.json"
SAFE_OCCULT = frozenset({"HUMAN", "KNOWN_SAFE_NON_VAMPIRE"})
BLOCK_OCCULT = frozenset({"UNKNOWN", "VAMPIRE", "OTHER_OCCULT"})
VALID_OCCULT = frozenset(
    {"UNKNOWN", "HUMAN", "VAMPIRE", "OTHER_OCCULT", "KNOWN_SAFE_NON_VAMPIRE"}
)


class SocialOpportunityError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 256000:
        raise SocialOpportunityError("UNSAFE_SOCIAL_OPPORTUNITY_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.social-opportunity/v1":
        raise SocialOpportunityError("INVALID_SOCIAL_OPPORTUNITY_SCHEMA")
    if not data.get("sim_library"):
        raise SocialOpportunityError("SIM_LIBRARY_REQUIRED")
    return data


def _norm(text: str) -> str:
    s = str(text or "").strip().lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_occult(raw: Optional[str]) -> str:
    if raw is None or not str(raw).strip():
        return "UNKNOWN"
    token = str(raw).strip().upper().replace(" ", "_")
    aliases = {
        "NOT_VAMPIRE": "KNOWN_SAFE_NON_VAMPIRE",
        "SAFE": "KNOWN_SAFE_NON_VAMPIRE",
        "NON_VAMPIRE": "KNOWN_SAFE_NON_VAMPIRE",
        "NORMAL": "HUMAN",
        "SPELLCASTER": "OTHER_OCCULT",
        "WEREWOLF": "OTHER_OCCULT",
        "ALIEN": "OTHER_OCCULT",
        "MERMAID": "OTHER_OCCULT",
        "PLANTSIM": "OTHER_OCCULT",
    }
    token = aliases.get(token, token)
    if token not in VALID_OCCULT:
        raise SocialOpportunityError("INVALID_OCCULT_STATUS:" + token)
    return token


def lookup_sim_library(
    invitee_name: str,
    library: Sequence[Mapping[str, object]],
) -> dict:
    """Exact unique name match in the supplied Sims library. Never invents rows."""
    needle = _norm(invitee_name)
    if not needle:
        raise SocialOpportunityError("INVITEE_NAME_REQUIRED")
    hits: list[dict] = []
    for row in library:
        if not isinstance(row, Mapping):
            continue
        name = _norm(str(row.get("name") or row.get("sim_name") or ""))
        if not name or name != needle:
            continue
        occult = _norm_occult(
            str(row["occult_status"]) if row.get("occult_status") is not None else None
        )
        hits.append(
            {
                "name": str(row.get("name") or row.get("sim_name")),
                "occult_status": occult,
                "sim_id": row.get("sim_id"),
                "source": row.get("source") or "sim_library",
            }
        )
    if not hits:
        return {
            "state": "NOT_FOUND",
            "match_count": 0,
            "unique": False,
            "record": None,
            "occult_status": "UNKNOWN",
        }
    if len(hits) > 1:
        return {
            "state": "AMBIGUOUS_NAME",
            "match_count": len(hits),
            "unique": False,
            "record": None,
            "occult_status": "UNKNOWN",
            "ambiguous_names": [h["name"] for h in hits],
        }
    rec = hits[0]
    return {
        "state": "FOUND_UNIQUE",
        "match_count": 1,
        "unique": True,
        "record": rec,
        "occult_status": rec["occult_status"],
    }


def invitee_from_prompt(prompt_text: str) -> Optional[str]:
    """Best-effort extract of classmate name from invite dialog text."""
    text = str(prompt_text or "")
    m = re.search(
        r"invite\s+over\s+(?:classmate\s+)?([A-Za-z][A-Za-z\-']+)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1)
    return None


def evaluate_social_opportunity(
    *,
    social_prompt_active: bool = False,
    prompt_kind: str = "invite_over",
    prompt_text: str = "",
    invitee_name: Optional[str] = None,
    sim_library: Sequence[Mapping[str, object]] = (),
    lookup_ran: bool = False,
    occult_status: Optional[str] = None,
    player_directed: bool = False,
    already_busy: bool = False,
    capture_ref: str = "capture:social-opportunity",
) -> dict:
    """Return the highest-priority social-opportunity gate for one invite prompt."""
    cfg = load_contract()
    gates = cfg["call_stack"]["gates"]
    findings: list[str] = []
    name = invitee_name or invitee_from_prompt(prompt_text)
    lookup = None
    resolved_occult = _norm_occult(occult_status) if occult_status is not None else None

    if player_directed or already_busy:
        row = gates["PLAYER_FIRST_OR_BUSY"]
        return _result(
            gate="PLAYER_FIRST_OR_BUSY",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult or "UNKNOWN",
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if not social_prompt_active:
        row = gates["NO_SOCIAL_PROMPT"]
        return _result(
            gate="NO_SOCIAL_PROMPT",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult or "UNKNOWN",
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if prompt_kind != "invite_over":
        findings.append("UNSUPPORTED_PROMPT_KIND")
        return _result(
            gate="NO_SOCIAL_PROMPT",
            action="NO_SOCIAL_ROUTING",
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult or "UNKNOWN",
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if not name:
        findings.append("INVITEE_NAME_UNRESOLVED")
        row = gates["SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING"]
        return _result(
            gate="SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status="UNKNOWN",
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if not lookup_ran and not sim_library and resolved_occult is None:
        findings.append("SIM_LIBRARY_LOOKUP_REQUIRED")
        row = gates["SOCIAL_LOOKUP_REQUIRED"]
        return _result(
            gate="SOCIAL_LOOKUP_REQUIRED",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status="UNKNOWN",
            capture_ref=capture_ref,
            press_ok_allowed=False,
            next_actions=_lookup_actions(cfg),
        )

    if sim_library or lookup_ran:
        lookup = lookup_sim_library(name, sim_library)
        findings.append("SIM_LIBRARY_" + lookup["state"])
        resolved_occult = lookup["occult_status"]
        if lookup["state"] in {"NOT_FOUND", "AMBIGUOUS_NAME"}:
            row = gates["SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING"]
            return _result(
                gate="SOCIAL_LOOKUP_AMBIGUOUS_OR_MISSING",
                action=row["action"],
                cfg=cfg,
                findings=findings,
                invitee_name=name,
                lookup=lookup,
                occult_status="UNKNOWN",
                capture_ref=capture_ref,
                press_ok_allowed=False,
            )
    elif resolved_occult is None:
        resolved_occult = "UNKNOWN"

    if resolved_occult == "UNKNOWN":
        findings.append("OCCULT_STATUS_UNKNOWN_AFTER_LOOKUP")
        row = gates["SOCIAL_OCCULT_UNKNOWN"]
        return _result(
            gate="SOCIAL_OCCULT_UNKNOWN",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult,
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if resolved_occult in BLOCK_OCCULT - {"UNKNOWN"}:
        findings.append("OCCULT_BLOCKS_HOME_INVITE")
        row = gates["SOCIAL_OCCULT_UNSAFE_HOME_INVITE"]
        return _result(
            gate="SOCIAL_OCCULT_UNSAFE_HOME_INVITE",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult,
            capture_ref=capture_ref,
            press_ok_allowed=False,
        )

    if resolved_occult in SAFE_OCCULT:
        findings.append("UNIQUE_SAFE_OCCULT_OK_ALLOWED")
        row = gates["SOCIAL_OPPORTUNITY_OK_ALLOWED"]
        return _result(
            gate="SOCIAL_OPPORTUNITY_OK_ALLOWED",
            action=row["action"],
            cfg=cfg,
            findings=findings,
            invitee_name=name,
            lookup=lookup,
            occult_status=resolved_occult,
            capture_ref=capture_ref,
            press_ok_allowed=True,
        )

    findings.append("OCCULT_UNHANDLED")
    row = gates["SOCIAL_OCCULT_UNKNOWN"]
    return _result(
        gate="SOCIAL_OCCULT_UNKNOWN",
        action=row["action"],
        cfg=cfg,
        findings=findings,
        invitee_name=name,
        lookup=lookup,
        occult_status=resolved_occult,
        capture_ref=capture_ref,
        press_ok_allowed=False,
    )


def _lookup_actions(cfg: dict) -> list[dict]:
    steps = list((cfg.get("sim_library") or {}).get("lookup_steps") or [])
    return [
        {
            "id": "LOOKUP_INVITEE_IN_SIM_LIBRARY",
            "labels": ["relationship", "sim library", "known sims"],
            "steps": steps,
            "confidence": "HOST_HEURISTIC",
        }
    ]


def _result(
    *,
    gate: str,
    action: str,
    cfg: dict,
    findings: list[str],
    invitee_name: Optional[str],
    lookup: Optional[dict],
    occult_status: str,
    capture_ref: str,
    press_ok_allowed: bool,
    next_actions: Optional[list[dict]] = None,
) -> dict:
    return {
        "schema": "betterinstincts.social-opportunity-result/v1",
        "state": "SOCIAL_OPPORTUNITY_EVALUATED",
        "capture_ref": capture_ref,
        "gate": gate,
        "action": action,
        "disposition": "EMULATE",
        "invitee_name": invitee_name,
        "occult_status": occult_status,
        "press_ok_allowed": press_ok_allowed,
        "dialog_choice": "OK" if press_ok_allowed else "CANCEL",
        "lookup": lookup,
        "next_actions": next_actions or [],
        "primary_route": (next_actions or [{}])[0].get("id") if next_actions else None,
        "findings": sorted(set(findings)),
        "call_stack_order": list(cfg["call_stack"]["order"]),
        "proof_ceiling": cfg["proof_ceiling"],
        "journey": cfg.get("journey"),
    }


def should_attach_social_opportunity(
    *,
    social_prompt_active: bool,
    prompt_kind: Optional[str] = None,
) -> bool:
    return bool(social_prompt_active) and (
        prompt_kind in {None, "invite_over"} or bool(prompt_kind)
    )
