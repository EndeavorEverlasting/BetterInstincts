# Host budget & needs-item securing (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect
**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`
**Vocabulary:** [GLOSSARY.md](GLOSSARY.md) · Autonomy parent: [HOST_AUTONOMY.md](HOST_AUTONOMY.md)

## User outcomes
1. Host **secures** cheapest adequate objects for critical needs before wasting autonomy on fluff.
2. With low funds (LOCAL_OBSERVED lab ~§638 after sleep surface purchase), host **refuses** autonomous discretionary Build/Buy below the §1,000,000 reserve.
3. Judgment balances **needs → mood recovery → income → skills** without bankrupting the disposable household.
4. Player-directed purchases still win (`PLAYER_FIRST`).

## Domain vocabulary (new)
`HOUSEHOLD_FUNDS`, `EMERGENCY_RESERVE`, `SOFT_BUDGET_FLOOR`, `NEED_OBJECT_GAP`, `SECURE_NEED_OBJECT`, `HOLD_PURCHASE`, `BUDGET_LOCKDOWN`, `CHEAPEST_ADEQUATE`, `EARN_BEFORE_SPEND`.

## Priority (invariant with doctrine/horizon)
1. Player direction
2. Viewport / presence yield
3. Critical need **use** if object already owned (MAP_TRAVEL home — not walk thrash)
4. **SECURE_NEED_OBJECT** only if gap + affordable after reserve
5. Moodlet relief that is free/cheap (shower if owned, talk, etc.)
6. `earn_income` when funds are below the household minimum and needs not critically blocked
7. Skills only after needs objects exist and funds ≥ soft floor (horizon order)

## Module map
| Module | Owns |
| --- | --- |
| `contracts/host-budget.v1.json` | Floors, catalog prices, purchase policy |
| `budget_eval` | Gap detection, affordability, purchase/hold/earn plan |
| `instincts_host.NEED_OBJECTS` | Which object classes satisfy which need |
| `host_stack` | Gates `SECURE_NEED_OBJECT` / `BUDGET_LOCKDOWN` / `EARN_BEFORE_SPEND` |
| Build/Buy scripts (later) | Live catalog clicks — not claimed by this offline slice |

## Success call stack
```
observation(funds, needs, owned_objects, moodlets?)
  -> budget_eval.evaluate
  -> if NEED_OBJECT_GAP and AFFORDABLE: SECURE_NEED_OBJECT (CHEAPEST_ADEQUATE)
  -> elif NEED_OBJECT_GAP and NOT_AFFORDABLE: HOLD_PURCHASE + EARN_BEFORE_SPEND or MAP_TRAVEL to use community/home
  -> elif funds < EMERGENCY_RESERVE: BUDGET_LOCKDOWN (no Buy)
  -> else host_stack / instincts as today
```

## Failure stacks
| Failure | Response |
| --- | --- |
| Autonomous discretionary Buy would leave less than §1,000,000 | `HOLD_PURCHASE` |
| Duplicate object class already owned | skip secure |
| Critical gap, unaffordable | earn / travel / community — never luxury Buy |
| Player in Build/Buy | `YIELD_TO_PLAYER` |

## Proof ceiling
Offline budget plans are **not** live catalog proof. LOCAL_OBSERVED prices (fridge §215, etc.) are hints. Exact bed SKU/price from the operator's sleep-surface purchase should be recorded into the catalog when known. GAME_CERTIFIED income remains BI-004.

## Household minimum and growth

`contracts/host-budget.v1.json#floors.minimum_household_balance` owns the
§1,000,000 minimum. The budget evaluator reports spendable surplus, shortfall
and the earned income goal. Emergency and soft thresholds still describe
immediate urgency. This floor governs autonomous discretionary recommendations
from the shared budget and upkeep procurement policies. Player-directed
purchases and bill obligations retain their existing behavior.

The growth goal uses earned gameplay proceeds above the floor. The verified
last-resort laundry console top-up is a subsidy and carries no earned income
credit. The generic budget does not automatically run a cheat when funds drop.
