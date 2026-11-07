# Build / Buy optimize program design (P95)

**Prompt:** TokenCorridor P95 — Program Design & Call-Stack Prototype Architect

**Provenance:** `spec-architecture-prompts.v1.json` blob `5926a198a14567de55110ed19e922fc444b4dec7`

**Trifecta:** P08 live apply remains evaluate-only until disposable Build Mode proof; P82 scored ranking; P07 owns this seam.

**/design upstreams:** `impeccable`, `UP-A85AD9DC3`, `UP-REDERIVE-2026-1103-01`, `mattpocock-wayfinder`, `UP-40FE662CF`

## User outcomes
1. Host can **deterministically** name the best wall covering / Buy item for a stated objective (Environment Gain, Green footprint, Industrial footprint, or yield Env+Green).
2. Ranking uses a **versioned catalog** of attested tooltip stats — not invented OCR and not “whatever looks nice.”
3. Automation **plans** Apply (Shift+whole-room) without fighting the player; execute stays gated on `HOST_MAY_AUTOMATE` + disposable lab + explicit session.
4. Green vs Industrial are **mutually exclusive objectives** — household default is `MAXIMIZE_YIELD` (Decorated + Clean Air moodlets). Aesthetics are never a ranking factor.
5. Current LOCAL_OBSERVED dual max floor: **Veins of Gold Marble Walls** and **Working Bricks** (Env 2 + Green 2).

## Governance vs harness vs program
| Layer | Owns |
| --- | --- |
| Governance | Player first; save-safe; no install auto-discovery; BI-002 hunger still the live product gate |
| Harness | unittest, doctrine REQUIRED paths, FakeGui CI |
| Program | `build_optimize` ranking + `contracts/build-optimize.v1.json` catalog |
| Live adapters | future `scripts/build_optimize --execute` only after P08 Build Mode proof |

## Domain vocabulary
| Term | Meaning |
| --- | --- |
| **LOT_ENVIRONMENT_GAIN** | Per-panel décor contribution toward room Environment Score / Decorated moodlets |
| **ECO_FOOTPRINT_GREEN** | Lot contribution toward neighborhood Clean Air (Eco Lifestyle) |
| **ECO_FOOTPRINT_INDUSTRIAL** | Lot contribution toward smog / Gross Air (opt-in storytelling) |
| **WALL_COVERING** | Build Mode wall paint; stacks per wall panel |
| **BUILD_CATALOG_ITEM** | Rankable wall or Buy object row with attested stats |
| **MAXIMIZE_ENV / MAXIMIZE_GREEN / MAXIMIZE_INDUSTRIAL / BALANCED_ENV_GREEN** | Ranking objectives |
| **BUILD_OPTIMIZE_PLAN** | Evaluate-only receipt with ordered picks + apply technique note |

## Module map
| Module | Responsibility | Side effects |
| --- | --- | --- |
| `contracts/build-optimize.v1.json` | Catalog + objectives + policies | none |
| `betterinstincts/build_optimize.py` | Filter, rank, stack project, evaluate plan | none |
| `scripts/build_optimize.py` | CLI evaluate / show-contract | stdout only |
| `host_stack` | Optional compose when `build_objective` supplied | none |

## Success call stack (evaluate-only)
```
operator/host query (objective, packs, budget, panels)
  -> build_optimize.evaluate_build_optimize
  -> filter owned packs + budget + category
  -> exclude industrial from green/balanced (and green from industrial)
  -> rank by primary score, then cost, then name
  -> project stacking × panels
  -> receipt: BUILD_OPTIMIZE_PLAN_READY (execute_allowed=false)
```

## Failure / abstention stacks
| Case | State / gate |
| --- | --- |
| Player-directed | `YIELD_TO_PLAYER` |
| Not in Build/Buy context | `BUILD_OR_BUY_REQUIRED` |
| No eligible items after filters | `ABSTAIN_NO_ELIGIBLE_ITEMS` |
| Unknown objective | `BuildOptimizeError` fail-closed |
| Live paint without session | Forbidden — plan only |

## Competing designs (P95 widen-then-converge)
| Candidate | Verdict |
| --- | --- |
| A. Tooltip OCR every paint | Rejected — flaky; catalog is authority |
| B. Hard-code one “best” wallpaper | Rejected — packs/budget/objective differ |
| C. Versioned catalog + deterministic rank | **Selected** — testable offline; expandable with LOCAL_OBSERVED rows |
| D. Immediate SendInput painter | Deferred — P08 disposable Build Mode proof required |

## P82 admission
- **Hypothesis:** With Spa Day + Enchanted packs owned, `MAXIMIZE_ENV` prefers Environment Gain 2 coverings over Brick & Plaster (env 1); `MAXIMIZE_GREEN` prefers Log Siding (green 2) and excludes industrial Brick & Plaster; `BALANCED_ENV_GREEN` excludes industrial.
- **Measure:** `tests/test_build_optimize.py`
- **Decision rule:** KEEP seam if rankings match; expand catalog only with attested rows.

## Design tokens (operator receipt / future overlay — not a SaaS dashboard)
- Palette: lot-night glass `#0E1A22`, rain teal `#2F6F7A`, brick clay `#8B4A3B`, clean-air lime `#A7C4A0`, industrial soot `#3A3A3A`
- Type: tabular data in system mono for scores; UI chrome deferred until live overlay sprint
- Principle: one composition = ranked pick + why (objective score + stacking), not a card grid of every wallpaper

## Proof ceiling
Offline ranking ≠ live Build Mode apply. BI-002 hunger remains ACTIVE / GAME UNPROVEN. Eco Lifestyle neighborhood effects are documented gameplay knowledge until LOCAL_OBSERVED green/industrial meters are captured on the lab lot.
