# Async lot opportunity survey — needs, careers, hover memory

**Status:** implemented in the opt-in host listener and bounded asynchronous coordinator, **offline-only**. It is not a playable mod, a calibrated screen recognizer, or evidence of live Sims 4 traversal.

## Terminal user value

As an active Sim works through an action queue, BetterInstincts can **continue discovering and evaluating** the observed lot's opportunities for needs and career goals. It does not discard that work when the player uses the mouse or a Sim's queue fills up. When the player is idle, a verified client adapter can request an idle exploration of a *known, current* room/object, hover once to discover a previously unknown affordance, and store its token identity in a durable, bounded local index. Future matching patch/lot surveys do not schedule rediscovery of that same tooltip.

This is deliberately not autonomous mouse seizure or filling a queue blindly. **Player play and current responsibilities outrank exploration.**

## Architecture (P95)

| Owner | One responsibility |
| --- | --- |
| `betterinstincts/house_state.py` | Current observed lot entities and revisions |
| `betterinstincts/room_census.py` | Attested room, floor, enclosure and object classification |
| `betterinstincts/opportunity_survey.py` | Rank bounded needs/career opportunities from supplied observations; identify unknown targets |
| `betterinstincts/queue_capacity.py` | Conservative 2/6 occupancy admission; unknown means no new enqueue |
| `betterinstincts/hover_learning.py` | Validate opt-in semantic tooltip/action/review events and time-window associations |
| `betterinstincts/affordance_memory.py` | Atomic patch-and-lot-scoped cross-session candidate catalog under ignored `dist/host-listener/` |
| `betterinstincts/host_listener.py` | Every active-session tick, including player-yield, emits read-only survey receipt |
| `betterinstincts/host_tandem.py` | Bounded async observation callback loop and optional single idle-exploration staging |
| `betterinstincts/workflow_interop.py` | Existing two-probe idle, exclusive desktop lock, pre-effect checkpoint and deferred queue |

No second room store, global input hook, new background daemon, automatic source edits, or independent screen scheduler.

## Two concurrent lanes

**Passive lane (always when the listener is activated):** Incoming sanitized `needs`, `queue`, `lot_model`, `active_lot_id`, `game_version`, `survey_goals`, `occupied_objects`, `multitasking`, and `capture_ref` are evaluated against attested objects. A player-active or busy queue tick still returns `opportunity_survey` with room classifications, domain candidates, and hover targets to investigate later. No cursor traversal, interruption, cancel, or enqueue takes place.

**Idle exploration lane (explicit adapter):** When a player-idle probe and scene-backed Live context exist, the survey may emit `IDLE_EXPLORATION_CANDIDATE`. The async coordinator can stage a single `CooperativeScreenQueue.QueuedStep` with an explicitly supplied navigation/hover adapter. The queue double-probes desktop presence and uses the exclusive desktop lock, then independently checks a fresh capture, game build, actor, exact lot ID, model revision, room, object and followed camera. The adapter **must call `checkpoint()` before each input** and follow the existing bounded camera-traverse/finally-restore contract. A changed or unverified scene requires reobservation and makes no input. The branch introduces no unconditional live input driver.

## Learning is persistent but evidence-qualified

`python -m scripts.host_listener hover --session-id ID --event EVENT.json --explicit-opt-in --game-version 1.121.361.1020 --lot-id LOT` records approved tokenized `tooltip_visible`, `action` and `outcome` events through `observe_hover`. The event source is validated by `hover_learning` (no raw tooltip text), then a compact index is atomically updated at `dist/host-listener/affordance-memory.v1.json`. It holds at most **128** entries, **512** seen-event IDs and **64** in-flight associations in at most **128 KB**. Each entry has a patch, target, tooltip, observed lots, seen count, any matched action refs and independently reviewed helpful/harmful counts. After at least three matched helpful reviewed outcomes and 75% success, it marks a *reviewed association*, **not a proven causal game mechanic or a click permit**.

When a matching `game_version` and `active_lot_id` appear on later sessions, the survey can skip hover rediscovery for previously observed targets. An unknown patch/lot keeps learning as unqualified candidates but does not block necessary fresh discovery. A lost index write reports `AFFORDANCE_INDEX_REPAIR_REQUIRED`, rather than pretending persistence succeeded. The session hover event log remains the source for manual recovery.

The canonical **semantic vocabulary** remains tracked in `contracts/glossary.v1.json`, with `PASSIVE_LOT_SURVEY`, `LOT_OPPORTUNITY_CANDIDATE`, `HOVER_AFFORDANCE_MEMORY`, `IDLE_EXPLORATION_CANDIDATE`, `MODEL_REVISION_REVALIDATION`, `QUEUE_PREDICTIVE_HINT` and `OBSERVED_HOVER_VS_REVIEWED_UTILITY`. Dynamic in-game observations belong to the bounded local index, not automatic Git commits or unreviewed rewrites of the canonical glossary. An agent may submit verified new semantic definitions for repository review after gathering evidence.

## Usage

1. Opt in: `python -m scripts.host_listener activate --session-id survey-lab`.
2. Feed current-snapshot JSON through `python -m scripts.host_listener tick --session-id survey-lab --observation observation.json --process-id PID`. A proper presence probe is needed for idle admission; no probe still yields passive survey with no control.
3. Pass a trustworthy async `observe` callback to `run_opportunity_survey_session(session_id, actor_ref, observe=..., probe=...)` to keep gathering observations while the active user plays. No timer or observation source is started by importing the module. This runner is bounded to the session's remaining tick budget.
4. To actually explore, provide the existing `CooperativeScreenQueue` plus a separately verified local navigation adapter and `observe_fresh` callback. Merely emitting `IDLE_EXPLORATION_CANDIDATE` grants no input rights. The adapter must revalidate after each camera traversal and restore follow.
5. Submit tokenized tooltip observations through the `hover` CLI as above; re-run a survey to see deduplication.
6. End: `python -m scripts.host_listener deactivate --session-id survey-lab`.

The source of game observations, process lifetime, actual Windows hover sensing and physical interaction are a **P08 live test and adapter** requirement. Running the above offline CLI against a JSON file is not automatic gameplay capture. Existing installed game patches and protected saves remain untouched.

## P124 factoring / Trifecta

P124 keeps the original room model, queue-admission owner, semantic glossary and screen-lock contract intact; survey and memory are narrow peers rather than new global managers. P82 regression tests cover player activity during polling, full queues, stale lot versions, missing mode/camera evidence, cross-session deduplication, outcome review, and simulated idle traversal. P07 integration/CI lands on main only when green. P08 must test a disposable save and observe game-native queue, hover and camera outcomes before live certification. Existing BI-002 hunger certification remains separate.
