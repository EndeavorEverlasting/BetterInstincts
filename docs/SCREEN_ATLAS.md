# Screen atlas: observe → verify → one input → safe interior rest

**Owners:** `betterinstincts/screen_atlas.py` composes `contracts/ui-chrome.v1.json`, `contracts/game-scenes.v1.json`, `contracts/camera-traverse.v1.json`, `contracts/hidden-object-discovery.v1.json` and `betterinstincts/workflow_interop.py`. The schema is `contracts/screen-atlas.v1.json`. No new screenshot daemon, console executor, native input owner or parallel cursor controller.

## Inspect the screen, targets, shortcuts and curated console functions

```sh
python -m scripts.screen_atlas inventory
python -m scripts.screen_atlas target --mode BUILD --id catalog.search_field
python -m unittest tests.test_screen_atlas tests.test_ui_chrome tests.test_camera_traverse tests.test_playwright_interop -v
```

The inventory is **machine-readable and dynamically composed** from the existing authoritative definitions. Its `screen_maps` joins every scene ID to its independent cues, any known UI-chrome targets, and historical host-menu click candidates. An `unmapped=true` screen is an explicit coverage gap, not a reason to guess coordinates. It lists scene IDs, Live/Buy/Build region maps, panels and hotkeys, plus the cheat console chord and curated commands already defined by hidden-object discovery. It is deliberately **not** a claim to enumerate every possible Sims console command. Add a console function to its owning contract only after corroborating exact patch, effect, prerequisites and consent needs; never infer unknown commands or execute from inventory.

A `catalog.search_field` coordinate in the current map is **CANDIDATE_UNVERIFIED**. Normalized points and shortcut names do not create permission to click. Live/phone panels remain uncalibrated. For a new screen, add named targets to the existing `ui-chrome` owner and scene signatures to the existing `game-scenes` owner, with two independently sourced cues. For a changed patch, create a new scoped calibration after local operator review; never silently reuse 1920×1080 coordinates on another resolution, UI scale, mod profile or game version.

## Native game vs Playwright page

Playwright automates browser DOM/pages; The Sims 4 is normally a **native game**, not a Playwright DOM. `enqueue_game_click` is an opt-in, injected **existing-page** adapter for a Playwright-hosted game surface that genuinely exposes `page.mouse`. It does **not** launch a browser or make native Sims clickable through Playwright. Native game input stays in `scripts/win32_input.py` behind `screen_admit` and the real game host's exact-PID/scene/save checks. The **injected** `enqueue_native_game_click` seam accepts only a locally admitted port with matching process/session, foreground PID, window-client origin and fresh scene/target observations; it converts client pixels to absolute screen coordinates and parks after one input. It never calls Win32 by itself. Both adapters share the same atlas semantics and safe-rest calculation. Do not run simultaneous Playwright and Win32 controllers.

A reviewed target calibration must supply exact `game_version`, `profile`, client width/height, `mode`, named `target_id`, **actual measured client pixels**, `status=OPERATOR_VERIFIED_EXACT_BUILD`, and a bounded nonsecret evidence ID. `resolved_calibration` checks its shape and references but does not establish the truth of the assertion. The host's fresh, independent observation callback must confirm the target is visible, current scene/mode, exact geometry, good viewport, authorized lab save, no player queue ownership, and two distinct visual/operator cues; that callback is the trust boundary. Missing any one field fails closed.

A host-integrated Playwright example (pseudocode for externally supplied sensors):

```python
queue = CooperativeScreenQueue(probe=trusted_os_idle_probe, session_active=active_session)
enqueue_game_click(
    queue, work_id="reviewed.build.search",
    page=existing_playwright_game_page,
    calibration=reviewed_exact_build_target,
    observe=fresh_game_scene_target_and_save_probe,
)
result = await queue.run_once()
```

Each step checks the 15-second player-idle gate and cross-agent lock **before** the click; the injected observation is checked again immediately before input. After the click, it rechecks player idleness **before** calling `page.mouse.move` to park the pointer at the safe client interior (currently center). An interruption between click and park **never fights the human**; the queue records `NEEDS_RECONCILIATION` and refuses blind click replay. The game may still need a local screen-rest step after operator control ends. Do not attempt to park a pointer in an unowned app or while the player is active.

## Acceptance and remaining live proof

The offline tests require incorrect patch, wrong mode, profile drift, unverified calibration, invisible/stale target, ambiguous visual/operator cues, player-owned queue and black/unknown viewport to reject input. They test clean completion plus safe rest and human interruption after a click. `execute_allowed=false` in the read-only lookup prevents the planner from claiming control authority. These simulated tests **cannot prove** that a real Sims camera stopped drifting or that live per-pixel target recognition is reliable.

**P08/local agent next gate:** capture exact Sims patch, UI scale, window bounds and target pixels; independently observe scene and save/protected-player status; verify edge pan stops after safe parking; test 5+ repeated placements on an explicitly authorized disposable save without camera drift or missed targets; attach game captures and rollback. BI-002 remains active. Do not auto-apply candidate calibrations or run the console on personal saves.

For a native-game cursor that was already left at an edge **without** a click, the existing admitted one-shot recovery is `python -m scripts.camera_traverse rest --execute --session-id SID --process-id PID`. Use only after verifying the live client geometry and the player's inactivity. Do not rely on background movement or polling to park the cursor while the player is working.
