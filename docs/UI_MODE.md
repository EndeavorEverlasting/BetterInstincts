# Game mode and panel context — offline candidate

**Scope:** P95 call stack / P124 ownership factoring / Trifecta P82→P07. P08 game screenshot calibration remains open. Consultation: `contracts/consultations/BI-UI-MODE-CONTEXT-20261109.v1.json`.

## One owner; three modes

`contracts/game-scenes.v1.json` remains the canonical **scene** owner. `betterinstincts/ui_mode.py` is a read-only projection of `scenes.classify`, not a duplicate screen recognizer. For the exactly declared Sims patch, two distinct inputs — one `visual`, one `operator` — identify candidate `live_mode` (F1), `buy_mode` (F2) or `build_mode` (F3). Both cue labels are **unverified research tokens** until the local Windows game adapter is calibrated. The prior `build_buy` scene remains supported as a genuinely ambiguous combined legacy scene, not forced to Buy or Build.

The shortcut key is merely an intent hint: focus theft, blocked transitions, dialogs, loading, and other overlays may prevent a switch. Conflicting or missing cues, an unknown patch or an unrelated modal result in mode `UNKNOWN`. No last-known-mode fallback is allowed. The optional panel context (needs, action queue, item catalog, household inventory, wall tools, floor selector, etc.) likewise requires distinct `visual` and `operator` cues. `available_panels` lists expected menus, **not** menus actually observed. Only `active_panel` is attested by supplied cues.

## Asynchronous call stack

`capture/operator adapter → host_listener.tick → ui_mode.evaluate_mode → scenes.classify → mode/context receipt → [LIVE: existing host_stack] or [BUY/BUILD: existing build_floor_activity only] or [UNKNOWN: no Live plan]`.

`host_tandem` consumes the **same tick**. For explicit Buy/Build/Unknown context it ends its bounded loop before a new Live action dispatch, preserving pending goal continuity and never cancelling the player's queue. In Live, the existing needs/career/gardening/aspiration/balance owners remain unchanged. `build_floor_activity` continues to classify floor/story/theme when Buy or Build is attested. No new daemon, input adapter, filesystem scan or per-frame polling is added.

Legacy observations without mode cue fields remain compatible and unchanged; their mode is **not independently verified**. When explicit mode cues are supplied, `build_or_buy_mode` becomes a derived compatibility flag; a contradictory supplied legacy flag fails closed.

Example evaluate-only input (not a screenshot):

```json
{
  "schema": "betterinstincts.host-listener.observation/v1",
  "game_version": "1.121.361.1020",
  "mode_observations": [
    {"source": "visual", "token": "mode:build_structural_tools"},
    {"source": "operator", "token": "build_tools_visible"}
  ],
  "panel_observations": [
    {"source": "visual", "token": "panel:build_walls"},
    {"source": "operator", "token": "wall_tools_visible"}
  ],
  "shortcut_hint": "F3"
}
```

The remaining legacy observation fields (all six needs, queue, location and capture reference) are still required. P08 on the local game machine must gather genuine, fresh exact-build screen evidence for each mode, menu variant, overlay and focus transition before any claim of real game detection or input authority. No change to BI-002's hunger live certification status.

## Related: chrome maps and hotkeys

Mode classification does not know where to click. Named Build/Buy targets, the
per-mode hotkey glossary, Live panel stubs, and the **AOK** → Household Inventory
recipe live in [UI Chrome](UI_CHROME.md) (`contracts/ui-chrome.v1.json`).
