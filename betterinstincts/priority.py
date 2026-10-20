"""Deterministic OFFLINE autonomy recommendation prototype.

No Sims API imports; never queues actions, writes files, or modifies saves.
Game integration and eligibility rules require separate live proof.
"""
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

NEED_ACTIONS = (
    ("hunger", "eat"),
    ("bladder", "use_toilet"),
    ("energy", "sleep"),
    ("hygiene", "shower"),
)
URGENT_BELOW = 0.35

@dataclass(frozen=True)
class SimSnapshot:
    needs: Mapping[str, float]
    available_actions: Tuple[str, ...]
    player_directed: bool = False
    autonomy_enabled: bool = True
    aspiration: str = "balanced"  # balanced | income | career

@dataclass(frozen=True)
class Suggestion:
    action: str
    reason: str

def suggest(snapshot: SimSnapshot) -> Optional[Suggestion]:
    """Suggest one eligible action; return None rather than force or invent one."""
    if not snapshot.autonomy_enabled or snapshot.player_directed:
        return None
    if snapshot.aspiration not in ("balanced", "income", "career"):
        raise ValueError("unsupported aspiration")
    for key, value in snapshot.needs.items():
        if not isinstance(value, (float, int)) or not 0 <= value <= 1:
            raise ValueError("needs must be in [0, 1]: " + key)

    options = set(snapshot.available_actions)
    urgent = []
    for index, (need, action) in enumerate(NEED_ACTIONS):
        value = snapshot.needs.get(need)
        if value is not None and value < URGENT_BELOW and action in options:
            urgent.append((value, index, action, need))
    if urgent:
        _, _, action, need = min(urgent)
        return Suggestion(action, "urgent_" + need)

    intent = {"income": "earn_income", "career": "career_prep"}
    candidate = intent.get(snapshot.aspiration)
    if candidate in options:
        return Suggestion(candidate, "optional_" + snapshot.aspiration)
    if "enjoy_leisure" in options:
        return Suggestion("enjoy_leisure", "no_urgent_need")
    return None

if __name__ == "__main__":
    sample = SimSnapshot(needs={"hunger": 0.15, "energy": 0.80},
                         available_actions=("eat", "career_prep", "enjoy_leisure"),
                         aspiration="career")
    print(suggest(sample))
