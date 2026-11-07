# P141 — strategic opportunity scout (refreshed 2026-11-06)

## Current facts
- Parent product gate remains **BI-002 hunger** (`plans/horizon.v1.json` `current_gate`); certified profiles **0**; live trials **0/5** vanilla and modified.
- Offline Mod Lab + bounded DBPF TGI index are on `main` (PR #7/#8/#9). Proof ceiling stays file metadata / index keys — not gameplay.
- Local Documents `GameVersion.txt` observed as `1.121.361.1020` (LOCAL_OBSERVED only). No Studio/install under common Program Files paths on this host → **BLOCKED_LOCAL_GAME_ACCESS** for BI-002.
- **Identity collision:** horizon/roadmap **BI-004 = recurring income**, while `plans/active/BI-004*` previously named the Mod Lab tooling sprint. `scripts/horizon_status.py` still emits `"income_gate":"BI-004"`. Agents conflating these IDs can mis-close gates.
- Prior 2026-10-20 scout selected hunger tuning; that product choice is unchanged. This refresh asks what deserves the **next offline investigation** while the game host is blocked.

## Design brief (tooling identity, not a UI)
- **Subject:** BetterInstincts lane labeling (horizon vs Mod Lab).
- **Audience:** local agents and maintainers reading plans/status JSON.
- **Job:** make income gate and Mod Lab impossible to conflate at a glance.
- **Upstreams (bounded):** `impeccable` — purpose clarity; `UP-A85AD9DC3` Diagram Design — lane storytelling; `UP-40FE662CF` no-mistakes — validate before push. No product chrome; IA/contracts only.

## Competing theses, falsification, and dispositions
| Thesis | Evidence | Leverage / timing | Cheapest disproof | Result |
| --- | --- | --- | --- | --- |
| A. Unblock BI-002 hunger on a real game host | Horizon `current_gate`, LIVE_CERT, zero trials | Highest product value | Game/Studio still absent | **SURVIVES as parent gate**; **BLOCKED** here — not the offline next mutation |
| B. Disambiguate Mod Lab sprint ID from horizon BI-004 income | Collision across ROADMAP, HORIZON, plans/active, handoff, status CLI | Stops wrong-gate closure; cheap; timing is now post-Mod Lab merge | If every consumer already names paths not IDs — falsified by `income_gate` + `plans/active/BI-004*` sharing the token | **SURVIVES; preferred next offline investigation** |
| C. Add cross-package TGI overlap candidates next | DBPF index now emits per-package keys | Natural Mod Lab depth | Without selected real Mods root / Studio compare, value is synthetic-only; overlaps are not conflicts | **DEFERRED** until B lands and an explicit Mods root is selected |
| D. Ship a Mod Lab GUI / dashboard | /design attached; CLI JSON exists | Visible product surface | Violates current “no cards/dashboard by default,” adds surface before game proof; AI-default risk | **REJECTED** as premature product chrome |
| E. Broad autonomy/scheduler rewrite offline | Horizon still unproven in game | Large future scope | Same rejection as 2026-10-20; external mods already target slices | **REJECTED** |

## Strategic choice
**B: rename the Mod Lab tooling lane to `BI-MODLAB` and keep horizon `BI-004` as income-only.** Confidence **HIGH** for the offline contract fix; does not claim game progress. Counterfactual: if a future tooling sprint needs a numeric ID, allocate outside BI-002…BI-008 (for example BI-009+) rather than reuse an income/skills/career gate.

Parent product recommendation remains **A** whenever a game-capable host and disposable save exist.

## Cheapest discriminating investigation
1. Move Mod Lab plans/dispatch/handoff to `BI-MODLAB*` and update references.
2. Add a regression that forbids an active Mod Lab dispatch sprint id equal to a horizon stage id.
3. Prove `python -m scripts.horizon_status` still reports `income_gate=BI-004` and `current_gate=BI-002`.
4. Leave BI-002 gameplay proof untouched.

**Route:** **P07** (bounded contract/docs/tests; strategic uncertainty resolved). Parallel **P124** on `betterinstincts/dbpf.py` readability only if behavior-preserving. Cross-package TGI overlap → later **P82** after explicit Mods root. Hunger → local game **P07/P08** when unblocked. This scout does not implement those successors beyond the selected B slice when a combined trifecta invocation authorizes immediate P07.
