"""Read-only machine status for the long-term BetterInstincts sequence.

No game access, no assumption that a green PR proves a playable mod.
"""
import json
from pathlib import Path
from scripts.check_horizon import validate
from betterinstincts.compatibility import load_catalog

ROOT=Path(__file__).resolve().parents[1]

def status(root=ROOT):
    horizon=json.loads((root/"plans/horizon.v1.json").read_text())
    validate(horizon)
    catalog=load_catalog(root)
    certified={(p["module"],p["game_version"],p["platform"]) for p in catalog["profiles"]
               if p["status"]=="certified"}
    return {"parent":"BetterInstincts","current_gate":horizon["current_gate"],
            "next_work":"Finish actual BI-002 hunger game A/B and rollback",
            "after_hunger":["BI-003A","BI-003B","BI-003C","BI-003D","BI-003E"],
            "balance_gate":"BI-003F","income_gate":"BI-004","skills_gate":"BI-005",
            "certified_module_patch_combinations":len(certified),
            "closure":"UNPROVEN_GAME_HOST" if not certified else "REVIEW_GAME_EVIDENCE",
            "proof_ceiling":"REPO_CONTRACTS_ONLY"}

if __name__=="__main__":
    print(json.dumps(status(),sort_keys=True))
