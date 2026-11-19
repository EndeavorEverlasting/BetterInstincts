"""Effect-free native runtime seam notices for an opt-in exact-build adapter port.

A native cycle returns the *same* result whether this port is present or not.
The port is advisory only and never writes a file, spawns a process, opens a
save, sends desktop input, or grants game effect authority.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "betterinstincts.runtime-seam-notice/v1"
MAX_EMISSIONS_PER_SESSION = 16
TOKEN = re.compile(r"^[A-Z][A-Z0-9_]{2,100}$")

# Explicit source-owner recovery signals. Normal gameplay yields, wait states,
# pending dispatch and momentary portrait readbacks are NOT source gaps.
GAPS = {
    "NATIVE_FRAME_UNQUALIFIED": (
        "FRESH_EXACT_BUILD_FRAME", "HOST_OBSERVATION_REQUIRED",
        "betterinstincts/installed_player_runtime.py",
    ),
    "NATIVE_SESSION_REBIND_REQUIRED": (
        "RECONCILE_CURRENT_NATIVE_SESSION", "OBSERVE_BEFORE_RETRY",
        "betterinstincts/installed_player_runtime.py",
    ),
    "PORTRAIT_EVIDENCE_UNQUALIFIED": (
        "NATIVE_PORTRAIT_OBSERVER_EVIDENCE", "HOST_BINDING_REQUIRED",
        "betterinstincts/portrait_handoff.py",
    ),
    "NATIVE_PROPOSAL_ID_UNVERIFIED": (
        "NATIVE_ACTION_PROPOSAL_IDENTITY", "IMPLEMENTATION_OR_HOST_PROOF_REQUIRED",
        "betterinstincts/installed_player_runtime.py",
    ),
}


def notice_for(outcome: object, *, game_build: str, session: object = None) -> dict | None:
    """Return bounded status semantics; never raw Sim/household/save identity."""
    if not isinstance(outcome, str) or not TOKEN.fullmatch(outcome):
        return None
    route = GAPS.get(outcome)
    if route is None:
        return None
    if (not isinstance(game_build, str) or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", game_build)):
        return None
    capability, resolution, owner = route
    key = json.dumps([outcome, capability, owner], separators=(",", ":"))
    run_tag = (hashlib.sha256(session.encode("utf-8")).hexdigest()[:16]
               if isinstance(session, str) and 1 <= len(session) <= 100 else None)
    return {
        "schema": SCHEMA,
        "type": "NATIVE_RUNTIME_SEAM",
        "seam_id": "scl-" + hashlib.sha256(key.encode("ascii")).hexdigest()[:20],
        "stage": "native_runtime",
        "reason_code": outcome,
        "capability": capability,
        "resolution_state": resolution,
        "canonical_owner": owner,
        "game_build": game_build,
        "session_tag": run_tag,
        "effect_admission": "NOT_GRANTED",
        "proof_ceiling": "ADAPTER_NOTICE_NOT_INDEPENDENT_GAME_OBSERVATION",
    }
