"""Pure offline six-needs -> income -> skills decision prototype; NEVER queues gameplay."""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Optional, Tuple

SIX_NEEDS=frozenset(("hunger","bladder","energy","hygiene","fun","social"))
OTHER_ACTIONS=frozenset(("earn_income","practice_skill","enjoy_leisure"))

class PolicyError(ValueError):
    pass

@dataclass(frozen=True)
class Context:
    needs: Mapping[str,float]
    available_actions: Tuple[str,...]
    player_directed: bool=False
    already_busy: bool=False
    autonomy_enabled: bool=True
    supported_life_stage: bool=True
    cooldown_actions: Tuple[str,...]=()
    needs_game_certified: bool=False
    income_game_observed: bool=False
    income_due: bool=False
    skill_goal_active: bool=False

@dataclass(frozen=True)
class Choice:
    action: str
    reason: str
    domain: str

def validate_rules(cfg):
    if not isinstance(cfg,dict) or cfg.get("schema")!="betterinstincts.needs/v1":
        raise PolicyError("BAD_NEED_SCHEMA")
    rows=cfg.get("needs")
    if not isinstance(rows,list) or len(rows)!=6:
        raise PolicyError("SIX_NEEDS_REQUIRED")
    if any(not isinstance(r,dict) or not isinstance(r.get("id"),str) or
           not isinstance(r.get("action"),str) for r in rows):
        raise PolicyError("INVALID_NEED_RULE")
    names=[r["id"] for r in rows]
    actions=[r["action"] for r in rows]
    if set(names)!=SIX_NEEDS or len(set(names))!=6:
        raise PolicyError("MISSING_OR_DUPLICATE_NEED")
    if len(set(actions))!=6 or any(not x.isidentifier() or x in OTHER_ACTIONS for x in actions):
        raise PolicyError("INVALID_ACTIONS")
    a,b=cfg.get("urgency_threshold"),cfg.get("preemptive_threshold")
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v) for v in (a,b)):
        raise PolicyError("BAD_THRESHOLDS")
    if not 0<a<b<1:
        raise PolicyError("THRESHOLD_ORDER")
    return tuple((r["id"],r["action"]) for r in rows)

def choose(state:Context,cfg:dict)->Optional[Choice]:
    rules=validate_rules(cfg)
    if not state.autonomy_enabled or state.player_directed or state.already_busy or not state.supported_life_stage:
        return None
    if set(state.needs)!=SIX_NEEDS:
        return None  # unknown ghost/toddler/missing motive: do not guess
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v) or not 0<=v<=1
           for v in state.needs.values()):
        raise PolicyError("INVALID_NEED_VALUE")
    if not all(isinstance(a,str) for a in state.available_actions+state.cooldown_actions):
        raise PolicyError("INVALID_ACTION_NAME")
    eligible=set(state.available_actions)-set(state.cooldown_actions)
    due=sorted((state.needs[need],i,need,action) for i,(need,action) in enumerate(rules)
               if state.needs[need]<cfg["preemptive_threshold"])
    for value,_,need,action in due:
        if action in eligible:
            tag="urgent_" if value<cfg["urgency_threshold"] else "proactive_"
            return Choice(action,tag+need,"needs")
    if due:
        return None  # no remedy: no work or skill while needs unmet
    if state.needs_game_certified:
        if state.income_due and "earn_income" in eligible:
            return Choice("earn_income","eligible_income_opportunity","income")
        if state.income_game_observed and state.skill_goal_active and "practice_skill" in eligible:
            return Choice("practice_skill","eligible_skill_opportunity","skills")
    if "enjoy_leisure" in eligible:
        return Choice("enjoy_leisure","safe_uncommitted_time","leisure")
    return None
