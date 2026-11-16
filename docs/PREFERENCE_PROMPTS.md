# Skill-triggered likes and dislikes — human-first decision microsystem

**Owner:** `betterinstincts/preference_prompts.py` / `contracts/preference-prompts.v1.json`. **Host caller:** `betterinstincts/host_stack.py` (from `host_listener.py`). **Observed single-step input:** `scripts/preference_prompts.py`. **Screen ownership:** `betterinstincts/screen_admit.py`, never this catalog.


## Chased by Death

For the Live Mode add-trait offer titled **Chased by Death**, choose **No thanks!**.
This rule requires the exact offered trait and both visible response labels.
It never advances to a confirmation step. The preference CLI can assess the
offer and plan the decline. Its screen executor refuses this trait on every
stage, including when a caller supplies a rectangle labeled as No.

The existing native response port accepts an explicit local
`trait_binding` sourced from the installed game's tuning. It uses
`betterinstincts.chased-by-death-native-binding/v1` with `topic_id`
`chased_by_death`, exact `game_build`, `dialog_tuning_id`,
`localization_key`, `trait_id`, `installed_tuning_ref`, and a
`response_ids` mapping with distinct `YES` and `NO` IDs. The adapter
reads the current raw EA offer, including its Actor recipient, both
response labels and the offered trait ID. `submit_if_current` must
atomically match the requested ID, negative label and role, current
dialog, recipient, state revision, save, pause and input generation.
No position, index, keyboard default or other offer's mapping is evidence
for the negative response.

The port sends at most one unresolved response for that dialog. A separate
native ACK and a later capture showing the same dialog closed and trait absent
on the recipient establish the decline outcome. This path never requests
unpause or continuation of the conversation. The exact installed EA callback,
trait binding and live decline still require a local test under
[native integration #171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).


## Video Gaming native response on build 1.121.361.1020

Use the existing recipient snapshot and the same continuation actions to score both choices in `betterinstincts/preference_recipient.py`. The actual offer recipient can differ from the selected Sim. Missing or indeterminate native evidence holds Video Gaming. Other catalogued topics retain their existing policy.

`scripts/preference_response_port.py::PreferenceResponsePort` binds the exact EA offer and offers one response through a separately verified adapter. The adapter contract and exact IDs live in `contracts/preference-native-response-map.v1.json`. The adapter owns a game-thread recheck of the dialog, recipient, revision, save, pause and player intent. If submit was attempted and its return is lost, a matching native acknowledgement with the reserved attempt reference can reconcile the result using independent actor/household effect and originating activity evidence. An uncertain submit is never replayed.

PRs #261, #262, #263, #275 and #278 supplied the source and review history. The repeat-offer Yes is recorded as agent-assisted visual resolution. Keep it closed. Issue #171 tracks the remaining Windows gate. Inspect the installed exact-build EA response path and verify the mod's game-side adapter registration. Then use the next naturally occurring eligible offer to observe one product-owned choice and submit, matching native acknowledgement and effects. The separate LabLab successor review can proceed without waiting for that new offer.

## Correct an existing preference through Simology

In Live Mode, select the Sim and press **Y** or click the **Simology**
head icon in the bottom-right tray. In the panel, find **Preferences** /
**Likes and Dislikes** and use that section's **Enter Create a Sim**.
The Relationship Preferences section can have a button with the same
label. In the existing household's Create-a-Sim (CAS) screen, select the
target Sim and open **Select Preferences** via the faces beneath the
Aspiration/Traits area. If CAS opens on that panel already, continue from
the visible state.

| Branch | Control | Categories relevant to this workflow |
| --- | --- | --- |
| **Likes and Dislikes** | Smiling and frowning faces | **Activity** opens **Hobbies & Skills**, including Robotics, Programming, and Video Gaming. **Fashion** has its own like/dislike controls. |
| **Turn-Ons and Turn-Offs** | Magnet | **Way of Life** is the first tile. Attraction **Fashion** is the right tile on the second row of the observed layout. These are sibling categories. Lovestruck availability must be observed. |

After selecting the exact category and row, clear the old selection if
needed. Reobserve neutral before selecting the replacement. Confirm with
the bottom-right checkmark only after verifying the target preference and
the absence of other staged edits. Reobserve the same Sim's preference in
Live Mode after confirmation. The route identifies the current semantic
target from the latest capture. Reference coordinates are in
`contracts/preference-corrections.v1.json`; the live host must verify a
fresh control or hitbox before using either channel. If the row is
off-screen, scroll its category list and recapture the row.

### How BetterInstincts evaluates a correction

`host_listener.tick` reads an optional `preference_correction` packet
with `preference_correction_opt_in: true` and
`preference_game_build_confirmed: true`. The packet carries
`request_ref`, session/PID/build/save/Sim identities, `pref_revision`,
`family`, `category`, `topic_id`, the current and desired values, and
a current game observation. The listener checks the active session,
foreground PID, captured game build, capture ID and real clock. In Live
Mode, report the observed `simology_panel_open` boolean: a closed panel can
be opened with Y or the tray icon, an open panel routes to its scoped
CAS button, and unknown visibility holds. A staged edit or its final readback also needs a separate preceding input receipt
bound to the same request and control. If the previous dispatch is
unresolved, refresh the game state before retrying.

- **Mistake.** Supply an explicit operator correction or an attributable
  automation mistake receipt with the previous and intended values.
- **Repeated behavior.** Supply at least three independent matched
  comparisons for the same Sim and catalogued activity. Every pair needs
  distinct outcome receipts, stable availability, and evidence that the
  stored preference caused the difference. The starting weights are 40%
  needs, 25% net income, 20% skill, and 15% career on normalized outcomes.
  A decline in needs vetoes the change. The mean weighted gain is reduced
  by one standard error and shrunk toward zero for small samples. The
  resulting score must reach 0.15. These starting thresholds need live
  calibration. Player-owned choices and attraction preferences have no
  automated productivity correction. A missing or invalid activity catalog
  holds this lane while explicit mistake corrections can still be planned.

This clone-ready path emits one semantic plan or a reason to hold. The
Windows game observation producer, actual preference write, and
disposable-household gameplay certification are tracked with the native
integration work in [#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).
The existing earned preference offer path remains separate.

Focused check: `python -m unittest tests.test_preference_corrections -v`.

## What the user gets

When a Sim earns skill levels or a preference prompt appears, an agent can evaluate the proposed **like** or **dislike** without automatically clicking the first answer. The versioned catalog starts with practical preferences (Cooking, Gardening, Handiness, Programming, Robotics, Fabrication, Fitness, Painting, Writing, Charisma), while Mischief/Music require a matching Sim goal. A positive like is ordinarily useful; a dislike of a useful skill is ordinarily rejected. A dislike can be beneficial when it supports that Sim's declared goals (e.g., avoid Mischief). The catalog is a *heuristic*, not hardwired Sim personality truth. Player direction always wins.

**Distinct dialog domains remain distinct:** aspiration completion and occult/life-state transformations stay in `aspiration_service`; skill-reward traits must be classified as reward traits, not inferred from a level-up toast; likes/dislikes own only `sim_preference_offer`. Unknown or uncatalogued dialogs **HOLD** and need review. Game build, installed packs and actual phrase/button positions are **not certified by this repository's offline tests**.

## Machine-readable call stack

```text
Fresh game capture (exact PID, Sim, build, scene, candidate dialog, two cues)
  -> existing host_listener.tick / host_stack.evaluate_turn
  -> preference_prompts.evaluate_offer
      HOLD             -> no action
      DECLINE          -> propose single NO
      ACCEPT           -> propose YES, then independently observed OK
  -> explicit opt-in + ACTIVE listener session + trusted desktop-wide 30/60/120s idle
  -> one shared desktop input lock / repeated session and user-owner checks
  -> revalidate fresh capture (<5s), selected Sim, cleared player queue,
     authorized save, same Sims foreground PID and visible client button rectangle
  -> exactly ONE button click via scripts.preference_prompts
  -> receipt says INPUT_DISPATCHED (not accepted/verified)
  -> if YES: recapture the resulting confirmation; same Sim, topic, kind,
     session and process, distinct/newer capture -> separate OK operation
  -> observe actual in-game outcome before recording learned success
```

The listener receives optional structured observation values `preference_offer`, `preference_automation_opt_in`, `preference_game_build_confirmed`. The evaluation result lives at `host_stack.preference_prompt`; it is intentionally **not** a SendInput permit. Observations need `dialog_class: sim_preference_offer`, `dialog_stage: offer`, `scene: live`, `sim_ref`, `capture_ref`, `topic_id`, `offer_kind` (like/dislike), and exactly `visible_buttons: ["YES", "NO"]`; `goal_tags` are optional. Live --execute additionally needs `observed_process_id`, `captured_at_epoch_ms`, `sim_selected`, `selected_sim_ref` matching the offer capture’s `sim_ref`, `player_queue_clear`, `save_authorized`, `game_build_confirmed`, and exact pixel `target_boxes` from the current client viewport (e.g. `YES: [x1,y1,x2,y2]`); don't invent boxes. The Video Gaming screen fallback also requires a verified recipient identity and `selected_sim_id` matching `recipient_sim_id`. Independently confirm game scene, window identity and visual target in the producing adapter; this component does not perform image recognition.

```powershell
# Planning only — no game control
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --opt-in
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --opt-in --stage YES

# A deliberate single click; ACTIVE session/PID and a new receipt required
python -m scripts.preference_prompts --observation dist/game-host/preference-offer.json --stage YES --opt-in --execute --session-id SESSION --process-id PID --idle-ms 30000 --receipt dist/game-host/preference-yes-receipt.json

# Reobserve confirmation with a NEW capture, then one OK; do not replay old capture
python -m scripts.preference_prompts --observation dist/game-host/preference-confirmation.json --stage OK --opt-in --execute --session-id SESSION --process-id PID --idle-ms 30000 --previous-receipt dist/game-host/preference-yes-receipt.json --receipt dist/game-host/preference-ok-receipt.json
```

`--execute` does **not** steal focus from another application. It fails if Sims isn't already foreground; when a person works elsewhere, compatible agents retain pending intentions through `workflow_interop.CooperativeScreenQueue` and retry only after fresh permission. It won't attempt to simulate the game, auto-close every overlay, scan other apps, or alter Sims saves.

## Skill-force regression guard

Prior `scripts/diy_skill_force.py` used stable cursor time as a surrogate for OS idle and dispatched repeated Enter plus guessed reward-OK coordinates after skill upgrades. This could override dictation or accept an unwanted dislike. That logic is intentionally disabled: cursor stability remains diagnostic only; `GetLastInputInfo` must prove trustworthy idle, and reward prompts now report `NEEDS_DIALOG_IDENTIFICATION` instead of being clicked blindly. The catalogued preference path offers a safe next step; *actual reward traits* require their own independently verified prompt adapter. Until then they stay pending, not implicitly accepted.

Offline test commands:

```bash
python -m unittest tests.test_preference_prompts tests.test_preference_host_adapter tests.test_control_handoff tests.test_diy_skill_force -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-HUMAN-PRESENCE-PREFERENCES-20261109.v1.json --operation repo_mutation --file betterinstincts/preference_prompts.py
```

## Proof and gaps

P95: explicit dialog judgment call stack; P124: reuse aspiration/host/listener/screen owners instead of parallel controller; Trifecta: P08 live on the actual Windows Sims PID remains open, P82 synthetic negative/positive cases in offline tests, P07 CI and mainline integration. No local player activity, process names, UI targets, spoken words, or hotkey text are persisted by this feature. A running dictation process **alone** does not indicate a person is speaking: a local operator/agent can explicitly mark `--operator-busy` on the handoff CLI, and independent OS input age catches typing/mouse activity even outside Sims. The dormant-state detector is not a voice-recognition service.
