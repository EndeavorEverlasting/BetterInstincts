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
| Cursor park | `camera_traverse` + `win32_input.park_safe_cursor_rest` | After any mouse effect, park **SAFE_CURSOR_REST** (default 48px edge band). Never leave the cursor on the Sims viewport/screen edge. Edge→creek is `EDGE_CREEK_REGRESSION` (`live-host-ops` / `camera-traverse#edge_creek_regression`): park then Shift+Enter. |
| Live-host ops | `contracts/live-host-ops.v1.json` + `live_host_ops.py` | Chat corrections incomplete until repo-encoded. `PAUSED_PRODUCTIVITY_BEFORE_TIME_RISK`; yield to mouse/Wispr (`OPERATOR_RECLAIM`). |
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

## 2026-11-10 — Live HUD surface lease (Skills vs phone)

**Operator correction:** One agent opening Skills (`L`) and another opening the phone resets each other. Overlay-clear that dismisses a peer phone/panel is an interop failure. Desktop lock alone is not enough — Live exclusive HUD surfaces must be leased.

| Surface | Examples | Lock file |
| --- | --- | --- |
| `BOTTOM_RIGHT_PANEL` | Skills, Career, Needs, … | `hud-BOTTOM_RIGHT_PANEL.lock` |
| `PHONE` | Sim phone / Order UI | `hud-PHONE.lock` |
| `CHEAT_CONSOLE` | Ctrl+Shift+C | `hud-CHEAT_CONSOLE.lock` |

**Rule:** any two distinct surfaces conflict → `WAITING_FOR_AGENT` (retain work_id). Claim via `exclusive_live_hud_surface` under the same profile lock root as `desktop-shared.lock`. Assess first: `assess_live_hud_surface_claim("PHONE")` / `"PANEL_SKILLS"`. Overlay-clear withholds `peer_hud_leases` kinds (`PEER_LEASED_HUD_SURFACE`).

Owners: `workflow-interoperability.v1.json#live_hud_surface_lease`, `control_handoff.exclusive_live_hud_surface`, `workflow_interop.assess_live_hud_surface_claim`, `scene_ui_semantics.assess_overlay_clear_after_metadata`. Consultation `BI-LIVE-HUD-SURFACE-LEASE-20261110`.

```text
skills agent claims BOTTOM_RIGHT_PANEL
  -> phone agent assess_live_hud_surface_claim("PHONE")
  -> WAITING_FOR_AGENT (work retained; do not open phone / do not clear skills)
  -> skills completes / releases lease
  -> phone drain resumes after 15s idle + claim PHONE
```

## 2026-11-10 — Game input borrow / restore (watch YouTube while Sims ticks)

Authorized Live effects still need Sims focused for a moment (Windows delivers keyboard/mouse to the foreground window). That must **not** mean the agent monopolizes the desktop or leaves the operator trapped in Sims while they watch YouTube or use any other app.

Contract: `workflow-interoperability.v1.json` → `game_input_borrow_restore`. Live helper: `scripts.diy_skill_force._with_sims_input_borrow`. Assess: `assess_sims_input_borrow_cell`.

```text
WAIT trusted idle >= 15s (any mouse/key activity restarts the wait; work retained)
  -> SNAPSHOT operator foreground (YouTube / browser / IDE / …; remember last non-Sims hwnd)
  -> BORROW Sims briefly (<=8s wall; 1 effect; console batch <=60s)
  -> one armed effect (terrain RMB, panel letter, play/pause, console chord, …)
  -> RESTORE operator foreground (fallback LAST_NON_SIMS if prior was Sims)
```

**Multi-screen / other monitors (2026-11-10 correction):** Operator may work on another screen while Sims runs. Forbidden: long tip-sweeps or ad-hoc raw `_borrow_sims_foreground` loops that hold Sims for tens of seconds. **PrintWindow observation must not borrow** (`scripts/game_capture.py`). Computer-use screenshots that exclude Sims are not a substitute for PrintWindow.

**Resume ≠ OS cron.** When the operator is busy, host_listener ticks and skill-force helpers yield and keep the intent. Continuation happens when `GetLastInputInfo` age again clears 15s — via `CooperativeScreenQueue.drain`, host_listener tick, or `_wait_for_input_idle`. Do **not** install Task Scheduler, cron, autostart, or a keylogger daemon. Play-brief waits with the operator app restored so Skills can refresh while they keep watching. Typed cheat batches may hold the borrow until console close, then restore.

**Speaking to the agent (2026-11-10 regression):** voice/chat with the operator is operator activity even when Sims looks idle. Do **not** keep a Live SendInput job running while the operator is talking to the agent. Mark work retained / `WAITING_FOR_USER`, stop mid-beat actuation, and resume only after trusted idle (cooperative waiter). Explicit `operator_busy` covers dictation that emits no keyboard events.

**Away ≠ busy (2026-11-10 correction):** operator absence from the desk is not a blocker. Do **not** invent `operator_busy` / yield / “wait for user” from a quiet chat, a prior kill of an overlapping job, or agent uncertainty. Use OS last-input idle (≥15s) as the gate; when the machine is idle, continue Live certs (full catalog gaps — mischief, logic, wellness, robotics, gardening, etc.). Do not stop short of the canonical skill list.

## 2026-11-09 — Foreground PID diagnostics and voice-safe input handoff

The canonical `player_presence.probe_windows` now reports only the foreground PID and executable **basename** as ephemeral diagnostic hints, while the actual desktop control gate still depends on trustworthy system-wide `GetLastInputInfo` age. It never captures or persists window titles, process paths, outside-app keystrokes, speech, or an application-usage history. Being in a non-Sims PID is not itself proof of user activity; a recent mouse/key event anywhere blocks takeover. Call `python -m scripts.control_handoff --session-id SESSION --process-id PID --idle-ms 30000 --operator-busy` for explicit voice dictation / hands-free activity that does not produce input events. The busy state must be provided to each new decision and does not install a watcher. Idle thresholds 30/60/120s are supported (canonical minimum remains 15s). The cooperative in-memory queue retains intentions; screen input still requires fresh two-probe step admission.

The legacy skill-force cursor-stability idle bypass was revoked because a stationary cursor while someone types/dictates is not a trustworthy idle signal. Reward-trait/level-up blind Enter and coordinate clicks are now held for identification, with safe likes/dislikes evaluation in [PREFERENCE_PROMPTS.md](PREFERENCE_PROMPTS.md). No automatic screen seizure, unverified dialog dismissal or game certification is claimed.

## P00/P01 atomic effects and retained partial intent

New adapters call queue.enqueue_effect(work_id, validate, effect) for one bounded semantic/API/CLI or desktop effect. The queue supplies the immediate pre-effect checkpoint; break sequences into separate steps. live_host_ops.assess_interaction_channel prefers verified native capability, permits desktop fallback only on opt-in, and never grants execution.

Activity before effects retains pending work. Partial interruption retains the original intent in queue.suspended, marked NEEDS_RECONCILIATION. After observing outcome, call queue.reconcile(work_id, outcome_observed=True, completed=True), or provide an explicit QueuedStep remainder with the same ID. No original callback is automatically replayed. Remainders pass target validation, ownership and dual idle checks again. Pending and suspended work share the bounded budget. No watcher installed. Executing native calls cannot be forcibly preempted. Existing raw scripts and external agents must adopt the owners before claiming compliance. Offline tests are not live Sims certification.


## Cursor pre-effect admission — operator desktop boundary

For Cursor agents inside this repository, `.cursor/hooks.json` applies fail-closed `beforeShellExecution` and `preToolUse` gate checks through `.cursor/hooks/operator_boundary.py`. These **precede** shared desktop locking, 15-second idle confirmation and the game-specific save/scene checks; none substitutes for the others. A denied shell or file action is not a reason to disable hooks, reset Bluetooth, change screenshot preferences or invoke an alternate unguarded executor. Operator-reviewed OS maintenance belongs to a separate authorized workflow (SysAdminSuite). The guard intentionally permits only a short, measured set of read-only commands and offline checks; unknown commands fail closed and require review. See `contracts/operator-desktop-boundary.v1.json`, `tests/test_operator_boundary.py`, and `docs/PERIPHERAL_INCIDENT.md`.

This project-level hook does not reach non-Cursor harnesses, uncooperative computer-use agents, or direct commands outside the trusted project. Remote repository merge and local Cursor hook activation are independent proof dimensions.

### Game-host template-navigation admission

The `scripts/game_host.py` PyAutoGUI navigation path is not an exception to `admitted_screen_lease`: on Windows it now validates an active session and game PID, locks the shared desktop, confirms human-idle admission and exact Sims foreground before every template scan and each click. It does not focus/restore a different window to bypass these checks. Loss of ownership aborts with a blocked receipt; do not replay partial UI flows. `tests/test_game_host.py` contains four negative cases. Live Windows certification is still required.

## 2026-11-10 — Typed human-sovereignty effect admission

`contracts/effect-authority.v1.json` and `betterinstincts/effect_authority.py`
classify read-only `PASSIVE_OBSERVATION` / `BACKGROUND_REASONING`,
human-gated `SCREEN_EFFECT` / `GAME_MUTATION`, and always-denied
`OS_CONFIGURATION`. Missing/unknown class is denied. The pure policy cannot
be substituted for per-action `screen_admit` checks.

`CooperativeScreenQueue.enqueue_observation` is the reviewed read-only lane:
bounded local observation or processing can finish while the gamer is typing,
playing, using Wispr, or controlling another monitor. It requires an explicit
active session, and does not acquire the screen lock or change focus. UI/game
actions in the original queue **remain queued and paused** until trusted idle.
Both lanes share the 32-item cap; passive callbacks have a 2-second timeout
and no blind replay on ambiguous outcomes. A callback declaration is not a
sandbox: never pass untrusted code, Windows input, Playwright interactions,
game-state mutation, focus-changing capture, or save operations into it.

`scripts/check_peripheral_boundary.py` also rejects OS keyboard scancode and
accessibility changes, global input interception, registry mutations and existing
Bluetooth/PnP/capture preference controls. Print Screen, Escape and U are
operator-owned. It is a CI/static regression guard, **not** prevention of an
unadopted agent acting outside the repository. Local Windows game tests must
demonstrate physical takeover, release and no OS setting mutation.

### Human-first focus-borrow precondition (2026-11-10)

The canonical `admitted_screen_lease.ensure_ready()` uses **two fresh trusted
idle probes before any focus change**. If the game is not yet the foreground
window, the authorized focus callback runs once, followed by **two more
trusted samples**. Exact Sims foreground must be verified before returning
one game-input permit. Losing foreground between later actions requires fresh
admission and a new borrow; previously focused does not mean still focused.
`scripts/needs_force.py` now composes this same owner instead of carrying
a weaker duplicate one-sample focus preflight. Recovered mouse/keyboard input
while waiting prevents a new focus borrow rather than shutting down devices.
