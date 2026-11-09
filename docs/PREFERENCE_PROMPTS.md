# Skill-triggered likes and dislikes — human-first decision microsystem

**Owner:** `betterinstincts/preference_prompts.py` / `contracts/preference-prompts.v1.json`. **Host caller:** `betterinstincts/host_stack.py` (from `host_listener.py`). **Observed single-step input:** `scripts/preference_prompts.py`. **Screen ownership:** `betterinstincts/screen_admit.py`, never this catalog.

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

The listener receives optional structured observation values `preference_offer`, `preference_automation_opt_in`, `preference_game_build_confirmed`. The evaluation result lives at `host_stack.preference_prompt`; it is intentionally **not** a SendInput permit. Observations need `dialog_class: sim_preference_offer`, `dialog_stage: offer`, `scene: live`, `sim_ref`, `capture_ref`, `topic_id`, `offer_kind` (like/dislike), and exactly `visible_buttons: ["YES", "NO"]`; `goal_tags` are optional. Live --execute additionally needs `observed_process_id`, `captured_at_epoch_ms`, `sim_selected`, `player_queue_clear`, `save_authorized`, `game_build_confirmed`, and exact pixel `target_boxes` from the current client viewport (e.g. `YES: [x1,y1,x2,y2]`); don't invent boxes. Independently confirm game scene, window identity and visual target in the producing adapter; this component does not perform image recognition.

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
