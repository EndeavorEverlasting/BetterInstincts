## 2026-11-14 — Career decisions can use the shared math umbrella

The career/event microservice now has access to `contracts/microsystem-math.v1.json` via `domain_cascade` as well as a direct per-service `evaluate_microsystem_math` adapter. The existing source-backed career-event risk selection and Work Hard welfare checks are still the default/fallback. A complete per-event activity DAG, continuous work/preparation time budget and source-matched Gaussian timing evidence may improve recommendations without changing the original response handler or overriding player-chosen tones. A new independently validated planner can earn selection through the same shared feasibility/holdout gate; no single method is imposed forever. See [MICROSYSTEM_MATH.md](MICROSYSTEM_MATH.md). The installed native EA career-event responder, real effect and rollback still require independent P08; GitHub source math is not an in-game answer.

# Career decision autonomy — Work panel and chance cards

**Parent objective:** BetterInstincts should independently handle routine careers and work-event decisions **inside The Sims 4**, without a human repeatedly choosing options or a desktop agent controlling the screen. Preserve player control. This is a **repository-owned policy implementation**, not yet an installed native-game responder or completed P08.

## The two very different career controls

| Surface | Actual owner | Scope |
| --- | --- | --- |
| **Bottom-right Career / Work panel** | `contracts/ui-microsystems.v1.json#panels.career` | Live mode, **J** hotkey. Shows work/school, daily task, shift, performance, requirements. Inspection actions remain uncalibrated for clickable pixel effects. |
| **Work-tone menu on Sim portrait** | `career_service.evaluate_work_shift_tone`; `docs/CAREER_PERFORMANCE.md` | Rabbit-hole `Work Hard` vs other tone; choose only with confirmed promotion opportunity, welfare and no player-owned tone; hand off attention to next eligible awake Sim after actual tone verified. |
| **Career chance-card/event overlay** | `career_service.evaluate_career_event_turn` → `career_decisions.evaluate_career_event` | **New** decision microsystem; distinct from Work Hard and from a universal YES/NO preference prompt. Event may arise while Sim works; offered option IDs and recipient are dialog-specific, not fixed buttons. |
| **Teen school/homework** | `career_service.evaluate_career_service` | Sticky homework obligations beside needs; continue after survival recovery, not treated as adult promotion. |
| **Green Technician daily task** | `career_service.evaluate_green_technician_daily_task` | Exact recipe/available Fabricator and Bits & Pieces, not a chance-card. |

A career event is a **game-event overlay**, not a button that permanently lives inside the J panel. The Career panel gives job context; the event itself needs a fresh, separate, source-attested event and response observation. Neither screenshot coordinates nor arbitrary popup order establish native response IDs.

## How autonomous choice should work once an EA-native responder is certified

```text
native career event (exact version, complete options, recipient and shift)
 → career_service.evaluate_career_event_turn
 → career_decisions.evaluate_career_event
 → player/queue/autonomy guards
 → verify each option's actual response ID and EA-sourced outcome branches
 → compare 10,000-basis-point outcome probabilities, benefits and risks
 → reject irreversible/job-loss options
 → select uniquely best risk-adjusted benefit if supported
 → native owner admits ONE response (future exact-patch game adapter)
 → independently observe response ACK, changed recipient effects, activity resume
 → no duplicate or uncertain-outcome replay
```

This permits automatic decisions for **known, complete** career events without asking an agent which button looks promising. The policy doesn't treat `Yes`, `No`, leftmost or highest compensation as universally best. Some events trade performance against money, relationships, reputation, mood, Fun or job loss. The versioned scoring model is intentionally replaceable through `contracts/career-decisions.v1.json`; choose source-observed best expected outcome, subject to a conservative downside penalty and strict irreversible risk exclusion. If one safe option remains, prefer it; if two safe choices are tied, effect data is incomplete, or the recipient/response IDs are uncertain, **HOLD rather than invent a correct answer**. A future reviewed game-native safe-default source can reduce unknown cases; do not confuse a blank screen with permission to guess.

**Autonomy is not an always-on desktop agent:** `autonomy_enabled` and player-control signals come from the future embedded game adapter. Once installed and certified, ordinary event policy may make in-game choices without a live ChatGPT/Windows agent, while explicit player actions, career tone choices, and the player's queue still take priority. No new background service, global key handler, or external mouse clicker is needed or supplied.

## Celebrity Endorsement after inventing a Smog Vacuum

The Civil Designer card shown with Get Famous has two disclosed choices.
**Get Endorsement** promises fame, career performance, and extra pay.
**Self Promote** describes gaining fans. Use the operator's choice of
**Get Endorsement** for this exact card when career autonomy is enabled and
the recipient permits fame gains. The displayed disclosure does not quantify
either fame gain, career progress, or cash. The existing numeric policy still
handles other career events.

The native observer must match the Civil Designer / Get Famous card, title,
Smog Vacuum subject, and both labeled disclosures using exact-build EA
evidence. Supply the normalized `disclosed_card` identity,
`card_source_ref`, and `fame_allowed`, plus the native response ID and
`disclosed_positive_effects` for each observed option. Tested sample IDs
are synthetic. Screen position and the work-shift payout notification
cannot establish a response ID or prove the endorsement reward.

`betterinstincts.career_response_port.CareerResponsePort` is the integration
point. The adapter supplies `read_career_event()` with the event, verified
build/scene/save scope, process instance, session, pause and player state.
On the game thread, `submit_if_current(request)` must recheck the player,
fame permission, scope, actual event/revision and response ID before
dispatching. The port reserves the attempt before that call. An ambiguous
return holds for reconciliation. An explicit no-effect refusal may be
retried only after a newer capture. Create one port per active runtime and
preserve the adapter's one-event response invariant across restarts.

On readback, correlate the native acknowledgement with the attempt and
dispatch references. Require separate event-attributed positive fame,
performance and cash deltas, followed by the closed card and return to
Live Mode after the same shift. A prior wage payment is independent of the
endorsement. There is no required return to an already completed shift.

The source path is exercised through an injected adapter. Installation and
live proof require the exact-build native event hook under
[#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).
On an authorized disposable household, verify a real offer, the game-side
response and rewards, the player/fame opt-out control, and ordinary career
card behavior. Preserve a running session and independently record the
native response and observed effects.

Focused test: `python -m unittest tests.test_career_endorsement -v`.

## Binding and receipts

**Input:** `betterinstincts.career-event.observation/v1`; exact `event_ref` + `event_revision`, recipient Sim ID as unsigned-64 decimal text, optionally different selected HUD Sim, household, career/shift, full native response-ID list, current capture, exact dialog tuning ID, and complete outcome sets per option (each probability in basis points summing to 10,000, source refs, bounded effects, job-loss/irreversibility flag). Native source strings alone are not authenticated by this policy—local EA source/hook inspection and observed capture provenance belong to installed-game acceptance.

**Output:** `RECOMMENDED_NATIVE_CHOICE` with a proposed specific response ID, expected utility and risk exclusions; **no input permit**. An event reference is non-repeatable across UI/event revisions after any response attempt or uncertain result. Successful response receipts retain the original revision and distinct response/effect/resumption capture references. Repeated or ambiguously dispatched event identity is held. For a runtime claim, use distinct current response, effect, and resumed-activity captures; `reconcile_career_event_turn` checks their normalized shapes but cannot authenticate a caller-fabricated `EA_NATIVE` receipt.

### Progressive-disclosure map

Start with only the four short `CAREER_PANEL_J`, `CAREER_EVENT_CHOICE`, `CAREER_WORK_TONE`, `CAREER_NATIVE_GATE` glossary definitions (lazy `betterinstincts.glossary.define` / `contracts/glossary.v1.json`). Follow exactly one source route for the question at hand:

- Career event options/benefit/risk: this document → `contracts/career-decisions.v1.json` → `betterinstincts/career_decisions.py` → `tests/test_career_decisions.py`
- Work Hard and selected-portrait handoff: `docs/CAREER_PERFORMANCE.md` → `career_service.py#evaluate_work_shift_tone`
- Child homework: `docs/CAREER_SERVICE.md` → `career_service.py#evaluate_career_service`
- Game-native hook/certification: `docs/NATIVE_GAMEPLAY_ARCHITECTURE.md` → issue #171, exact EA source/tuning IDs from local installed game
- UI panel and exact click calibration: `docs/UI_MICROSYSTEMS.md` → `contracts/ui-microsystems.v1.json`

This router keeps detailed contracts and thousands of glossary tokens out of the default conversation. Unknown popup types or new DLC routes should add **one evidence-grounded event adapter**, not a second choice policy or giant agent prompt.

## Sixth Gear source evidence and remaining P08

- **P141:** inspected existing Career J panel, `career_service` Work Hard and teen sticky homework; rejected generic clicker, hardcoded option preference, guessed EA IDs. Selected evidenced choice policy within current career owner.
- **P95:** complete event schema, risk-adjusted outcomes, native one-response hook seam, actor/shift/event identities, lazy discovery owners.
- **P82:** source adversarial tests for beneficial vs harmful, probability, irreversible risk, incomplete branches, player override, duplicate reply, wrong recipient, and separate response/effect/activity evidence. Existing `test_career_service` and `test_ui_microsystems` remain regression anchors.
- **P08:** local installed-game runtime is **NOT AVAILABLE through connected GitHub**. Real event hook IDs/response/options and package activation from installed `1.121.361.1020` (or exact running patch) require user-authorized disposable Sims trial. Do not invent TGI/EA APIs or claim a compiled native mod.
- **P07/P124:** repository-owned source contract, policy, tests, glossary, and existing career facade; true merge/main/CI only after provider receipts, not assumed. The local MoonWake stage walker/agent crew was **not run** via GitHub.

**Native acceptance:** with player-autonomy option enabled on disposable save, observe a real employment chance card for a known recipient (not necessarily selected portrait), validate actual tuning/options/effects, watch an in-game choice made by the installed native mod without a desktop agent, observe career changes and resumed work, repeat controlled variants, measure player takeover and rollback, and prove uninstall restores vanilla. Distinguish Work Hard effect and active career prompts from chance cards. BI-002 hunger and the separate preference-P08 trial remain independently owned.

Run `python -m unittest tests.test_career_decisions tests.test_career_service tests.test_ui_microsystems -v` plus full repo CI; source green is **not** GAME_CERTIFIED.
