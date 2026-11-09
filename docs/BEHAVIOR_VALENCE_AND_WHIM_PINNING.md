# Reviewed action/whim valence and native whim pinning (P95 / P124 / Trifecta)

## Why these are peers, not a replacement intelligence engine

Keep one opt-in host listener and the canonical per-domain evaluators. `autonomy_moderation` owns current harmful-queue action decisions, `judgment_learning` owns reviewed Markov behavior selection, `hover_learning` owns supplied temporal tooltip outcomes, `behavior_valence` owns per-channel positive/negative classification plus **contextual Beta-Binomial supervised online review counts**, `ui_microsystems` owns the exact LIVE whims semantic target and `screen_atlas` owns the single admitted native mouse click. The new module does not introduce a daemon, raw history logger, learned global override, direct Win32 calls, or new game options.

## The two streams and model evidence

The queue and whims are **not the same thing**. Queue entries may have independently proven BENEFICIAL, RELATIONSHIP_HARM, ENVIRONMENT_HARM or NEUTRAL effects; wishes have individually supplied BENEFICIAL, HARMFUL, NEUTRAL or UNKNOWN benefit assessments. Each event returns a separate observed bucket (positive/negative/neutral/unknown), even if the learned label differs. Unknown is not negative. Neither negative whim nor a predicted-negative action is evidence that a cancel target is currently safe to click.

A reviewed semantic example contains only patch, platform, channel (QUEUE/WHIM), bounded action ID, activity context, positive/negative outcome, review/evidence refs, and explicit review + opt-in flags. It cannot store Sim names, raw dialog, screenshots or the player's keystrokes. `learn_reviewed` updates aggregate positive/negative counts with replay IDs bounded across calls; a Beta(1,1) posterior mean and minimum 3 samples yields advisory POSITIVE/NEGATIVE or UNKNOWN. Unreviewed queue events cannot train. The model is patch/platform-specific; a new installed game patch abstains unless the operator explicitly retrains/chooses the correct profile.

`observe_behavior_review` on an explicitly active listener session writes one bounded aggregate model in `dist/host-listener/<session-id>/behavior-valence.json`, via the existing opt-in session's sidecar writer. The model survives ticks; a new session can import an operator-provided prior model through the same explicit review call. Every model read is validation-bounded. Use review receipts, not automatic raw observation aggregation.

## P95 call stack

```text
opt-in host_listener tick + confirmed player-idle
  -> current autonomy_observation with verified selected actor & queue
  -> autonomy_moderation: player/needs/obligation protections + cancel/repair proposals
  -> behavior_valence: classify each queue event/whim & attach learned advisory
  -> host_stack receipt containing distinct observed/model buckets
  -> Discovery Quest panel: Scoring Simoleons, Navigating Needs, You and Your Phone
     (only attested current active quest routes through its existing owner)
  -> optional one observed beneficial, unpinned, available whim candidate
  -> whim_pinning.plan_whim_pin checks whim/capture/Sim and exact panel ID
  -> injected enqueue_native_game_click + existing 15s idle / desktop lock
     exact patch + operator-attested per-whim hitbox + two visual/operator cues
     current Sim revision + panel stable/visible/unobscured + PID focus
  -> CHECKPOINT / one click / safe mouse rest
  -> separate post-click observation MUST prove pinned state, else QUARANTINE
```

No keyboard shortcut for whim pinning is invented. Enqueuing a click is not pin success. The model cannot self-authorize pinning or cancellation. The player can pin whatever they want; BetterInstincts cannot unpin or replace it by prediction.

## Top-left three-module registry

The existing `discovery_hud` knows three core modules: **Scoring Simoleons**, **Navigating Needs**, and **You and Your Phone**. The host receives an inventory status for each from an explicitly supplied `observed_modules` list, independently of whichever one is actively visible. Only a verified active quest may affect that turn's goal planner; others are classification only. This does not assert that all three are simultaneously visible or activated in each game build.

## Offline evaluators / acceptance

P82 checks: 3+ reviewed opposite examples yield stable posterior predictions; replay/patch mismatch fail closed; every action/whim categorized once including neutral/unknown; ML never sets `execute_allowed` or `cancel_allowed`; no player-directed queue mutation; explicit pin opt-in and visible exact whim; wrong Sim/whim/capture, absent calibration and player input reject; optional legacy listener unaffected. P07: source + CI + merge with readback. **P08 open:** local Windows Sims 4 specific patch/hitbox, 5+5 baseline/modified needs tests, genuine whim pin post-click proof, player-interrupt quarantine, and quest updates. Offline PASS != installed mod.

## P82 evaluation beyond unit success

`prequential_evaluate` applies each consented, operator-reviewed event **after** predicting its outcome, to avoid training/test leakage. It reports exact reviewed denominator, issued predictions, coverage, overall precision and distinct positive/negative precision, with `null` for undefined precision. The caller may compare this evaluation to the existing `judgment_learning` model's prequential baseline. These are *offline reviewed-example results*, not proof that Sims autonomy becomes more socially successful in a live save.
