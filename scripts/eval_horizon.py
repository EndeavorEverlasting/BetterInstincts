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
            if result is None or result.action!=need["action"]:
                raise AssertionError("NEED_PRIORITY_REGRESSION:"+need["id"])
            cases+=1
    assert choose(Context(default,("earn_income","enjoy_leisure"),income_due=True),cfg).action=="enjoy_leisure"
    assert choose(Context(default,("earn_income",),income_due=True,needs_game_certified=True),cfg).action=="earn_income"
    assert choose(Context(default,("practice_skill",),needs_game_certified=True,skill_goal_active=True),cfg) is None
    assert choose(Context(default,("practice_skill",),needs_game_certified=True,
                          income_game_observed=True,skill_goal_active=True),cfg).action=="practice_skill"
    cases+=4
    print(json.dumps({"state":"PASS","cases":cases,"proof_ceiling":"SYNTHETIC_OFFLINE_ONLY_NOT_GAMEPLAY"}))
if __name__=="__main__":
    main()
