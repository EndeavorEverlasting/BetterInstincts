"""Fail closed if BetterInstincts horizon loses required phases."""
import json
from pathlib import Path

NEEDS={"BI-002","BI-003A","BI-003B","BI-003C","BI-003D","BI-003E","BI-003F"}
class HorizonError(ValueError):
    pass

def validate(data):
    if data.get("schema")!="betterinstincts.horizon/v1":
        raise HorizonError("INVALID_SCHEMA")
    rows=data["stages"]
    ids=[x["id"] for x in rows]
    if len(ids)!=len(set(ids)) or not NEEDS.issubset(ids):
        raise HorizonError("MISSING_OR_DUPLICATE_NEED_PHASE")
    parents={x["id"]:x["depends_on"] for x in rows}
    for phase,prereq in (("BI-004","BI-003F"),("BI-005","BI-004"),("BI-006","BI-005")):
        if prereq not in parents.get(phase,()):
            raise HorizonError("PHASE_ORDER_REGRESSION")
    if set(parents["BI-003F"])!={"BI-003A","BI-003B","BI-003C","BI-003D","BI-003E"}:
        raise HorizonError("BALANCE_GATE_REMOVED")
    if data.get("current_gate")!="BI-002":
        raise HorizonError("HUNGER_GATE_LOST")
    visiting=set()
    visited=set()
    def walk(name):
        if name in visiting:
            raise HorizonError("CYCLE")
        if name in visited:
            return
        visiting.add(name)
        for dep in parents[name]:
            if dep not in parents:
                raise HorizonError("DANGLING_DEPENDENCY")
            walk(dep)
        visiting.remove(name)
        visited.add(name)
    for name in parents:
        walk(name)
    # A cross-stage policy cannot become a shortcut around live Horizon gates.
    # The merged pure evaluator is an offline advisor, not an EA runtime hook.
    cross=data.get("cross_cutting_capabilities")
    native=cross.get("native_goal_continuity") if isinstance(cross,dict) else None
    if not isinstance(native,dict) or native.get("contract_id")!="NATIVE_AUTONOMY_GOAL_YIELD":
        raise HorizonError("NATIVE_AUTONOMY_HORIZON_CONTRACT_MISSING")
    if (native.get("placement")!="CROSS_CUTTING_NON_GATE"
            or native.get("horizon_gate_effect")!="NONE"
            or native.get("excluded_from_stage_certification") is not True):
        raise HorizonError("CROSS_CUTTING_CAPABILITY_CANNOT_ADVANCE_HORIZON")
    if set(native.get("linked_stage_ids",()))!=set(ids):
        raise HorizonError("NATIVE_AUTONOMY_HORIZON_SCOPE_DRIFT")
    if (native.get("owner_contract")!="contracts/autonomy-moderation.v1.json#native_household_policy"
            or native.get("policy_implementation")!="betterinstincts/autonomy_moderation.py#evaluate_native_household_autonomy"):
        raise HorizonError("NATIVE_AUTONOMY_OWNER_DRIFT")
    adapter=native.get("native_adapter")
    if not isinstance(adapter,dict):
        raise HorizonError("NATIVE_ADAPTER_STATUS_UNKNOWN")
    status=adapter.get("status")
    if status=="NOT_INSTALLED_NOT_CERTIFIED":
        if any(adapter.get(k) is not None for k in ("game_build","live_receipt","rollback_receipt")):
            raise HorizonError("NATIVE_AUTONOMY_PROOF_INFLATION")
    elif status=="PATCH_CERTIFICATION_RECORDED":
        if not all(isinstance(adapter.get(k),str) and adapter[k].strip()
                   for k in ("game_build","live_receipt","rollback_receipt")):
            raise HorizonError("NATIVE_AUTONOMY_CERT_REFS_MISSING")
    else:
        raise HorizonError("NATIVE_ADAPTER_STATUS_UNKNOWN")
    if not isinstance(adapter.get("owner_issue"),int) or adapter["owner_issue"]<=0:
        raise HorizonError("NATIVE_AUTONOMY_OWNER_ISSUE_MISSING")
    return {"state":"PASS","stages":len(rows),"game_certification":"NOT_PROVED",
            "native_autonomy_policy":native["policy_merge"]["proof"],
            "native_adapter_status":status}

if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    print(json.dumps(validate(json.loads((root/"plans/horizon.v1.json").read_text()))))
