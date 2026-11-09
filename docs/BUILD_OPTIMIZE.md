# Build yield microsystem (P95 + P124)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect; P124 readability (single owner, no second catalog daemon)

**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`

**Consultations:** `contracts/consultations/BI-BUILD-YIELD-MICROSYSTEM-20261108.v1.json`, `contracts/consultations/BI-COUNTERTOP-MECHANICS-20261108.v1.json`

**Trifecta:** P08 live apply / snap / bill-meter observation OPEN; P82 category pools + countertop seating falsifiers; P07 owns this seam.

## User outcomes
1. Host maintains a **per-category best-value pool** (walls, floors, windows, lighting, plumbing, appliances, decor, outdoor, counters, islands, barstools, …).
2. Pools cover **environment**, **neighborhood** (eco green/industrial), and **bills** (power/water) — moodlet/return yield, never aesthetics.
3. Ranking uses a **versioned attested catalog** — null bill axes skip bill pools (no fake zeros).
4. Household default remains `MAXIMIZE_YIELD`; dual Env+Green **2/2** walls (Veins of Gold / Working Bricks) stay the observed Env+Green floor.
5. **Countertop placement** is machine-readable: island overhangs admit **barstools only**; standard counters never snap seating; Env cap for counters/islands is **2**.

## Value axes
| Axis | Direction | Domain |
| --- | --- | --- |
| `lot_environment_gain` | higher | environment / Decorated moodlets |
| `eco_footprint_green` | higher | neighborhood Clean Air |
| `eco_footprint_industrial` | higher | opt-in Gross Air only |
| `combined_env_green` | higher (derived) | yield |
| `bill_power` / `bill_water` | lower | household utility bills |

## Countertop placement mechanics
| Rule | Meaning |
| --- | --- |
| `standard_counter` | No overhang → food prep / sink / small appliance only; seating never snaps |
| `island_counter` | Overhang edge → barstools snap; dining chairs never snap |
| Auto-Counters gear | Color-palette gear opens set shapes (island + corners) |
| Corner snap | Adjacent island tiles form L/U shapes on the grid |
| Env cap | Observed max Environment score on counters/islands = **2** |
| Career lock | Corporate Chic Env-2 set locks behind Culinary career level 2 |
| Unlock cheat | `testingcheats true` then `bb.ignoregameplayunlocksentitlement` |
| Default Env-2 islands | Harbinger / Real Flat / Immemorial (no cheat required) |

## Module map (P124)
| Surface | Owns |
| --- | --- |
| `contracts/build-optimize.v1.json` | Catalog, categories, axes, objectives, `placement_mechanics.countertops` |
| `rank_items` / `rank_axis` / `category_hierarchy` | Single-axis, objective, and ordered category dictionaries |
| `seating_snap_verdict` / `evaluate_countertop_plan` | Countertop seating gates + island setup receipt |
| `best_pools` / `evaluate_category_pools` | Microsystem pool receipt |
| `evaluate_build_optimize` | Objective plan (+ optional pools) |
| `scripts/build_optimize.py` | CLI `--pools` / `--hierarchy` / `--countertops` / rank / show-contract |
| `host_stack` | Attaches pools when `build_objective` supplied |

## Success call stack
```
operator/host query
  -> load contract
  -> filter packs + budget + unlocks
  -> best_pools / category_hierarchy
  -> seating_snap_verdict (when placing seating)
  -> optional evaluate_countertop_plan
  -> receipt BUILD_YIELD_POOLS_READY | BUILD_OPTIMIZE_PLAN_READY | COUNTERTOP_PLAN_READY
  -> execute_allowed=false
```

## CLI
```sh
python -m scripts.build_optimize --pools --owned-packs base,EP09,GP02,EP19,EP20
python -m scripts.build_optimize --objective MAXIMIZE_YIELD --category wall_covering --include-pools
python -m scripts.build_optimize --objective MAXIMIZE_BILL_SAVINGS --category appliance
python -m scripts.build_optimize --hierarchy --category counter_island --owned-packs base
python -m scripts.build_optimize --countertops --owned-packs base
python -m scripts.build_optimize --countertops --ignore-gameplay-unlocks
python -m scripts.build_optimize --show-mechanics
```

## P82 admission
- **Hypothesis:** Dual 2/2 walls head Env/Green/yield pools; efficient fridge/light head bill pools; null bill axes never win via implicit zero; industrial excluded from green/yield; island+barstool ALLOWs; standard+barstool and any dining chair DENY; default island hierarchy excludes Corporate Chic until unlocks ignored.
- **Measure:** `tests/test_build_optimize.py`
- **Decision:** KEEP if pools/snap match; expand catalog only with attested rows.

## Proof ceiling
Offline pools/mechanics ≠ live Build Mode place, barstool snap, Sim eat-at-counter pathing, or live bill/neighborhood meters. BI-002 hunger remains ACTIVE / GAME UNPROVEN.
