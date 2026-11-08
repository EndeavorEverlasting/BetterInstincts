# Canonical TokenCorridor prompt invocations — 2026-10-20

Do not treat this as a local Prompt Kit or substitute repository. Source of truth: private **EndeavorEverlasting/TokenCorridor**, file `harness/exports/prompt-invocation-catalog.v1.json`, fetched at blob SHA `8c281379ba7ccc871947391233b1db72f4a108ef`. TokenCorridor canonical invocation resolver: `scripts/prompt_invocation_resolver.py`; IDs were selected using exact catalog matches, not inferred from titles.

| ID | Verified title | Canonical prompt definition owner | Source blob SHA | Invoked in BI-001 as |
| --- | --- | --- | --- | --- |
| P07 | Repo Sprint Executor | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | Implement, validate, commit, PR, integrate scoped horizon code |
| P82 | Prototype-Measure-Refine Delivery Loop | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | Six-needs policy hypothesis, measurable offline prototype; `docs/HORIZON_DECISIONS.md` |
| P01 | Harness Infrastructure Builder | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | 2026-11-07 ontology preflight and CI operational infrastructure — `scripts/semantic_preflight.py`, `scripts/check_ontology.py` |
| P00 | Governance Doctrine Installer | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | AGENTS.md, docs/DOCTRINE.md, validator and CI: multiversion preservation |
| P97 | Open-Source Prior-Art & Gap Analyst | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | docs/PRIOR_ART.md: reference implementation, gap map and adoption decisions |
| P141 | Repository Strategic Opportunity Scout | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | docs/STRATEGY.md: compare/falsify competing theses, select next investigation |
| P04 | [PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor | `src/tokencorridor/interface/promptkit/registry/base/prompts.json` | `848728632c1243ebba023fa0012292a2ad33cada` | plans/active/BI-001.md: runtime partition, safe owner lanes, proof/gates |
| P95 | Program Design & Call-Stack Prototype Architect | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-08 aspiration microsystem (`docs/ASPIRATION_SERVICE.md`) + career microsystem (`docs/CAREER_SERVICE.md`) + camera-safe traverse (`docs/CAMERA_TRAVERSE.md`) + library-save-before-room-mutate (`docs/BUILD_LIBRARY_CHECKPOINT.md`) + build spatial/integrity/house-state + prior need services |
| P83 | Agent Work Verifier & Iterative Advancer | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-08 verify Bargain Bend destruction claims then harden Build mechanisms |
| P78 | Repository Glossary & Documentation Diet | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-07 preserve existing `contracts/glossary.v1.json` as vocabulary owner and `contracts/ontology.v1.json` as graph owner |

| P67 | Repository Eval Framework Builder | `src/tokencorridor/interface/promptkit/registry/prompts/ai-engineering-level-up-prompts.v1.json` | `5350ce61085e748ab219fa482e25d70517b10e0f` | 2026-11-07 progression/CI honesty eval pyramid — see docs/PROGRESSION_EVAL.md |
| P62 | Skill Correctness and Efficiency Eval Implementer | `src/tokencorridor/interface/promptkit/registry/prompts/skill-development-prompts.v1.json` | `7ef8e6991f558db191989c495d9255a282f88ba9` | 2026-11-07 vision/scaffolding/product rates + forbidden promotion cases — see `betterinstincts/progression_eval.py` |
| P124 | Repository Code Readability & Structural Refactorer | `src/tokencorridor/interface/promptkit/registry/prompts/spec-architecture-prompts.v1.json` | `5926a198a14567de55110ed19e922fc444b4dec7` | 2026-11-07 `need_service_base` + domain_cascade poll bus + need-services registry; Navigating Needs peer owner; prior: moodlets/event_balance |

**Resolution is not execution.** Artifacts prove these workflows were applied to this initial sprint; no TokenCorridor CLI execution, full compliant remote parallel-worker receipt, or installed `/trifecta` skill is claimed. In BI-001 the branch-writer is one GitHub provider lane. Do not copy proprietary/private Prompt Kit contents into this public repository; this file contains only invocation identities and evidence pointers. Refresh exact provenance from TokenCorridor on subsequent work instead of trusting this snapshot indefinitely.

## 2026-11-08 aspiration microsystem trifecta

**P95** designed sticky `ASPIRATION_SERVICES_TANDEM` beside need/career services for
OK/Cancel judgment on aspiration and life-state dialogs (Mother Nature / Fairy).
**P82** measured disabled-Cancel, occult-unready-Cancel, and sticky-prompt falsifiers
in `tests/test_aspiration_service.py`. **P08** live Cancel on the Mother Nature dialog
remains OPEN on the local game host. **P07** owns implementation/integration of
`aspiration_service` + host wiring. Consultation predates mutation:
`contracts/consultations/BI-ASPIRATION-MICROSYSTEM-20261108.v1.json`.

## 2026-11-08 career microsystem trifecta

**P95** designed sticky `CAREER_SERVICES_TANDEM` beside need_services for teen homework
continuity. **P82** measured suspend/resume/complete falsifiers in
`tests/test_career_service.py`. **P08** live homework completion remains OPEN on the
local game host (offline proof only). **P07** owns implementation/integration of
`career_service` + host wiring. Consultation predates mutation:
`contracts/consultations/BI-CAREER-MICROSYSTEM-20261108.v1.json`.

## 2026-11-07 exact invoked order

Current Moonwake catalog read at `harness/exports/prompt-invocation-catalog.v1.json` and current root `AGENTS.md`: **P97 — Open-Source Prior-Art & Gap Analyst** (`spec-architecture-prompts.v1.json`, blob `5926a198a14567de55110ed19e922fc444b4dec7`) → **P95 — Program Design & Call-Stack Prototype Architect** (same owner/blob) → Trifecta sequence **P08 live proof → P82 measured prototype → P07 bounded implementation**, with real Windows runtime proof deferred to local host rather than forged in CI; then **P04 [PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor** (`base/prompts.json`, blob `848728632c1243ebba023fa0012292a2ad33cada`) for local-agent ownership/handoff. The P97/P95/P82/P07 implementable offline work and tests are in `docs/JUDGMENT_LEARNING.md`; P08 remains a separately observable game task. Do not equate canonical prompt identity retrieval with a live launch of a local agent.

## 2026-11-07 ontology-first semantic sprint and final P04

Moonwake current source `AGENTS.md`, deterministic resolver `scripts/prompt_invocation_resolver.py`, and exact exported 144-prompt catalog `harness/exports/prompt-invocation-catalog.v1.json` (blob `8c281379ba7ccc871947391233b1db72f4a108ef`) were read. Actual applied order: **P00 governance** → **P01 harness** → **P141 strategic alternatives** → **P124 ownership/readability** → **P95 thin evaluate-only architecture** → **P78 glossary authority**, with Trifecta's current-runtime P82/P07 verification/integration and real-game P08 deferred to the local host. **Only after source integration** was **P04** created as `docs/handoff/BI-SEMANTIC-ONTOLOGY-P04-2026-11-07.md` and its typed execution plan. PR #57 merged to `main` `091fa6d2ae49de54fd3536b8f7aa6913006df49d`; post-merge CI run `42423191457` passed. The P04 handoff records game trial and maintainer review as unproven. Moonwake's generic parallel-dispatch CLI and schema were not found at the documented paths in current `main`, so its invocation/execution is **not** asserted; the BetterInstincts typed plan is the local agent transport.

## 2026-11-07 P04 — hidden-item operator playbook routing

P04 remains the canonical Moonwake **[PARALLEL] Repo-Aware Sprint + Harness Factoring Distributor**, *not* an invented Sims-specific prompt. BetterInstincts `AGENTS.md` now requires every P04 inventory to inspect `plans/active/BI-HIDDEN-OBJECTS.P04.md` and run `python -m scripts.hidden_object_discovery guide` to retrieve the canonical five-step recipe. The machine dispatch `plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json` owns local-host work placement; `python -m scripts.hidden_object_discovery audit --observation dist/game-host/hidden-object-p04-receipt.json` enforces receipt shape; CI `scripts/check_hidden_object_p04.py` guards the route and ordered instructions. This applies directly when the parent objective concerns hidden items; otherwise it is inventoried/deferred rather than creating a side quest. These are repository contracts, **not** a verified invocation of Moonwake's own agent dispatcher or a claim that a Windows game session was accessed.
