# Asynchronous workflow interoperability — operator-first contract

**Authority:** [workflow-interoperability.v1.json](../contracts/workflow-interoperability.v1.json) / [control-handoff.v1.json](../contracts/control-handoff.v1.json). **Code:** [workflow_interop.py](../betterinstincts/workflow_interop.py) and [playwright_interop.py](../betterinstincts/playwright_interop.py). **Location owner:** [workstation-paths.v1.json](../contracts/workstation-paths.v1.json) / [bootstrap.py](../bootstrap.py).

## Terminal user value

A human types, clicks, works in another application, or uses The Sims while an explicitly activated agent job remains queued. **The agent yields immediately at its next guarded boundary, does not cancel the intended work, stays silent, and retries only after at least 15,000 ms of trusted desktop-wide inactivity.** New human input restarts the wait. A browser action must not race an agent's own Sims automation; all participating input executors share the single desktop lock.

This is **not** permission to run unattended, overwrite a player's command, or edit saves. No global keyboard hook, key logs, daemon, cron, scheduled task, autostart, or invisible browser-launcher is installed. Fresh observation, active session, scene/save ownership, target verification, and one-action admission remain independent required gates. Unknown input age is not proof of idleness.

## P00/P01/P124/P95/P92 ownership map

| Layer | Owner | Rule |
| --- | --- | --- |
| Governance | `AGENTS.md`, `docs/DOCTRINE.md` | Human input is authoritative; never interrupt or delete player activity |
| Harness | contracts, `tests/test_workflow_interop.py`, `tests/test_bootstrap.py` | Regression checks and machine-readable policy precede live deployment |
| OS screen admission | `control_handoff.py` and `screen_admit.py` | **Minimum** 15 seconds; two fresh probes before each UI effect; one user-scoped desktop lock across worktrees |
| Cross-agent waiter | `workflow_interop.py` | Bounded ordered intents and silent wake/retry while the active agent stays alive |
| Browser adapter | `playwright_interop.py` | Reuse an injected existing Playwright page; one click/fill; never spawn a new context |
| Game adapter | existing `scripts/*` host admission | Session/PID, scene, protected-save and player-queue checks still required |
| Effect channel | `ui_chrome` input_preference + `win32_input` | **Prefer hotkeys/KEY over mouse** when equivalent; mouse is fallback only; no global keyhook |
| Cursor park | `camera_traverse` + `win32_input.park_safe_cursor_rest` | After any mouse effect, park **SAFE_CURSOR_REST** (default 48px edge band). Never leave the cursor on the Sims viewport/screen edge. |
| Machine paths | `bootstrap.py:paths` | Canonical dev/use/worktree roles, no arbitrary duplicate clones |

### States and control transitions

```text
Agent: ENQUEUE work_id + typed callback
  -> CHECK active session + trusted idle >= 15 seconds
  -> if recent/unknown input: WAITING_FOR_USER (work retained; quiet poll)
  -> if lock owned by another agent: WAITING_FOR_AGENT (work retained)
  -> acquire desktop-shared.lock
  -> double-check idle -> revalidate exact page/scene/save/queue/target
  -> before EVERY UI effect: double-check idle again
  -> one preferred effect (hotkey/KEY when catalogued; else one click/fill/host step)
  -> recorded outcome: COMPLETED
  -> partial/unknown effect, stale target: NEEDS_RECONCILIATION/NEEDS_REVALIDATION
```

Prefer catalogued hotkeys over mouse clicks whenever equivalent (`preferred_effect_channel: HOTKEY_THEN_MOUSE_FALLBACK`). Keyboard chords still need dual idle probes, but they avoid relocating the cursor into a fight with the operator. A fresh mouse/keyboard event while waiting does not call `Task.cancel()`; it simply leaves the next intent queued. An action with any approved effect checkpoint is **not** blindly replayed after interruption: it is quarantined for outcome reconciliation because a click or key may already have happened. Callbacks must split longer tasks into short, idempotent, re-observable UI steps. A long, uncooperative Playwright operation or a separate process that ignores this contract **cannot** be preempted by these Python modules.

### Playwright adaptation example

```python
from betterinstincts.workflow_interop import CooperativeScreenQueue
from betterinstincts.playwright_interop import enqueue_playwright_step
from betterinstincts.player_presence import probe_windows

# Run only within an explicitly authorized agent session. On Windows,
# probe_windows(None) supplies a best-effort OS input-idle observation.
queue = CooperativeScreenQueue(
    probe=lambda: probe_windows(),
    session_active=lambda: actual_agent_session_is_active(),
)
enqueue_playwright_step(
    queue, work_id="one-reviewed-click", page=existing_page,
    selector="#reviewed-action", expected_url=observed_current_url,
)
await queue.drain(max_checks=120)
# If still waiting, keep the queue object alive and call drain again.
# NEEDS_REVALIDATION and NEEDS_RECONCILIATION demand fresh operator review.
```

`actual_agent_session_is_active`, `existing_page`, and `observed_current_url` are injected host/agent evidence, **not** supplied implementations. This module does not install or run Playwright. An agent may not treat an offline test as proof that a real browser, Linux desktop, or local Sims game is under the cooperative contract. On Linux, provide an independently verified, explicitly permitted OS idle probe; the Windows probe fails closed there.

### Async microsystems and game modes

Existing `host_listener` / `host_tandem` own game observations and Live/Buy/Build context. The waiter owns only **computer-input resource admission**, not need evaluation, Sim goals, lesson plans, or mode classification. Live needs actions must still be blocked in Buy/Build or unknown mode. Cooperative adapter adoption is required per executor: wrapping only one entrypoint does **not** retrofit other Playwright instances or legacy Sims action callbacks. Do not cancel an actual player-directed Sims queue to pause BetterInstincts. If a long in-flight callback cannot cooperate at effect checkpoints, reconcile it explicitly; do not promise an instantaneous OS-level interruption.

## P92 portable canonical location and lifecycle

`bootstrap.py` is a **stdlib-only, inspectable, user-scoped bootstrapper**. It never installs a mod package into Sims or changes a machine-wide service. Profiles:

| Role | Windows rule | Linux Mint rule |
| --- | --- | --- |
| Development checkout | `%USERPROFILE%\\dev\\BetterInstincts` | `$HOME/dev/BetterInstincts` |
| Use/launcher | `%LOCALAPPDATA%\\BetterInstincts\\app` | `${XDG_DATA_HOME:-$HOME/.local/share}/betterinstincts/app` |
| Worktrees | `%USERPROFILE%\\dev\\.worktrees\\BetterInstincts` | `$HOME/dev/.worktrees/BetterInstincts` |
| Input locks | `%LOCALAPPDATA%\\BetterInstincts\\runtime\\locks` | `${XDG_DATA_HOME:-$HOME/.local/share}/betterinstincts/runtime/locks` |

The shared lock path is resolved from the user profile by `bootstrap.paths().locks`, **not** from the current source checkout. Independent worktrees can no longer create independent desktop-control locks. A non-private lock directory or unresolvable profile fails closed; read-only presence policy remains usable because lock-path resolution is lazy.

These are **tracked rules, not proof** of where a particular user's pre-existing clone is located. Bootstrapper refuses a conflicting noncanonical checkout; reconcile a pre-existing checkout before cloning again. Use path contains one managed launcher and one identity+SHA-validated manifest. Entry point runs the existing **offline opt-in host-listener CLI** only. It does not claim a playable Sims mod.

### Install and uninstall from the repository home page

1. Download and inspect [bootstrap.py](../bootstrap.py) from the trusted repo, outside any checkout being installed.
2. Double-click the trusted script using Python, or run `python bootstrap.py gui` for a local window with **Inspect paths**, **Install** and **Uninstall** buttons. Opening it has no installation side effects. **Uninstall** always asks for confirmation; cancel is a no-op. If Tkinter or a graphical desktop is unavailable, use the CLI below.
3. Run `python bootstrap.py doctor` to print the derived locations.
4. Run `python bootstrap.py install`. It clones the exact GitHub origin into the canonical development directory **only if absent**, then creates the use-path launcher and manifest.
5. Run `python bootstrap.py uninstall` to remove the manifest-owned launcher and manifest. A clone created by the bootstrapper is removed only when the worktree is clean, **exactly one Git worktree remains**, and the recorded install-time HEAD, branch, Git refs, reflogs, Git config, custom Git-private metadata and linked-worktree signature still match exactly. Clean-looking but unpublished commits or local branches are preserved. A legacy manifest without this provenance cannot authorize checkout deletion. Otherwise it preserves the checkout and reports the reason for manual review.

No unsafe forced directory removal, no deletion of user saves, mods, local experiments, or untracked files. A mutated launcher, unexpected installation file, symlink, or tampered manifest blocks deletion. A user-provided checkout is never adopted as disposable. For a complete removal of a modified installer-created clone, reconcile/export the unique work first, then rerun uninstall from a trusted external bootstrapper.

## P83 independent review — 2026-11-09

P83 resolved as Moonwake's **Agent Work Verifier & Iterative Advancer** from the canonical prompt catalog (owner `repository-work-ledger-prompts.v1.json`, source blob `e1d571b5490a68292c1953dd7b1ecf6ee28fe96c`). The prior #86/#88 tests were green but did not falsify two material hazards: a clean checkout may still have unpublished Git work, and separate checkout-local lock roots allowed cooperating agents to race. The correction also makes 15,000 ms the **hard admission minimum**, not a default that a script can override with 1,000 ms.

- **Git deletion gate:** `bootstrap._clone_signature` records exact install-time refs, reflogs, head/branch, config and extra Git hooks/info. `uninstall` removes only an installer-owned pristine clone with matching provenance. A pre-existing/modified/legacy clone is preserved. Uninstall atomically reserves the **same exclusive desktop lock** held by cooperative game/browser executors throughout checkout removal, closing the check-then-delete race; active or stale lock files block uninstall before any managed file is removed. Only empty app-owned lock directories are pruned after the lease releases. Host-listener and host-automate CLI defaults now both import the canonical 15-second value, rather than retaining the historical 8-second bypass.
- **Computer-control gate:** `control_handoff.canonical_lock_root` resolves a stable user-profile location across independent repository/worktree copies, with private POSIX permissions. Pure read-only presence decisions do not need working host paths; input mutation still does.
- **Proof:** isolated Git-repository fixtures exercise unpublished commits, local branches, detached linked worktrees, changed Git config and hooks, legacy manifests, busy locks and a racing second executor; existing listener/Playwright tests preserve 15s operator priority. Repository CI is offline validation, **not** live two-agent/game certification. Uncooperative external Playwright instances must still adopt the adapter.

## Trifecta proof (P08 / P82 / P07)

- **P82 synthetic:** inactivity 14.999s waits; 15s resumes; second sample interruption waits; competing desktop owner waits; scene drift halts; partial effect never auto-replays; duplicate/cap limits hold. Bootstrap tests validate clone ownership, manifest drift, symlink and extra-file refusal.
- **P07 integration:** test-runner and repository CI must pass before merging; consultation must predate *all* affected behavior files.
- **P08 live certification remains OPEN:** on the actual Windows host, verify inactive and actively typing humans, agent Playwright and game executors, 15-second resumption, no focus theft, process restart behavior, clean install/uninstall, and production/use launcher readback. BI-002 live hunger remains independent.

**Proof dimensions:** remote main integration; canonical development checkout current; production/use path installed; real launcher observed; browser/game action observed are separate fields. Do not infer one from another. Existing `host_tandem` and any unmodified Playwright instance are not universally covered merely because this protocol exists.


## 2026-11-09 — screen atlas and camera-safe game pointer

The bounded screen-action extension is [SCREEN_ATLAS.md](SCREEN_ATLAS.md), `contracts/screen-atlas.v1.json` and `betterinstincts/screen_atlas.py`. It **composes**, not replaces, the existing `ui_chrome` target map, `scenes`, `camera_traverse.safe_rest_point`, hidden-object console glossary and this cooperative queue. Use `python -m scripts.screen_atlas inventory` to inspect available screen/action names. Exact-build target calibration, independent scene cues, an already-owned Playwright-hosted game page and fresh 15s idle are mandatory before a click. A second admitted effect parks the cursor in the interior; after human interruption, no cursor fight or blind replay. The additional injected `enqueue_native_game_click` port accepts exact native PID/session, foreground PID and window origin while reusing the same queue. It does not bypass `screen_admit` or dispatch Win32 on its own. Live Win32 caller adoption and observed no-pan game proof remain P08/local-agent work. Do not assume that Playwright automatically sees a native Sims game.

## 2026-11-09 — Foreground PID diagnostics and voice-safe input handoff

The canonical `player_presence.probe_windows` now reports only the foreground PID and executable **basename** as ephemeral diagnostic hints, while the actual desktop control gate still depends on trustworthy system-wide `GetLastInputInfo` age. It never captures or persists window titles, process paths, outside-app keystrokes, speech, or an application-usage history. Being in a non-Sims PID is not itself proof of user activity; a recent mouse/key event anywhere blocks takeover. Call `python -m scripts.control_handoff --session-id SESSION --process-id PID --idle-ms 30000 --operator-busy` for explicit voice dictation / hands-free activity that does not produce input events. The busy state must be provided to each new decision and does not install a watcher. Idle thresholds 30/60/120s are supported (canonical minimum remains 15s). The cooperative in-memory queue retains intentions; screen input still requires fresh two-probe step admission.

The legacy skill-force cursor-stability idle bypass was revoked because a stationary cursor while someone types/dictates is not a trustworthy idle signal. Reward-trait/level-up blind Enter and coordinate clicks are now held for identification, with safe likes/dislikes evaluation in [PREFERENCE_PROMPTS.md](PREFERENCE_PROMPTS.md). No automatic screen seizure, unverified dialog dismissal or game certification is claimed.
