"""Active Sim profile inspection for host call stacks (P95).

Composes supplied Simology / skills / preferences / whims with moodlets.
Never claims screenshot vision, a Sims API, BI-005 skill growth, or UI clicks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union

from betterinstincts.moodlets import MoodletError, evaluate_moodlets

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "sim-profile.v1.json"

SkillInput = Union[str, Mapping[str, object]]


class SimProfileError(ValueError):
    pass


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128000:
        raise SimProfileError("UNSAFE_SIM_PROFILE_CONTRACT")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "betterinstincts.sim-profile/v1":
        raise SimProfileError("INVALID_SIM_PROFILE_SCHEMA")
    return data


def _norm_token(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _bounded_labels(items: Sequence[str], *, max_items: int, field: str) -> list[str]:
    if len(items) > max_items:
        raise SimProfileError(f"TOO_MANY_{field.upper()}")
    out: list[str] = []
    for raw in items:
        if not isinstance(raw, str) or not raw or len(raw) > 80:
            raise SimProfileError(f"INVALID_{field.upper()}_TOKEN")
        token = _norm_token(raw)
        if token not in out:
            out.append(token)
    return out


def _parse_skills(skills: Sequence[SkillInput], *, max_items: int) -> list[dict]:
    if len(skills) > max_items:
        raise SimProfileError("TOO_MANY_SKILLS")
    out: list[dict] = []
    seen: set[str] = set()
    for item in skills:
        level: Optional[int] = None
        if isinstance(item, str):
            raw = item.strip()
            if ":" in raw:
                raw_name, level_part = raw.rsplit(":", 1)
                try:
                    level = int(level_part)
                except ValueError as exc:
                    raise SimProfileError("INVALID_SKILL_LEVEL") from exc
                if level < 0 or level > 10:
                    raise SimProfileError("INVALID_SKILL_LEVEL")
                name = _norm_token(raw_name)
            else:
                name = _norm_token(raw)
        elif isinstance(item, Mapping):
            raw_name = item.get("name") or item.get("skill")
            if not isinstance(raw_name, str) or not raw_name or len(raw_name) > 80:
                raise SimProfileError("INVALID_SKILL_TOKEN")
            name = _norm_token(raw_name)
            level_raw = item.get("level")
            if level_raw is None:
                level = None
            else:
                try:
                    level = int(level_raw)
                except (TypeError, ValueError) as exc:
                    raise SimProfileError("INVALID_SKILL_LEVEL") from exc
                if level < 0 or level > 10:
                    raise SimProfileError("INVALID_SKILL_LEVEL")
        else:
            raise SimProfileError("INVALID_SKILL_TOKEN")
        if not name:
            raise SimProfileError("INVALID_SKILL_TOKEN")
        if name in seen:
            continue
        seen.add(name)
        row = {"name": name, "proof": "READ_LEVELS_ONLY"}
        if level is not None:
            row["level"] = level
        out.append(row)
    return out


def _match_desires(
    *,
    catalog: Mapping[str, dict],
    likes: Sequence[str],
    dislikes: Sequence[str],
    whims: Sequence[str],
    skills: Sequence[Mapping[str, object]],
    moodlets: Sequence[str],
    traits: Sequence[str],
) -> list[dict]:
    haystack = {
        "likes": set(likes),
        "dislikes": set(dislikes),
        "whims": set(whims),
        "skills": {str(s["name"]) for s in skills},
        "moodlets": {_norm_token(m) for m in moodlets},
        "traits": set(traits),
    }
    matched: list[dict] = []
    for desire_id, row in catalog.items():
        aliases = {_norm_token(desire_id), *{_norm_token(a) for a in row.get("aliases", [])}}
        evidence: list[str] = []
        for surface, tokens in haystack.items():
            if surface == "dislikes":
                continue
            hits = sorted(aliases & tokens)
            if hits:
                evidence.append(f"{surface}:{','.join(hits)}")
            related = {
                _norm_token(x)
                for x in row.get(
                    "related_skills" if surface == "skills" else "related_preferences",
                    [],
                )
            }
            if surface == "skills":
                related_hits = sorted(related & tokens)
                if related_hits:
                    evidence.append(f"skills:{','.join(related_hits)}")
            elif surface == "likes":
                related_hits = sorted(related & tokens)
                if related_hits and f"likes:{','.join(related_hits)}" not in evidence:
                    evidence.append(f"likes:{','.join(related_hits)}")
        # Prefer unique evidence lines
        evidence = list(dict.fromkeys(evidence))
        if evidence:
            matched.append(
                {
                    "desire_id": desire_id,
                    "evidence": evidence,
                    "host_note": row.get("host_note"),
                    "explain_via": list(row.get("explain_via", [])),
                }
            )
    return matched


def evaluate_sim_profile(
    *,
    sim_name: Optional[str] = None,
    life_stage: Optional[str] = None,
    traits: Sequence[str] = (),
    aspiration: Optional[str] = None,
    aspiration_track: Optional[str] = None,
    skills: Sequence[SkillInput] = (),
    likes: Sequence[str] = (),
    dislikes: Sequence[str] = (),
    whims: Sequence[str] = (),
    emotion: Optional[str] = None,
    moodlets: Sequence[str] = (),
    needs: Optional[Mapping[str, float]] = None,
    capture_ref: str = "capture:sim-profile",
) -> dict:
    """Normalize supplied Sim profile panels into a host-readable inspection report."""
    cfg = load_contract()
    surfaces = cfg["surfaces"]

    has_any = any(
        [
            sim_name,
            life_stage,
            traits,
            aspiration,
            skills,
            likes,
            dislikes,
            whims,
            emotion is not None,
            moodlets,
        ]
    )
    if not has_any:
        return {
            "schema": "betterinstincts.sim-profile-result/v1",
            "state": "SENSOR_NOT_SUPPLIED",
            "findings": ["SIM_PROFILE_NOT_OBSERVED"],
            "player_discovery_map": cfg["player_discovery_map"],
            "desires": [],
            "gate": None,
            "forbidden_actions": list(cfg["forbidden_actions"]),
            "capture_ref": capture_ref,
            "proof_ceiling": cfg["proof_ceiling"],
        }

    try:
        moodlet_eval = evaluate_moodlets(
            emotion=emotion,
            moodlets=moodlets,
            needs=needs,
            capture_ref=capture_ref,
        )
    except MoodletError as exc:
        raise SimProfileError(str(exc)) from exc

    trait_labels = _bounded_labels(traits, max_items=int(surfaces["traits"]["max_items"]), field="traits")
    like_labels = _bounded_labels(likes, max_items=int(surfaces["likes"]["max_items"]), field="likes")
    dislike_labels = _bounded_labels(
        dislikes, max_items=int(surfaces["dislikes"]["max_items"]), field="dislikes"
    )
    whim_labels = _bounded_labels(whims, max_items=int(surfaces["whims"]["max_items"]), field="whims")
    skill_rows = _parse_skills(skills, max_items=int(surfaces["skills"]["max_items"]))

    if sim_name is not None:
        if not isinstance(sim_name, str) or not sim_name or len(sim_name) > 80:
            raise SimProfileError("INVALID_SIM_NAME")
    if life_stage is not None:
        if not isinstance(life_stage, str) or not life_stage or len(life_stage) > 40:
            raise SimProfileError("INVALID_LIFE_STAGE")
    if aspiration is not None:
        if not isinstance(aspiration, str) or not aspiration or len(aspiration) > 80:
            raise SimProfileError("INVALID_ASPIRATION")

    desires = _match_desires(
        catalog=cfg["desire_catalog"],
        likes=like_labels,
        dislikes=dislike_labels,
        whims=whim_labels,
        skills=skill_rows,
        moodlets=list(moodlets),
        traits=trait_labels,
    )

    findings: list[str] = ["SIM_PROFILE_EVALUATED"]
    if desires:
        findings.append("DESIRE_CONTEXT_MATCHED")
    if skill_rows:
        findings.append("SKILL_LEVELS_READ_ONLY")
    if like_labels or dislike_labels:
        findings.append("PREFERENCES_SUPPLIED")
    if whim_labels:
        findings.append("WHIMS_SUPPLIED")
    if trait_labels or aspiration:
        findings.append("SIMOLOGY_SUPPLIED")
    if moodlet_eval.get("state") == "SENSOR_NOT_SUPPLIED":
        findings.append("MOODLETS_OPTIONAL_ABSENT")
    elif moodlet_eval.get("unknown_moodlets"):
        findings.append("UNKNOWN_MOODLET_LABEL")

    conflicted = []
    for desire in desires:
        did = desire["desire_id"]
        aliases = {_norm_token(did), *{_norm_token(a) for a in cfg["desire_catalog"][did].get("aliases", [])}}
        if aliases & set(dislike_labels):
            conflicted.append(did)
    if conflicted:
        findings.append("DESIRE_CONFLICTS_DISLIKE")

    return {
        "schema": "betterinstincts.sim-profile-result/v1",
        "state": "SIM_PROFILE_EVALUATED",
        "identity": {
            "sim_name": sim_name,
            "life_stage": _norm_token(life_stage) if life_stage else None,
        },
        "simology": {
            "traits": trait_labels,
            "aspiration": _norm_token(aspiration) if aspiration else None,
            "aspiration_track": _norm_token(aspiration_track) if aspiration_track else None,
        },
        "skills": skill_rows,
        "preferences": {"likes": like_labels, "dislikes": dislike_labels},
        "whims": whim_labels,
        "moodlets": moodlet_eval,
        "desires": desires,
        "findings": sorted(set(findings)),
        "player_discovery_map": cfg["player_discovery_map"],
        "gate": cfg["call_stack_gate"],
        "disposition": "EMULATE",
        "forbidden_actions": list(cfg["forbidden_actions"]),
        "naming_disambiguation": cfg["naming_disambiguation"],
        "capture_ref": capture_ref,
        "proof_ceiling": cfg["proof_ceiling"],
    }
