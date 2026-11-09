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
| OS screen admission | `control_handoff.py` and `screen_admit.py` | Default 15 seconds; two fresh probes before each UI effect; one desktop lock |
| Cross-agent waiter | `workflow_interop.py` | Bounded ordered intents and silent wake/retry while the active agent stays alive |
| Browser adapter | `playwright_interop.py` | Reuse an injected existing Playwright page; one click/fill; never spawn a new context |
| Game adapter | existing `scripts/*` host admission | Session/PID, scene, protected-save and player-queue checks still required |
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
  -> one click/fill/host step
  -> recorded outcome: COMPLETED
  -> partial/unknown effect, stale target: NEEDS_RECONCILIATION/NEEDS_REVALIDATION
```

A fresh mouse/keyboard event while waiting does not call `Task.cancel()`; it simply leaves the next intent queued. An action with any approved effect checkpoint is **not** blindly replayed after interruption: it is quarantined for outcome reconciliation because a click may already have happened. Callbacks must split longer tasks into short, idempotent, re-observable UI steps. A long, uncooperative Playwright operation or a separate process that ignores this contract **cannot** be preempted by these Python modules.

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

These are **tracked rules, not proof** of where a particular user's pre-existing clone is located. Bootstrapper refuses a conflicting noncanonical checkout; reconcile a pre-existing checkout before cloning again. Use path contains one managed launcher and one identity+SHA-validated manifest. Entry point runs the existing **offline opt-in host-listener CLI** only. It does not claim a playable Sims mod.

### Install and uninstall from the repository home page

1. Download and inspect [bootstrap.py](../bootstrap.py) from the trusted repo, outside any checkout being installed.
2. Run `python bootstrap.py doctor` to print the derived locations.
3. Run `python bootstrap.py install`. It clones the exact GitHub origin into the canonical development directory **only if absent**, then creates the use-path launcher and manifest.
4. Run `python bootstrap.py uninstall` to remove the manifest-owned launcher and manifest. If this bootstrapper created the checkout and Git reports **no tracked, untracked or ignored changes**, it removes that clean clone too. Otherwise it preserves the checkout and reports the reason for manual review.

No unsafe forced directory removal, no deletion of user saves, mods, local experiments, or untracked files. A mutated launcher, unexpected installation file, symlink, or tampered manifest blocks deletion. A user-provided checkout is never adopted as disposable. For a complete removal of a modified installer-created clone, reconcile/export the unique work first, then rerun uninstall from a trusted external bootstrapper.

## Trifecta proof (P08 / P82 / P07)

- **P82 synthetic:** inactivity 14.999s waits; 15s resumes; second sample interruption waits; competing desktop owner waits; scene drift halts; partial effect never auto-replays; duplicate/cap limits hold. Bootstrap tests validate clone ownership, manifest drift, symlink and extra-file refusal.
- **P07 integration:** test-runner and repository CI must pass before merging; consultation must predate *all* affected behavior files.
- **P08 live certification remains OPEN:** on the actual Windows host, verify inactive and actively typing humans, agent Playwright and game executors, 15-second resumption, no focus theft, process restart behavior, clean install/uninstall, and production/use launcher readback. BI-002 live hunger remains independent.

**Proof dimensions:** remote main integration; canonical development checkout current; production/use path installed; real launcher observed; browser/game action observed are separate fields. Do not infer one from another. Existing `host_tandem` and any unmodified Playwright instance are not universally covered merely because this protocol exists.
