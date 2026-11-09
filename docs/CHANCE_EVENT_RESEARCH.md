# Chance-event intelligence: research, memoization, and player-first companion

**Status:** offline, supplied-observation prototype. This is **not** an installed Sims mod, live popup detector, background researcher, or rendered in-game overlay. The host must separately certify all Windows/game-facing adapters before claiming live behavior.

## Parent outcome

When a previously unseen chance card or other decision-forcing modal appears, BetterInstincts should understand the exact event, inspect game mechanics and current independent references, explain the potential benefit, downside and permanence of **every** option, and let the player decide. It should avoid repeating already-reviewed computation for the *same* patch, packs, mods and wording. This is **memoization**, not memorization or model training by itself.

A companion *beside* the native dialog should communicate genuine progress rather than appearing stuck. The native buttons and game focus remain the player's. No background agent may decide irrevocable life-state, relationship, career, save or world changes from unverified sources. Preserve unknowns and personality choice; "best" is context- and player-preference-dependent.

## Owned call stack (P95; reuse/factoring P124)

```text
local host calibrated screenshot + exact game context
  → two independent popup/choice cues (existing scene/atlas evidence owners)
  → supplied chance-event.observation/v1
  → chance_event_research.identify (stable exact-context SHA256 key)
  → chance_event_research.assess (read reviewed memo)
       ├─ fresh reviewed full mapping → READY_FOR_PLAYER UI projection
       └─ unknown/stale/contradictory → bounded research_dispatch
             ├─ LOCAL_MECHANICS: inspect installed patch, packs, mod tuning,
             │                   run safe repeatable disposable-game experiment
             └─ FRONTIER_CROSSCHECK: opt-in, privacy-sanitized, date/version
                                 checked independent references
  → human-reviewed option implications → chance_event_research.remember
  → optional atomic local memo storage → next popup cache hit
  → companion presentation model → independent future host renderer
  → native player action (not an advisory auto-click)
```

**Existing owners remain intact:** `betterinstincts/decision_eval.py` and `contracts/decision-prompts.v1.json` hold known catalogued chance-card heuristics; `host_stack` owns domain composition; `host_listener` and `screen_atlas` own supplied observations and host activity; `control_handoff` protects human activity; none is replaced. This prototype adds the read-only new-event research seam. Existing catalog matches should be reused as evidence candidates, **not** silently promoted to trusted exact-outcome facts.

## Data contract and memo identity

Use `schema: betterinstincts.chance-event/v1`, `capture_ref`, `modal_visible: true`, at least two independent cues among `dialog_bounds`, `choice_controls`, and `modal_layer`, `title`, `body`, two to eight distinct `options` with `id` and `label`, plus `context`: the **exact** `game_version`, `locale`, sorted `packs`, and a `mods_digest` (explicit `NONE` is different from unknown). Event identity is content+options+context SHA-256, not title alone. A different patch, pack set, mod signature, locale, choice text, or option set misses the memo and dispatches investigation again.

Sample synthetic observation (not a real-game capture):

```json
{
  "schema": "betterinstincts.chance-event/v1",
  "capture_ref": "capture:sample",
  "modal_visible": true,
  "scene_cues": ["dialog_bounds", "choice_controls"],
  "title": "A Strange Offer",
  "body": "An odd offer appears.",
  "options": [{"id": "take", "label": "Accept"}, {"id": "decline", "label": "Decline"}],
  "context": {"game_version": "EXACT.OBSERVED.GAME.PATCH", "locale": "en-US", "packs": [], "mods_digest": "NONE"}
}
```

Place sanitized JSON input in an explicitly controlled local file. From repo root:

```powershell
python -m scripts.chance_event_research assess --observation dist/game-host/event-observation.json
python -m scripts.chance_event_research assess --observation dist/game-host/event-observation.json --external-research-opt-in --host-research-state RUNNING
python -m scripts.chance_event_research remember --observation dist/game-host/event-observation.json --reviewed-research dist/game-host/reviewed-research.json
```

`--host-research-state RUNNING` is for a genuinely running host worker **only**; it does not launch research. The research dispatcher returns source-agnostic jobs that a local agent/host can accept. Without explicit network opt-in, only the local mechanics job is offered. Returned jobs include event keys and capture references, **not** unredacted Sims narrative/player data for external queries. Never transmit screen images, save metadata, household names, or private player identifiers without an additional explicit permitted local sanitization gate.

Reviewed research JSON must contain `reviewed: true`, `sources: [{kind,ref,observed_at}]` with `LOCAL_TUNING`, `LOCAL_OBSERVED` or `EXTERNAL_REFERENCE`; `recommended_option_id` if defensible; and `implications` for **every** `option_id`, each with `benefits`, `risks`, `unknowns`, `permanence` (`REVERSIBLE`, `PERSISTENT`, `IRREVERSIBLE`, `UNKNOWN`), and `confidence`. Review is attestation provided by the caller, **not a game certification claimed by this function**.

Memo data is versioned, bounded to 128 entries/512 KiB, atomic-write, local-only `dist/chance-event-research/memo.json` via explicit CLI command. Defaults: 30-day expiry (maximum 90); exact-context invalidation is independent of TTL. A source conflict, unknown permanence or uncorroborated persistent choice returns `REVIEW_REQUIRED` with **no recommended option**. A cache hit never authorizes automatic in-game input. Verified option consequences are claims with dated source provenance, not assumed universal across future Sims patches.

## Companion UI state and design acceptance

The result's `ui` is a **presentation model**, not a Windows surface. A future opt-in host adapter renders it alongside the game dialog while the native choice buttons retain focus and remain accessible:

| State | Player-visible status | Behavior |
|---|---|---|
| `OBSERVATION_REQUIRED` | Confirming which event appeared | Never research or click from a single ambiguous cue |
| `RESEARCH_REQUIRED` | Checking the installed game mechanics | Show local vs external lanes; external says opt-in required when off |
| `RESEARCHING` | Research in progress; no choice made | Only when worker is actually running; no invented percentage |
| `RESEARCH_FAILED` | Research couldn't finish; native decision remains available | Preserve player control, no infinite blocking spinner |
| `REVIEW_REQUIRED` | Consequences remain uncertain | Show known benefits/risks/unknowns, no recommendation |
| `READY_FOR_PLAYER` | Evidence reviewed; you decide | Clear per-choice implications, risk permanence, confidence and sources |

**Visual and accessibility safeguards:** compact adjacent layout, readable hierarchy and option alignment; no second modal, no automatic focus theft, no duplicate action buttons, no forced countdown; visible loading/failure/retry explanations; reduced-motion static fallback; keyboard and screen-reader labels; text-only high-contrast fallback; performance budgets and DPI/viewport calibration; no occlusion of game dialog. The design is intentionally *quietly immersive*, not cinematic distraction.

The upstream design source registry informed these requirements, especially state-aware component critique, clear information hierarchy, visual regression testing, and WCAG reduced-motion safeguards. These are design methods, not copied upstream code or authority to redesign a player-facing UI.

## Distinct proof gates (Trifecta P82 → P07 → P08)

- **P82 / offline falsifiers:** run `python -m unittest tests.test_chance_event_research -v`, then full `python -m unittest discover -s tests -v`, semantic preflight and CI. Verify cache hit, stale/patch/mod invalidation, disputed/irreversible abstention, review control, no fake progress, and no execution capability.
- **P07 / repository integration:** tested new module/CLI and schema-bearing consultation/ledger, linked to established host contracts; merge only after PR validators and review. A green offline test does not imply an installed UI.
- **P08 / local game certification (separate, still open):** identify actual installed Sims patch/DLC/mods; pass two-cue popup detection on real chance cards, verify stable game-pause/host idle cooperation, validate mechanic findings with repeatable/disposable experiments, render the companion on borderless fullscreen without stealing focus or covering native choices, verify correct player option after intervention and recovery, measure loading/error/accessibility/reduced-motion, confirm no irreversible choices are auto-dispatched, record original screenshot/receipt in ignored local evidence and a safe redacted certification receipt. No user saves may be modified or overwritten by the evaluator.

**Rollback:** revert this feature PR and remove only the explicit local memo file if desired. Existing chance-card heuristics, saves, human input and host adapters are unchanged.
