"""Load the canonical BetterInstincts glossary (fail closed on drift)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "glossary.v1.json"
MAX_BYTES = 64_000
REQUIRED_TERMS = frozenset({
    "PLAYER_FIRST",
    "GOOD_BEHAVIOR",
    "BAD_BEHAVIOR",
    "EMULATE",
    "OPTIMIZE",
    "EMULATE_THEN_OPTIMIZE",
    "IN_FRAME_WALK_THRASH",
    "MAP_TRAVEL",
    "CRITICAL_NEED",
    "HOST_LISTENER",
    "HOST_EVALUATOR",
    "PROGRESSION_EVALUATOR",
    "OUTDOOR_SOCIAL_DEFAULT",
    "EVENT_INDOOR_ROUTING",
    "EVENT_BALANCE_STACK",
    "EVENT_GOAL_ACTION",
    "EVENT_GOAL_PLAN",
    "MOODLET_STRIP",
    "MOODLET_AWARE_ROUTING",
    "SIM_PROFILE_INSPECT",
    "SIMOLOGY_PANEL",
    "PLAYER_DISCOVERY_MAP",
    "PROOF_CEILING",
    "PLAYER_PRESENT_ON_CANVAS",
    "PLAYER_PLAYING",
    "HOST_MAY_AUTOMATE",
    "YIELD_TO_PLAYER",
    "HOST_AUTOMATE",
    "LOT_ENVIRONMENT_GAIN",
    "ECO_FOOTPRINT_GREEN",
    "ECO_FOOTPRINT_INDUSTRIAL",
    "BUILD_OPTIMIZE_PLAN",
})


class GlossaryError(ValueError):
    pass


def load_glossary(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise GlossaryError("GLOSSARY_UNSAFE")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != "betterinstincts.glossary/v1":
        raise GlossaryError("BAD_GLOSSARY_SCHEMA")
    terms = cfg.get("terms")
    if not isinstance(terms, dict) or not REQUIRED_TERMS.issubset(terms):
        raise GlossaryError("GLOSSARY_TERMS_INCOMPLETE")
    for key in REQUIRED_TERMS:
        row = terms[key]
        if not isinstance(row, dict) or not isinstance(row.get("definition"), str) or len(row["definition"]) < 12:
            raise GlossaryError("GLOSSARY_TERM_INVALID:" + key)
    return cfg


def define(term_id: str, path: Path = CONTRACT) -> str:
    cfg = load_glossary(path)
    row = cfg["terms"].get(term_id)
    if row is None:
        raise GlossaryError("UNKNOWN_TERM:" + term_id)
    return str(row["definition"])
