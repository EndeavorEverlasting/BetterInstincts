"""Fail closed if BetterInstincts horizon loses required phases."""
import json
from pathlib import Path

NEEDS={"BI-002","BI-003A","BI-003B","BI-003C","BI-003D","BI-003E","BI-003F"}
SUPPORTING_ID="BI-WORLD-TRAVERSAL-P08-SENSOR"
SUPPORTING_DISPATCH="plans/active/BI-HORIZON.dispatch.v1.json"
SUPPORTING_RUNBOOK="plans/active/BI-WORLD-TRAVERSAL-CLOSERS-P04-20261110.md"
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
    supporting=data.get("next_supporting_priority")
    if (not isinstance(supporting,dict)
            or supporting.get("id")!=SUPPORTING_ID
            or supporting.get("kind")!="SUPPORTING_GAME_HOST_PROOF"
            or supporting.get("priority")!="NEXT_SUPPORTING_LOCAL_PROOF"
            or supporting.get("current_product_gate")!="BI-002"
            or supporting.get("product_gate_effect")!="NONE_BI002_REMAINS_ACTIVE_GAME_UNPROVEN"
            or supporting.get("execution_environment")!="LOCAL_AGENT_RUNTIME"
            or supporting.get("status")!="READY_FOR_LOCAL_ADMISSION_UNPROVEN"
            or supporting.get("dispatch")!=SUPPORTING_DISPATCH
            or supporting.get("runbook")!=SUPPORTING_RUNBOOK):
        raise HorizonError("SUPPORTING_WORLD_SENSOR_PRIORITY_LOST")
    forbidden=set(supporting.get("never_authorizes",()))
    for needed in ("GAME_SEND_INPUT","AUTO_RECLICK","PERSONAL_SAVE_ACCESS",
                   "OS_PERIPHERAL_MUTATION","BI002_CLOSE","PR159_TAKEOVER"):
        if needed not in forbidden:
            raise HorizonError("WORLD_SENSOR_SAFETY_BOUNDARY_LOST")
    return {"state":"PASS","stages":len(rows),"game_certification":"NOT_PROVED",
            "native_autonomy_policy":native["policy_merge"]["proof"],
            "native_adapter_status":status,"next_supporting_priority":SUPPORTING_ID}

def validate_dispatch(horizon,dispatch):
    """P04 machine dispatch must preserve BI-002 and single local game owner.

    This is a planning/routing validator only, never live-game certification.
    """
    supporting=horizon.get("next_supporting_priority",{})
    if (dispatch.get("schema")!="betterinstincts.sprint-dispatch/v1"
            or dispatch.get("current_gate")!="BI-002"
            or dispatch.get("next_supporting_priority")!=supporting.get("id")
            or dispatch.get("priority_contract")!="plans/horizon.v1.json#next_supporting_priority"):
        raise HorizonError("P04_DISPATCH_HORIZON_JOIN_MISMATCH")
    lanes=dispatch.get("lanes")
    if not isinstance(lanes,list) or any(not isinstance(x,dict) for x in lanes):
        raise HorizonError("P04_DISPATCH_LANES_INVALID")
    ids=[x.get("id") for x in lanes]
    if len(ids)!=len(set(ids)) or not {"GAME_HUNGER","WORLD_SENSOR","WORLD_OUTCOME","WORLD_INTEGRATE"}.issubset(ids):
        raise HorizonError("P04_DISPATCH_LANE_COVERAGE_LOST")
    by_id={x["id"]:x for x in lanes}
    graph={x["id"]:x.get("dependencies",[]) for x in lanes}
    for key,deps in graph.items():
        if not isinstance(deps,list) or any(d not in graph for d in deps):
            raise HorizonError("P04_DISPATCH_DANGLING_DEPENDENCY")
    visiting=set()
    visited=set()
    def walk_lane(key):
        if key in visiting:
            raise HorizonError("P04_DISPATCH_CYCLE")
        if key in visited:
            return
        visiting.add(key)
        for dep in graph[key]:
            walk_lane(dep)
        visiting.remove(key)
        visited.add(key)
    for key in graph:
        walk_lane(key)
    sensor=by_id["WORLD_SENSOR"]
    outcome=by_id["WORLD_OUTCOME"]
    integration=by_id["WORLD_INTEGRATE"]
    if by_id["GAME_HUNGER"].get("host")!="LOCAL_AGENT_RUNTIME":
        raise HorizonError("P04_HUNGER_HOST_OWNER_LOST")
    for lane in (sensor,outcome):
        if (lane.get("host")!="LOCAL_AGENT_RUNTIME"
                or lane.get("execution_environment")!="LOCAL_AGENT_RUNTIME"
                or "GAME_HUNGER" not in lane.get("serial_with",[])
                or not lane.get("expected_artifact","").startswith("dist/game-host/")):
            raise HorizonError("P04_LOCAL_GAME_HOST_OR_PRIVACY_LOST")
    if ("WORLD_SENSOR" not in outcome["dependencies"]
            or "WORLD_SENSOR" not in dispatch.get("launch_order",[])
            or dispatch.get("launch_order")!=["WORLD_SENSOR","WORLD_OUTCOME","WORLD_INTEGRATE"]
            or "WORLD_OUTCOME" not in integration["dependencies"]
            or integration.get("execution_environment")!="CURRENT_CHAT_RUNTIME"):
        raise HorizonError("P04_WORLD_SENSOR_EXECUTION_ORDER_LOST")
    if ("WORLD_OUTCOME" not in sensor.get("serial_with",[])
            or "WORLD_SENSOR" not in outcome.get("serial_with",[])):
        raise HorizonError("P04_SINGLE_CURSOR_OWNERSHIP_LOST")
    flags=dispatch.get("parallel_execution",{})
    if flags.get("active_game_graph_width")!=1 or flags.get("observed_parallelism") is not False:
        raise HorizonError("P04_PHANTOM_PARALLEL_GAME_AGENT")
    for lane in (sensor,outcome):
        forbidden=set(lane.get("forbidden",[]))
        if not any("peripheral" in x.lower() or "windows" in x.lower() for x in forbidden):
            raise HorizonError("P04_PERIPHERAL_PROTECTION_LOST")
    if integration.get("status")!="BLOCKED_ON_REAL_SENSOR_PROOF_AND_INDEPENDENT_PR159_OWNER":
        raise HorizonError("P04_PR159_COLLISION_GUARD_LOST")
    return {"state":"PASS","lanes":len(lanes),"current_gate":"BI-002",
            "next_supporting_priority":SUPPORTING_ID,
            "parallel_game_workers":0,"game_certification":"NOT_PROVED"}


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    horizon=json.loads((root/"plans/horizon.v1.json").read_text(encoding="utf-8"))
    dispatch=json.loads((root/SUPPORTING_DISPATCH).read_text(encoding="utf-8"))
    summary=validate(horizon)
    summary["p04_dispatch"]=validate_dispatch(horizon,dispatch)
    print(json.dumps(summary,sort_keys=True))
