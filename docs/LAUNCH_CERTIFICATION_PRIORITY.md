# Certification-first Sims save handoff (MoonWake Sixth Gear)

**Status:** repository policy and read-only launch-receipt integration. This has not loaded a save or operated the local Windows game. The observed Video Gaming preference offer and its ignored Windows evidence remain local.

## Windows certification entry point

Double-click `Continue-BetterInstincts-Certification.cmd` from the BetterInstincts checkout on the Windows game host. This launches the installed Codex CLI with the [current-session task](LIVE_CERTIFICATION_HANDOFF.md), retaining the current game and using existing host permissions. It requires Python 3.11+ and an installed, signed-in Codex CLI on PATH with access to the existing local game tooling. The existing Install and Play launcher still handles ordinary startup.

When the local evidence is in a different worktree, the updated source can stay in a separate checkout. Run this from its root in PowerShell, using the path to the existing local evidence worktree:

```powershell
.\Continue-BetterInstincts-Certification.cmd --checkout "C:\path\to\existing\trial-worktree"
```

The startup sample gives the agent the running Sims PID when it can find one. A missing memo routes the agent to recover existing evidence. The game action, GitHub evidence sync, and hunger-session transition are performed by the local agent using existing host adapters and review evidence. `python -m scripts.continue_certification --print-handoff` previews the task without a dispatch.

## Do not lose the active Video Gaming certification

The parent task is **finish the current Video Gaming ("IT BEGINS...") preference prompt certification first**, then return to standardized oldest-eligible-lab-save tests. The already completed vanilla/modded and prior Yes/No/rollback trials are **historical evidence**, not a reason to restart. The already-open/current prompt needs its own current outcome/readback if still required. Open PR #263 owns the native outcome binding, not this routing feature.

The first question at **every agent/game launch** is whether the *same current Sims game process and prompt* are still open. If so, preserve the session, capture fresh scene and recipient identity, re-use known mapping and prior read-only receipts, and finish only genuinely missing current-offer evidence with the existing player-first/native effect gates. **Do not click Resume, switch saves, relaunch, reset vanilla/modded trials, install a replacement observer, or assume an old response handled today's prompt.**

If Sims is not running, recover the **exact previously authorized lab save pinned for this certification**, using its independent run/capture/game-build binding; this may be a newer lab continuation. The oldest-first preference **must not override the pinned active certification**. If no pinned lab identity is supported, HOLD and recover local session evidence rather than selecting a convenient old or personal save. The launcher still does not automatically navigate menus or select a save.

For a new mechanic, independent review of **offer outcome + native effect + rollback** precedes the existing `scripts.save_candidate_priority` ranker. For a repeat of a reviewed mechanic, see the [repeat-offer path](#reuse-reviewed-evidence-on-a-repeat-offer). It considers only current-run operator-attested `LAB_DISPOSABLE` saves, oldest creation timestamp first; missing/tied chronology abstains. No age/date is authorization; all `USER_PROTECTED`, `UNKNOWN_PROTECTED` and `LAB_CONTINUATION` entries remain excluded from standardized disposable ranking.

## Cross-chat local continuity record

The local operator/agent maintains **one explicitly authorized private, ignored JSON memo** at `dist/game-host/active-certification.v1.json`, never inside the repository's tracked contract. The read-only route treats this as an *unverified operator memo*, not a freshly authenticated image of a running game. A fresh process/scene/readback check remains mandatory. No saves, personal names, screenshots or private host paths are committed.

Create the memo after reconciling the **real** existing local evidence (use actual observed run ID, version and status):

```json
{
  "schema": "betterinstincts.launch-certification-session/v1",
  "certification_id": "BI-VIDEO-GAMING-PREFERENCE-265965",
  "run_id": "REPLACE_WITH_REAL_LAB_RUN_ID",
  "game_version": "1.121.361.1020",
  "status": "PENDING"
}
```

Do **not** mark `REVIEWED_COMPLETE` because older Yes/No tests succeeded. After a genuine current-certification review, add:

```json
"status": "REVIEWED_COMPLETE",
"completion_review": {
  "reviewer_verified": true,
  "game_version": "1.121.361.1020",
  "current_offer_outcome_ref": "capture:REAL-CURRENT-OFFER",
  "native_effect_ref": "capture:REAL-NATIVE-EFFECT",
  "rollback_ref": "capture:REAL-ROLLBACK",
  "review_ref": "capture:REAL-REVIEW"
}
```

The second snippet is a **replacement/addition** to the original JSON object, not a standalone file. References above are illustrative, not actual capture or reviewer proof. Never fabricate or bulk-approve missing receipts. A local reviewer must inspect real source evidence; the CLI can check only JSON shape/distinctness.

When no game is running and the certification remains pending, supply `pinned_save` **only** from an explicitly current-run-bound lab registry entry:

```json
"pinned_save": {
  "save_id": "slot:REPLACE_WITH_REAL_LAB_SLOT",
  "alias": "BI_CONT_REPLACE_REAL_LAB_ID",
  "capture_ref": "capture:REPLACE_REAL_SLOT_CAPTURE"
}
```

Again, this is an illustrative fragment, not a completed local permit. Do not synthesize a lab slot from timestamps or copy a personal save to make a trial. The canonical `betterinstincts.save_policy.decide` checks the registry's origin, operator consent, exact run/build/capture and classification.

## Commands and launcher integration

From the BetterInstincts root after reading `AGENTS.md`:

```sh
# Existing paused game/process independently observed: preserve this certification
python -m scripts.launch_save_route --game-running-observed --game-version 1.121.361.1020

# No game observed: pinned lab certification candidate, advisory only
python -m scripts.launch_save_route --registry dist/game-host/operator-lab-register.json --game-version 1.121.361.1020

# AFTER genuine completion review: identical CLI returns ranked oldest lab candidates
python -m scripts.launch_save_route --registry dist/game-host/operator-lab-register.json --game-version 1.121.361.1020

# Offline safety checks (no Sims launch)
python -m unittest tests.test_launch_save_route tests.test_save_candidate_priority -v
```

`python -m scripts.first_run auto --fallback-gui` and explicit first-run CLI launch now include `lab_save_route` in their receipt. The Windows `Start-BetterInstincts.cmd` already calls that entrypoint. A missing/invalid memo returns `HOLD_CERTIFICATION_CONTEXT` and does not invent a default save or suppress the existing player-owned launcher. To actually reuse the pinned save, the human-first game host must separately recheck the scene, slot, game build, player presence and one-effect permissions; this advisory **never** grants `AUTO_SELECT`, `RESUME`, `LOAD_USER_SAVE` or a game control permit.

## Sixth Gear verification and remaining live gate

- **P141:** Rejected oldest-first before certification, newest-auto-pick, replaying already finished trials, and duplicate desktop clickers. Selected certification-first route within the existing save guard + boot receipt owners.
- **P95/P82:** State transitions and hostile missing-pin, historical-proof, wrong-build, unreviewed-completion, protected-save and tied-age cases are expressed as bounded pure routing logic and regression tests.
- **P08:** Real Windows `1.121.361.1020` process, current prompt readback, native effect, rollback and distinct reviewed receipts **cannot** be observed through GitHub and remain unproven for this new route. Do not confuse previous historical trials with fresh current-prompt proof.
- **P07/P124:** New route lives in `scripts/launch_save_route.py` and reuses `betterinstincts.save_policy` plus `scripts.save_candidate_priority`; the existing launcher only reports the route, never clicks a save. Keep #263's separate stacked preference/observer work intact.

BI-002's independent hunger 5+5 and rollback requirement remains a separate live-certification gate. Source tests or a GitHub merge do not close it.

## Household-scoped successor route

The current certification memo and its completion review must each carry the
same observed `household_id`. The next run's registry records carry that
`household_id` and `household_binding_confirmed: true` for each attested slot.
Use the explicit `--successor-run-id` and repeat `--household-id` for all freshly
observed available households. With multiple households, first persist the
player's choice through `scripts.instance_settings choose-household`.
The oldest eligible slot is returned as `candidate_save_id`. The live adapter
still owns exact menu observation and effect admission. Legacy unscoped ranking
is advisory and cannot be used to automate this transition.


## Reuse reviewed evidence on a repeat offer

Keep the original, reviewed `completion_review` references and the verified
certification household in the private memo. A repeat needs its own offer and
resolution captures and review, but historical native evidence does not need
to come from the current game process. Use the existing same-household and
distinct successor-run arguments after recording:

```json
"repeat_offer": {
  "household_id": "household:OBSERVED_ID",
  "game_version": "1.121.361.1020",
  "same_mechanic_reviewed": true,
  "resolution_observed": true,
  "offer_capture_ref": "capture:actual-repeat-offer",
  "resolution_capture_ref": "capture:actual-repeat-resolution",
  "review_ref": "capture:actual-repeat-review"
}
```

The review must establish that the prior proof applies. Use new references
for the repeat. The route reports
`HISTORICAL_CERTIFICATION_REUSED_REPEAT_OFFER_RESOLVED` and treats the oldest
eligible save as a candidate for the existing host loader.
