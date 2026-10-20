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
    return {"state":"PASS","stages":len(rows),"game_certification":"NOT_PROVED"}

if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    print(json.dumps(validate(json.loads((root/"plans/horizon.v1.json").read_text()))))
