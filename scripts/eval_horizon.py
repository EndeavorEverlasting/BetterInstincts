"""Offline scenario probe; never certifies game behavior."""
import json
from pathlib import Path
from betterinstincts.horizon import Context, choose
ROOT=Path(__file__).resolve().parents[1]
def main():
    cfg=json.loads((ROOT/"contracts/needs.v1.json").read_text())
    default={x["id"]:0.9 for x in cfg["needs"]}
    cases=0
    for need in cfg["needs"]:
        for level in (0.1, 0.45):
            state=Context({**default,need["id"]:level},(need["action"],"earn_income"),
                          needs_game_certified=True,income_due=True)
            result=choose(state,cfg)
            assert result and result.action==need["action"],need["id"]
            cases+=1
    print(json.dumps({"state":"PASS","cases":cases,"proof_ceiling":"OFFLINE_ONLY"}))
if __name__=="__main__":
    main()
