# Sims 4 UI microsystems — semantic, scene-specific click targets

**Scope:** offline semantic prototype, not a playable Sims 4 mod and not proof of a physical click. Source: `contracts/ui-microsystems.v1.json`; implementation: `betterinstincts/ui_microsystems.py`; action owner: existing `betterinstincts/screen_atlas.py` and `CooperativeScreenQueue`. Consultation: `BI-SEMANTIC-CLICK-MICROSYSTEMS-20261109`.

## Why this is not a second Playwright engine

Sims 4's native game client has no browser DOM or Playwright selectors. Browser Playwright remains an **injected, existing-page adapter** in `playwright_interop.py`. Native game clicks use the already-owned, opt-in screen-host port. The new layer gives both a Playwright-like **semantic vocabulary** and explicit validation gates; it does not launch a browser, monitor the desktop, install a hook, discover saves, or bypass the player.

## One source per responsibility

- `game-scenes` and `ui-mode` own scene and mode identity, including independent visual/operator cues.
- `ui-chrome` owns confirmed hotkeys and Build/Buy chrome targets. Prefer a native hotkey when semantically equivalent; an unverified hotkey cannot prove a panel opened.
- `ui-microsystems` owns **which semantic action belongs to which panel** and its exact two panel-presence cue tokens. It **does not store invented pixels**.
- `screen_atlas` owns exact-patch target calibration, normalized/native client conversion, and the final scene/target revalidation. A panel-specific click additionally requires an operator-attested hitbox and a matching fresh observation.
- `workflow_interop` owns the 15-second player inactivity arbiter, desktop mutex, one-effect-per-job queue and no-blind-replay rule; `camera_traverse` owns safe interior rest.

## Panel namespaces

| Microsystem | Mode | Semantic action examples | Admission |
| --- | --- | --- | --- |
| `aspirations` | LIVE | inspect_current_aspiration, inspect_milestone, select_aspiration | Await exact-build hitbox |
| `career` | LIVE | inspect_schedule, inspect_performance, inspect_daily_tasks | Await exact-build hitbox |
| `skills` | LIVE | inspect_skill, inspect_progress | Await exact-build hitbox |
| `simology` | LIVE | inspect_traits, inspect_preferences | Await exact-build hitbox |
| `personal_inventory` | LIVE | inspect_item, select_item, filter_items | Await exact-build hitbox |
| `needs` | LIVE | inspect_motive, inspect_motive_state | Await exact-build hitbox |
| `household_inventory` | BUY / BUILD | open_inventory, inspect_item, select_item | Existing Build/Buy chrome owns tab identity; each panel action still needs independent calibration |
| `small_business` | LIVE, pack-gated | inspect_business, inspect_staff, inspect_tasks | Entitlement + hitbox required |
| `skills_and_needs` | LIVE | Composite inspection context only | No direct click target |
| `skit` | Unresolved | None | Literal label retained; no guessed menu mapping |

Action names express *intent slots*, not an assertion that a particular Sims button or DLC feature exists in every patch. Add new action names only when supported by canonical context; mark as uncalibrated until observed.

## P95 representative call stacks

**Native game success candidate:** agent requests `career.inspect_schedule` → `resolve_action("career", "career.inspect_schedule", mode="LIVE")` → `resolved_calibration` checks patch/profile, operator-verified status, scene, exact panel action, 8px+ hitbox and computed center → `enqueue_native_game_click` → canonical 15s idle + desktop owner → fresh game-process/scene/target and **panel-specific** cues, visible/enabled/unobscured/stable state, selected-Sim and layout revisions, exact hitbox → effect checkpoint → injected native click once → checkpoint → safe interior mouse rest → queue receipt. The click still needs separate **post-action outcome verification** by the host; queued/completed means input was attempted, not a game task succeeded.

**Failures:** unknown patch, ambiguous `skit`, cross-panel target, wrong mode, mismatched profile, no operator attestation, center outside hitbox, absent visual/operator panel cue, stale selected-Sim/layout revision, obscured/animating/disabled button, wrong focused process, player input or desktop lock: no click. After an ambiguous effect, queue quarantine blocks blind retry; operator/host must reconcile observable state. Never infer success from pixel proximity alone. For near-misses, the existing `click_error_eval` Escape-cancel **proposal** remains an independently admitted recovery, not automatic second action.

**Browser control:** existing `enqueue_playwright_step` retains URL/locator checks and waits for the same screen lease. If a future source actually renders the game within an existing Playwright page, `enqueue_game_click` accepts the same panel calibration under its own fresh observation gate. Browser CSS locators must not be advertised as native Sims selectors.

## Adding a new panel or target without regression

1. Confirm exact UI domain, game patch, mode and optional pack entitlement. Resolve or explicitly preserve ambiguous labels; never rename `skit` to `simology` by assumption.
2. Add one panel/action under the `ui-microsystems` owner, with unique semantic target ID and **independent visual/operator cue tokens**, no pixel guess.
3. Capture an exact-version, exact-client-resolution screenshot with genuine operator verification. Attest rectangle `[left,top,right,bottom]`, center `x/y`, `evidence_ref`, `ui_layout_revision`, `selected_sim_revision`, and optional pack entitlement. These are injected at runtime, not baked into a universal file.
4. Supply an independent **fresh** host observation containing the same `panel_id`, hitbox, revisions, two panel cues, active scene, viewport quality, focused PID, enabled and visible target, stable animation and no occlusion. Geometry/layout/Sim drift invalidates the intent.
5. Use the existing queue only. Verify click effect, intended UI change, mouse rest and no player interference. Add negative tests (wrong panel/patch/UI scaling/occlusion/Sim switch/ambiguous label), then ask P08 local game host for real calibration and validation.
6. Record outcome in `docs/LEDGER.md`. P82 tests synthetic cases; P07 merges after CI; P08 is required for physical gameplay closure. BI-002 hunger remains ACTIVE.

## P124 factoring decision

**KEEP** `playwright_interop`, `ui_chrome`, `screen_atlas`, `workflow_interop`, `camera_traverse` as independent proven owners. **EXTRACT** panel taxonomy plus hitbox/panel observation guards into one cohesive `ui_microsystems` module, rather than turning `screen_atlas` into another giant multipurpose glossary or creating a parallel Win32/Playwright daemon. **DEFER** computer-vision detection and exact DPI/pack screen mappings until the local game host supplies trustworthy receipts. This preserves the existing browser click/fill path and uncalibrated Build/Buy target semantics.
