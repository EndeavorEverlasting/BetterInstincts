# Build yield microsystem (P95 + P124)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect; P124 readability (single owner, no second catalog daemon)

**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`

**Consultation:** `contracts/consultations/BI-BUILD-YIELD-MICROSYSTEM-20261108.v1.json`

**Trifecta:** P08 live apply / bill-meter observation OPEN; P82 category pools + bill falsifiers; P07 owns this seam.

## User outcomes
1. Host maintains a **per-category best-value pool** (walls, floors, windows, lighting, plumbing, appliances, decor, outdoor, …).
2. Pools cover **environment**, **neighborhood** (eco green/industrial), and **bills** (power/water) — moodlet/return yield, never aesthetics.
3. Ranking uses a **versioned attested catalog** — null bill axes skip bill pools (no fake zeros).
4. Household default remains `MAXIMIZE_YIELD`; dual Env+Green **2/2** walls (Veins of Gold / Working Bricks) stay the observed Env+Green floor.

## Value axes
| Axis | Direction | Domain |
| --- | --- | --- |
| `lot_environment_gain` | higher | environment / Decorated moodlets |
| `eco_footprint_green` | higher | neighborhood Clean Air |
| `eco_footprint_industrial` | higher | opt-in Gross Air only |
| `combined_env_green` | higher (derived) | yield |
| `bill_power` / `bill_water` | lower | household utility bills |

## Module map (P124)
| Surface | Owns |
| --- | --- |
| `contracts/build-optimize.v1.json` | Catalog, categories, axes, objectives |
| `rank_items` / `rank_axis` | Single-axis and objective ranking |
| `best_pools` / `evaluate_category_pools` | Microsystem pool receipt |
| `evaluate_build_optimize` | Objective plan (+ optional pools) |
| `scripts/build_optimize.py` | CLI `--pools` / rank / show-contract |
| `host_stack` | Attaches pools when `build_objective` supplied |

## Success call stack
```
operator/host query
  -> load contract
  -> filter packs + budget
  -> best_pools (per category × axis)
  -> optional rank_items(objective, category)
  -> receipt BUILD_YIELD_POOLS_READY | BUILD_OPTIMIZE_PLAN_READY
  -> execute_allowed=false
```

## CLI
```sh
python -m scripts.build_optimize --pools --owned-packs base,EP09,GP02,EP19,EP20
python -m scripts.build_optimize --objective MAXIMIZE_YIELD --category wall_covering --include-pools
python -m scripts.build_optimize --objective MAXIMIZE_BILL_SAVINGS --category appliance
```

## P82 admission
- **Hypothesis:** Dual 2/2 walls head Env/Green/yield pools; efficient fridge/light head bill pools; null bill axes never win via implicit zero; industrial excluded from green/yield.
- **Measure:** `tests/test_build_optimize.py`
- **Decision:** KEEP if pools match; expand catalog only with attested rows.

## Proof ceiling
Offline pools ≠ live Build Mode apply or live bill/neighborhood meters. BI-002 hunger remains ACTIVE / GAME UNPROVEN.
