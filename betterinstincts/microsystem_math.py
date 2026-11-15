"""Evidence-bound, optional mathematical arbitration across Sims microsystems.

Reuse PS-0245 Bellman and Lagrange/KKT, and PS-0241's holdout-qualified
Gaussian-process duration model. Never replace the domain owner's receipt,
grant an effect permit, authenticate caller assertions, or install a worker.
A new mathematical architecture is welcome through the same comparison seam.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import json
import math
import re

from betterinstincts.decision_horizon import (
    DecisionHorizonError, optimize_activity_plan, allocate_continuous_time,
)
from betterinstincts.ecology_forecast import (
    EcologyForecastError, compare_duration_models,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "microsystem-math.v1.json"
PACKET = "betterinstincts.microsystem-math-packet/v1"
RESULT = "betterinstincts.microsystem-math-result/v1"
PROOF = "OFFLINE_MATH_COMPARISON_ONLY_NOT_GAMEPLAY_AUTHORITY"
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
MAX_RECEIPTS = 32


class MicrosystemMathError(ValueError):
    pass


def _ref(value: object) -> bool:
    return type(value) is str and REF.fullmatch(value) is not None


def _finite(value: object, *, lo: float = -100000, hi: float = 100000) -> bool:
    return type(value) in (float, int) and math.isfinite(value) and lo <= value <= hi


def load_contract(path: Path = CONTRACT) -> dict:
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
        raise MicrosystemMathError("MATH_REGISTRY_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MicrosystemMathError("MATH_REGISTRY_PARSE_FAILED") from exc
    if (data.get("schema") != "betterinstincts.microsystem-math/v1"
            or not isinstance(data.get("microsystems"), Mapping)
            or not isinstance(data.get("cascade_domains"), list)
            or len(set(data["cascade_domains"])) != len(data["cascade_domains"])
            or set(data["cascade_domains"]) - set(data["microsystems"])
            or data.get("validation", {}).get("min_challenger_holdout") != 8):
        raise MicrosystemMathError("MATH_REGISTRY_INCOMPLETE")
    return data


def _fallback(domain: str, gate: str, *, reason: str) -> dict:
    return {
        "schema": RESULT, "domain": domain, "state": "FALLBACK_EXISTING",
        "selected_planner": "EXISTING_MICROSYSTEM",
        "existing_gate": gate, "reason": reason,
        "bellman": None, "lagrange_kkt": None, "gaussian": None,
        "challenger": None, "execute_allowed": False,
        "control_permit": None, "proof_ceiling": PROOF,
    }


def _challenger(
    challenger: object, *,
    packet: Mapping, baseline: Mapping, settings: Mapping,
) -> dict:
    """Compare new planners on independent chronological observed holdout.

    Even a winning shape comparison is NOT a trusted live-game approval.
    The alternative first action must independently pass the existing
    PS-0245 hard feasibility guards before any offline advisory promotion.
    """
    decline = {"state": "NOT_PROMOTED", "reason": "NO_QUALIFIED_CHALLENGER"}
    if not isinstance(challenger, Mapping):
        return decline
    if (not _ref(challenger.get("planner_id"))
            or challenger["planner_id"] in {"EXISTING_MICROSYSTEM", "BELLMAN_KKT_GP"}
            or not _ref(challenger.get("proposed_step_id"))
            or not _ref(challenger.get("reviewer_ref"))
            or not _ref(challenger.get("producer_ref"))
            or challenger["reviewer_ref"] == challenger["producer_ref"]
            or challenger.get("independent_reviewed") is not True
            or challenger.get("game_build") != packet["game_build"]
            or challenger.get("capture_ref") != packet["capture_ref"]
            or not isinstance(challenger.get("steps"), list)
            or not isinstance(challenger.get("routes"), list)):
        return {**decline, "reason": "CHALLENGER_IDENTITY_OR_INDEPENDENCE_UNVERIFIED"}
    samples = challenger.get("holdout")
    if (not isinstance(samples, list)
            or not settings["min_challenger_holdout"] <= len(samples)
                   <= settings["max_challenger_holdout"]):
        return {**decline, "reason": "CHALLENGER_HOLDOUT_INSUFFICIENT"}
    capture_ids: set[str] = set()
    baseline_errors, challenger_errors = [], []
    for row in samples:
        if (not isinstance(row, Mapping)
                or row.get("game_build") != packet["game_build"]
                or row.get("evidence_state") != "LOCAL_OBSERVED"
                or not _ref(row.get("capture_ref"))
                or not _ref(row.get("proof_ref"))
                or row["capture_ref"] in capture_ids
                or any(not _finite(row.get(k)) for k in (
                    "observed_score", "baseline_predicted", "candidate_predicted"))):
            return {**decline, "reason": "CHALLENGER_HOLDOUT_PROVENANCE_INVALID"}
        capture_ids.add(row["capture_ref"])
        b = abs(row["baseline_predicted"] - row["observed_score"])
        c = abs(row["candidate_predicted"] - row["observed_score"])
        if c > b + settings["max_individual_error_regression"] + 1e-9:
            return {**decline, "reason": "CHALLENGER_HOLDOUT_REGRESSION"}
        baseline_errors.append(b)
        challenger_errors.append(c)
    base_mae = sum(baseline_errors) / len(baseline_errors)
    challenger_mae = sum(challenger_errors) / len(challenger_errors)
    if (base_mae <= 1e-8 or challenger_mae > (
            1.0 - settings["min_relative_mae_improvement"]) * base_mae + 1e-9):
        return {**decline, "reason": "NO_INDEPENDENT_SUPERIORITY"}
    try:
        checked = optimize_activity_plan(
            packet["bellman"]["snapshot"], challenger["steps"],
            challenger["routes"], capture_ref=packet["capture_ref"],
            horizon_minutes=packet["bellman"].get("horizon_minutes", 120),
            max_expansions=packet["bellman"].get("max_expansions", 1000),
            max_depth=packet["bellman"].get("max_depth", 6),
        )
    except (DecisionHorizonError, ValueError, TypeError, KeyError):
        return {**decline, "reason": "CHALLENGER_FEASIBILITY_INVALID"}
    step = checked.get("next_step")
    if (checked.get("gate") != "FORECAST_STAGED_NOT_DISPATCHABLE"
            or not isinstance(step, Mapping)
            or step.get("step_id") != challenger["proposed_step_id"]
            or checked.get("truncated")):
        return {**decline, "reason": "CHALLENGER_NOT_FEASIBLE_UNDER_SHARED_GATES"}
    return {
        "state": "BETTER_OFFLINE_CANDIDATE", "reason": "HOLDOUT_AND_HARD_FEASIBILITY",
        "planner_id": challenger["planner_id"],
        "proposed_step_id": challenger["proposed_step_id"],
        "reviewer_ref": challenger["reviewer_ref"],
        "baseline_mae": round(base_mae, 6),
        "challenger_mae": round(challenger_mae, 6),
        "holdout_count": len(samples),
        "execute_allowed": False,
    }


def evaluate_microsystem_math(
    receipt: Mapping, *, capture_ref: str, packet: Mapping | None = None,
    player_active: bool = False, registry: Mapping | None = None,
) -> dict:
    """Call all three canonical engines for complete fresh domain evidence.

    The existing microsystem receipt always remains independently available.
    Optional externally authored planners compete through the challenger
    protocol; no hardcoded family or one-permanent-engine lock-in.
    """
    cfg = load_contract() if registry is None else registry
    if not isinstance(receipt, Mapping) or not _ref(capture_ref):
        raise MicrosystemMathError("MATH_RECEIPT_OR_CAPTURE_INVALID")
    domain, gate = receipt.get("domain"), receipt.get("gate")
    if domain not in cfg["microsystems"] or not isinstance(gate, str):
        raise MicrosystemMathError("UNREGISTERED_MICROSYSTEM")
    result = _fallback(domain, gate, reason="NO_FRESH_MATH_PACKET")
    if player_active:
        return {**result, "state": "PLAYER_YIELD", "reason": "PLAYER_OWNS_DECISION"}
    if packet is None:
        return result
    if (not isinstance(packet, Mapping)
            or packet.get("schema") != PACKET
            or packet.get("capture_ref") != capture_ref
            or packet.get("microsystem_id") != domain
            or not _ref(packet.get("sim_ref"))
            or not _ref(packet.get("game_build"))
            or not _ref(packet.get("provenance_ref"))
            or not isinstance(packet.get("bellman"), Mapping)
            or not isinstance(packet.get("kkt"), Mapping)
            or not isinstance(packet.get("gaussian"), Mapping)):
        return {**result, "reason": "INCOMPLETE_OR_STALE_MATH_EVIDENCE"}
    bellman, kkt, gp = packet["bellman"], packet["kkt"], packet["gaussian"]
    snap = bellman.get("snapshot")
    if (not isinstance(snap, Mapping)
            or snap.get("capture_ref") != capture_ref
            or snap.get("sim_ref") != packet["sim_ref"]
            or snap.get("selected_sim_ref") != packet["sim_ref"]
            or not isinstance(bellman.get("steps"), list)
            or not isinstance(bellman.get("routes"), list)
            or gp.get("game_build") != packet["game_build"]
            or not _ref(gp.get("action_id"))
            or not isinstance(gp.get("samples"), list)):
        return {**result, "reason": "MATH_ACTOR_OR_EVIDENCE_MISMATCH"}
    try:
        # These are the EXISTING canonical algorithms, not replacements.
        bellman_result = optimize_activity_plan(
            snap, bellman["steps"], bellman["routes"],
            capture_ref=capture_ref,
            horizon_minutes=bellman.get("horizon_minutes", 120),
            max_expansions=bellman.get("max_expansions", 1000),
            max_depth=bellman.get("max_depth", 6),
        )
        kkt_result = allocate_continuous_time(
            kkt.get("budget_minutes"), kkt.get("activities"))
        gaussian_result = compare_duration_models(
            gp["samples"], game_build=packet["game_build"],
            action_id=gp["action_id"], context=gp.get("context"),
            baseline_upper_sim_minutes=gp.get("baseline_upper_sim_minutes"),
        )
    except (DecisionHorizonError, EcologyForecastError, ValueError, KeyError,
            TypeError, ZeroDivisionError, OverflowError):
        return {**result, "reason": "MATH_MODEL_INVALID_PRESERVE_EXISTING"}
    next_step = bellman_result.get("next_step")
    if (bellman_result.get("gate") != "FORECAST_STAGED_NOT_DISPATCHABLE"
            or not isinstance(next_step, Mapping)
            or bellman_result.get("truncated")
            or not _finite(bellman_result.get("expected_net_utility"),
                           lo=0.000001, hi=100000)):
        return {
            **result, "reason": "NO_VERIFIED_POSITIVE_BELLMAN_STEP",
            "bellman_gate": bellman_result.get("gate"),
            "lagrange_kkt": kkt_result, "gaussian": gaussian_result,
        }
    comparison = _challenger(
        packet.get("challenger"), packet=packet,
        baseline=bellman_result, settings=cfg["validation"])
    chosen = ("SUPERIOR_ADVISORY" if comparison["state"] ==
              "BETTER_OFFLINE_CANDIDATE" else "MATH_ADVISORY")
    return {
        **result, "state": chosen, "reason": "COMPLETE_MATH_ADVISORY",
        "selected_planner": (comparison["planner_id"] if
                             chosen == "SUPERIOR_ADVISORY" else "BELLMAN_KKT_GP"),
        "next_step_id": (comparison["proposed_step_id"] if
                         chosen == "SUPERIOR_ADVISORY" else next_step["step_id"]),
        "bellman": {
            "gate": bellman_result["gate"],
            "expected_net_utility": bellman_result["expected_net_utility"],
            "next_step_id": next_step["step_id"],
            "expansions": bellman_result["expansions"],
        },
        "lagrange_kkt": kkt_result,
        "gaussian": gaussian_result,
        "challenger": comparison,
    }


def evaluate_math_portfolio(
    receipts: Sequence[Mapping], *, capture_ref: str,
    math_packets: Mapping[str, Mapping] | None = None,
    player_active: bool = False, registry: Mapping | None = None,
) -> dict:
    """One bounded invocation per registered domain; never mutate receipts."""
    cfg = load_contract() if registry is None else registry
    if (not isinstance(receipts, (tuple, list)) or
            len(receipts) > min(MAX_RECEIPTS, cfg["validation"]["max_domain_receipts"])
            or not _ref(capture_ref) or type(player_active) is not bool or
            (math_packets is not None and not isinstance(math_packets, Mapping))):
        raise MicrosystemMathError("MATH_PORTFOLIO_INVALID")
    names = [r.get("domain") for r in receipts if isinstance(r, Mapping)]
    if (len(names) != len(receipts) or len(set(names)) != len(names)
            or any(name not in cfg["microsystems"] for name in names)):
        raise MicrosystemMathError("MATH_PORTFOLIO_SCOPE_INVALID")
    packets = {} if math_packets is None else math_packets
    if set(packets) - set(names):
        raise MicrosystemMathError("MATH_PACKETS_FOR_UNKNOWN_DOMAIN")
    results = [
        evaluate_microsystem_math(
            receipt, capture_ref=capture_ref,
            packet=packets.get(receipt["domain"]),
            player_active=player_active, registry=cfg)
        for receipt in receipts
    ]
    return {
        "schema": "betterinstincts.microsystem-math-portfolio/v1",
        "capture_ref": capture_ref,
        "state": "PLAYER_YIELD" if player_active else "POLLED",
        "domain_results": results, "fallback_receipts_unchanged": True,
        "execute_allowed": False, "control_permit": None,
        "proof_ceiling": PROOF,
    }
