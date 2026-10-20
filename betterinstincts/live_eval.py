"""Deterministic review of gameplay observations. NEVER certifies live game truth."""
import math
import statistics

STAGES = ("baseline", "modified", "rollback")
REQUIRED_BASELINE = 5
REQUIRED_MODIFIED = 5

class EvidenceError(ValueError):
    pass

def validate_trial(row):
    if not isinstance(row, dict) or row.get("stage") not in STAGES or not isinstance(row.get("trial"), int) or isinstance(row.get("trial"), bool) or row["trial"] < 1:
        raise EvidenceError("INVALID_TRIAL_KEY")
    for field in ("seconds_to_eat", "min_hunger", "sim_lag_ms"):
        val = row.get(field)
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val) or val < 0:
            raise EvidenceError("INVALID_METRIC:" + field)
    if row["seconds_to_eat"] > 7200 or row["min_hunger"] > 1 or row["sim_lag_ms"] > 60000:
        raise EvidenceError("METRIC_OUT_OF_BOUNDS")
    for field in ("player_interruptions", "action_loops", "exceptions"):
        val = row.get(field)
        if not isinstance(val, int) or isinstance(val, bool) or not 0 <= val <= 100:
            raise EvidenceError("INVALID_COUNT:" + field)
    note = row.get("observation_ref")
    if not isinstance(note, str) or not 3 <= len(note) <= 160:
        raise EvidenceError("OBSERVATION_REF_MISSING")

def evaluate(metadata, trials):
    """PASS means numeric criteria, never Sims 4 verification or approval."""
    grouped = {name: [] for name in STAGES}
    keys = set()
    for row in trials:
        validate_trial(row)
        key = (row["stage"], row["trial"])
        if key in keys:
            raise EvidenceError("DUPLICATE_TRIAL")
        keys.add(key)
        grouped[row["stage"]].append(row)
    counts = {s: len(grouped[s]) for s in STAGES}
    result = {"state": "INCOMPLETE", "counts": counts, "criteria": {}, "proof_ceiling": "UNVERIFIED_OBSERVATIONS_ONLY"}
    if counts["baseline"] < REQUIRED_BASELINE or counts["modified"] < REQUIRED_MODIFIED or counts["rollback"] < 1:
        return result
    a,b,r = (grouped[s] for s in STAGES)
    before = statistics.median(v["seconds_to_eat"] for v in a)
    after = statistics.median(v["seconds_to_eat"] for v in b)
    lag_a = statistics.median(v["sim_lag_ms"] for v in a)
    lag_b = statistics.median(v["sim_lag_ms"] for v in b)
    result["criteria"] = {
        "timelier_food_at_least_15pct": before > 0 and after <= before * 0.85,
        "no_player_interruptions": all(v["player_interruptions"] == 0 for v in b),
        "no_action_loops": all(v["action_loops"] == 0 for v in b),
        "no_exceptions": all(v["exceptions"] == 0 for v in b),
        "no_material_sim_lag": lag_b <= max(lag_a * 1.20, lag_a + 5),
        "rollback_smoke_safe": all(v["player_interruptions"] == v["action_loops"] == v["exceptions"] == 0 for v in r),
        "game_evidence_attested": (
            bool(metadata.get("disposable_save_confirmed")) and
            bool(metadata.get("user_selected_mods_root_confirmed")) and
            isinstance(metadata.get("package_sha256"), str) and len(metadata["package_sha256"]) == 64 and
            isinstance(metadata.get("tuning_resource_id"), str) and bool(metadata["tuning_resource_id"].strip()) and
            isinstance(metadata.get("tuning_source_sha256"), str) and len(metadata["tuning_source_sha256"]) == 64 and
            isinstance(metadata.get("capture_ref"), str) and bool(metadata["capture_ref"].strip())
        ),
    }
    result["medians"] = {"vanilla_seconds": before, "modified_seconds": after, "vanilla_lag_ms": lag_a, "modified_lag_ms": lag_b}
    result["state"] = "MEASUREMENTS_PASS_REVIEW_REQUIRED" if all(result["criteria"].values()) else "MEASUREMENTS_FAIL"
    return result
