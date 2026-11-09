# P04 — BetterInstincts safe local install + household skills P08 certification

## LAUNCH ORDER — one existing Windows local agent, one live screen owner

1. **LOCAL-00: Canonical checkout & preservation (read-only first).** Inspect actual Windows checkout, working tree, worktrees, remotes, main, overlapping local agent tasks and installed-use manifest. Reconcile latest `origin/main` by safe fast-forward only when clean and permitted. Preserve unique or dirty work; do not clone elsewhere merely to avoid a dirty tree.
2. **LOCAL-01: Toolkit installation and readback.** Use the already-verified canonical checkout and `bootstrap.py doctor` / `bootstrap.py install`; verify managed launcher + install manifest, exact checkout SHA and use-path. This is *not* a Sims Mods install. Do not touch Sims saves, Mods, registry, services, scheduled tasks or active Cursor user rules.
3. **LOCAL-02: Live-game preflight, observation only.** Locate current game PID, exact full version, foreground, window/client dimensions, patch/pack, two scene cues, offline mode, an explicitly approved disposable save, first selected portrait and stable ordered original roster of N. Confirm no other live input owner and a user-first host session. Never create a Sim or Servo to change N.
4. **LOCAL-03: Validate per-cell observer/input-safety seam.** P83 found that CLI `--roster-key` values are only operator/local-agent assertions and the existing executor compares that list to itself; it does not recapture a real portrait each cell. Inspect actual installed adapters and implement/validate the smallest game-capable per-step portrait/roster and fresh player-presence gate before any bulk `household --execute`. The remote offline tests did not prove this. No blind bulk execution.
5. **LOCAL-04: P08 bounded Handiness canary.** On the disposable save only, observe first portrait + Handiness baseline, dispatch one reviewed cell, allow bounded 1x play and re-pause, observe Skills panel level 10. If N>=2, prove one Space transition independently selects the *next original* portrait without reopening the console and remains player-safe. Stop if changed roster/unclear state. If N=1, don't add another household member just to test Space.
6. **LOCAL-05: P08 protected regressions and incremental progression.** Verify player input interruption, one foreground owner, online-only refusal, no new household members, no camera drift and no blind retry. Then repeat one skill across all original N, followed by next skill, only with per-cell evidence. Respect skill availability per original Sim and installed packs; unsupported skills are recorded NOT_APPLICABLE, not falsely PASSED.
7. **LOCAL-06: P07 convergence and receipts.** Preserve private screenshots/logs in ignored `dist/` only. Record exact SHA/build, scenes, before/after panels, protected control and outcomes in sanitized tracked ledger/PR. Run relevant unit/CI checks and merge authorized validated repairs. Report separately local checkout, managed launcher, local entrypoint, UI command sent, panel observed and live certification.

**Machine dispatch:** `plans/active/BI-HOUSEHOLD-SKILL-LOCAL-P04.dispatch.v1.json` defines typed lane dependencies and gates. **Runtime placement:** LOCAL_AGENT_RUNTIME; remote GitHub is a provider, not a Windows desktop. The work is serial because game-input ownership and prior gates form one critical path. The current chat cannot install into Windows and has not launched the local agent.

## Parent objective and hard stops

Keep the original active household roster fixed while leveling the requested skill across every existing eligible portrait to target 10, then proceeding to the next skill. This is a skill-first (not member-first) traversal. No new Sim, Servo, pet, CAS addition, household merge, Build/Buy purchase/change, EA Connect, Store, Gallery, login/online activity, save replacement, or detached/parallel game-input worker. Avoid unrelated side quests. Player direction beats agents. A game input effect requires an authorized, current screen lease and actual observation. A missing or unknown game/save/portrait/scene/patch means **STOP BEFORE INPUT**.

## Repository floor, precise identities, and prompt provenance

- Original verified change: PR #146 merged to `main` as `5ebe8f74f6869556d947c964aa1392e92fa10259` (minimum ancestor, not a frozen latest head). The post-merge CI passed. This P83 follow-up must be read from freshly fetched `main` after its PR is integrated.
- P83 = Agent Work Verifier & Iterative Advancer. P95 designs the call stack, P124 preserves canonical owners, P07 integrates, P08 requires real runtime proof, P82 tests falsifiers; P04 = Repo-Aware Sprint + Harness Factoring Distributor. Resolve exact definitions from *current Moonwake*, don't trust alias memory alone.
- Canonical repo: `https://github.com/EndeavorEverlasting/BetterInstincts`; default branch `main`. Windows development: `%USERPROFILE%\dev\BetterInstincts`; managed launcher: `%LOCALAPPDATA%\BetterInstincts\app`; agent worktrees: `%USERPROFILE%\dev\.worktrees\BetterInstincts`. Rules, not proof of actual machine state.
- Read first: `AGENTS.md`, `docs/ONTOLOGY.md`, `docs/DOCTRINE.md`, `docs/HOUSEHOLD_JUDGMENT.md`, `docs/DIY_SKILL_FORCE.md`, `docs/ASYNC_INTEROP.md`, `docs/SCENE_INTELLIGENCE.md`, `docs/LIVE_CERT.md`, `docs/COMPATIBILITY.md`, `contracts/diy-skill-force.v1.json`, `contracts/household-judgment.v1.json`, `scripts/diy_skill_force.py`, `bootstrap.py` and this manifest.

## Local Windows checkout / install gate — actual commands after discovering current path

Use PowerShell from the canonical checkout. **Do not run the modifying commands until the current checkout and its unrelated changes are understood.**

```powershell
$dev = Join-Path $env:USERPROFILE 'dev\BetterInstincts'
Test-Path -LiteralPath $dev
git -C $dev status --short --branch
git -C $dev remote get-url origin
git -C $dev worktree list --porcelain
git -C $dev branch --show-current
git -C $dev fetch origin --prune
git -C $dev rev-parse origin/main
git -C $dev merge-base --is-ancestor 5ebe8f74f6869556d947c964aa1392e92fa10259 origin/main
```

If the checkout is absent, obtain and inspect the original `bootstrap.py` from the verified repository source outside the intended checkout, run `python bootstrap.py doctor`, then `python bootstrap.py install` to create the canonical checkout and manifest. If the checkout exists, only a clean current tracking branch may fast-forward (`git pull --ff-only origin main` from that confirmed branch). Otherwise preserve and reconcile original work under a dedicated approved worktree; never `reset --hard`, `clean`, delete branches or create a duplicate canonical clone.

After verifying the checkout includes the relevant merged code and there is no conflicting local writer:

```powershell
Set-Location -LiteralPath $dev
python -m unittest tests.test_diy_skill_force tests.test_household_judgment tests.test_bootstrap tests.test_screen_admit -v
python scripts/validate_doctrine.py
python -m scripts.check_ontology
python bootstrap.py doctor
python bootstrap.py install
python bootstrap.py doctor
python bootstrap.py household-skills
```

Verify the manifest and launcher in the actual managed use directory by *readback*, not installation return code alone. Distinguish `origin/main`, local checkout HEAD, use launcher bytes/manifest and real invoked launcher. The launcher is **not** a packaged Sims mod and `bootstrap install` will not update an existing repository by itself.

## Game observation and safe canary

Use an explicitly disposable, operator-authorized save. Capture actual full game build and two independent Live/Build/Buy scene cues before any game action. Existing `scripts/game_capture.py` can produce a PrintWindow bitmap, but that bitmap does not itself classify selected portrait, scene, Skills level or goal. Beware black/unknown captures and focus drift. If an exact on-screen roster observer cannot be proven, **perform observation-only and report `P08_BLOCKED_PER_CELL_SENSOR`**, not simulated success.

```powershell
python -m scripts.diy_skill_force catalog
python -m scripts.diy_skill_force household --members 3 --skill handiness
python -m scripts.host_listener activate --session-id VERIFIED_LOCAL_SESSION
python -m scripts.host_listener status --session-id VERIFIED_LOCAL_SESSION
```

`3` is an illustrative **plan-only** N; substitute observed count and identities. Do not copy illustrative IDs or mark a `--first-portrait-attested` flag without a fresh selection observation. Do not run the bulk household `--execute` merely because CLI arguments pass validation. In the safe certified local path, the local agent should verify each selected portrait, each actual observed skill delta, console closure, Space transition, player-idle gate and original roster preservation. If resuming after save reload, a previous `DISPATCHED` ledger entry is only a typing receipt; use actual panels to decide which cells need redo. Never relabel it `PANEL_OBSERVED_MAX` without a witnessed read.

Native Win32/game control only; no imagined Playwright DOM for Sims. No screenshot upload to GitHub, no private save names or personal OS paths committed. Use `dist/game-host/household-skill-cert/` for bounded raw local receipts/captures. Later, sanitize a narrow durable proof in the tracked ledger and link only nonprivate references.

## P08 required proof matrix

| Claim | Required game evidence | If missing |
|---|---|---|
| Installer ready | manifest + launcher readback + canonical checkout HEAD | INSTALLED_UNPROVEN |
| Live scene/save | exact build, 2 cues, disposable save attested | GAME_PREFLIGHT_BLOCKED |
| First selected Sim | original ordered portrait roster + selected portrait read from actual game | NO_SKILL_INPUT |
| One skill cell | before/after Skills panel at target 10 after play-brief and re-pause | DISPATCHED_ONLY_NOT_PASS |
| Space traversal | evidence second original portrait selected, console closed, no wrong target | SELECTION_UNPROVEN |
| Player safety | interruption stops next effect; no competing input worker | PLAYER_INTEROP_UNPROVEN |
| Offline & household integrity | no online transition, original N unchanged, no CAS/Buy | REGRESSION_UNPROVEN |
| Mainline reconciliation | local branch and GitHub PR CI exact SHA merged readback | COMMITTED_NOT_MERGED |

**P83 findings preserved:** a typed cheat ledger can cause an unsafe `ALREADY_MAXED` claim; the review change gives ledger-only cases a separate `NO_PENDING_DISPATCH_UNVERIFIED` state and avoids game input when nothing remains to dispatch. The prior executor's roster-check compares supplied values with themselves rather than a live screen sensor. A single screen lease in `_execute_plan` spans multiple UI events; local agent must revalidate/adapt before unattended bulk execution. A successful remote unit test does not close these Windows gates.

## Final report contract

**CHANGED | PROVED | NEXT:** exact git floor, tracked edits if any, test commands/results, installer manifest/use-path readback, named live observations with capture references, fixed roster N, number of observed skill cells vs dispatched cells, protected control, GitHub PR/merge SHA, unknowns/blockers, one next command. Preserve all previous approved work and local user rules. Before editing active Cursor instruction settings, archive and verify them; repository `.cursor/rules` is not proof of account-wide activation.

**First executable local action:** open the existing canonical BetterInstincts repository in Cursor, read this handoff, and run the read-only LOCAL-00 checkout/dirty-state checks above. Do not start with `--execute` or create a new household.
