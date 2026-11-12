# BetterInstincts — Entire-observed local quality, independent of GitHub Actions

**Status:** Repository implementation + independent offline CI available. Actual operator-host Docker/Podman, Entire CLI and local Cursor-hook activation remain unobserved until a host receipt exists. This is not Sims gameplay certification.

## What owns what

- **Moonwake** `scripts/entire_host_cycle.cjs`: agent execution, bounded repair passes, failed-check feedback, private checkpoint/continuation state. DO NOT copy its loop here or run an editable CI test directly under your Windows login.
- **Entire CLI**: checkpoint and session provenance, read-only `agent-help --json`, `status --json`, `checkpoint list --json`. Does **not** replace a test engine, host privilege boundary, or game-state observation. This runner **never** enables hooks, modifies Entire configuration, pushes refs, logs into an account or uploads transcripts.
- **BetterInstincts**: the frozen executable quality list `contracts/local-quality-checks.v1.json`; isolated `scripts/local_quality.py`; one private receipt per executed source SHA; existing `docs/LIVE_CERT.md` and `plans/active/BI-002.md` own physical gameplay certification.

## Coverage of the current GitHub Actions workflow

The manifest maintains a fail-closed **minimum of 49 command invocations** (future additions may increase it), corresponding to every non-installation Python and Git diff command in the existing `.github/workflows/ci.yml`. Repeated invocations remain repeated until explicitly reviewed. The manifest compares all commands against the Actions source while the workflow exists; a missing or added check blocks the local plan. The Python `pip install` command from Actions is dependency provisioning and moves to the operator-reviewed sandbox image build, not a runtime check.

Included are full `unittest discover`, peripheral authority, Cursor desktop guard, human sovereignty, native EA-gate classifications, ontology consultation chronology, backward compatibility, horizon/host/progression/world evaluation, hidden item, asset leakage, scene protection, `git diff --check`, syntax compilation, and explicit supporting test modules.

**No GitHub token or GitHub Actions API is required to run these checks.** Git history is supplied read-only for base-ref validators. The committed source snapshot is copied to a disposable, networkless container. Output artifacts and `__pycache__` remain inside ephemeral storage.

## Read-only plan — trusted operator launcher

After the reviewed external-launcher copy step below, from a **clean BetterInstincts checkout**:

```powershell
$trusted = Join-Path $env:LOCALAPPDATA 'BetterInstincts\trusted-host'
python (Join-Path $trusted 'local_quality.py') plan --repo .
```

A plan validates the exact manifest and current Git SHA without invoking Entire, Docker, agent executors or any test code. **Both plan and run refuse the repository's own agent-editable Python launcher.** This is a project-scope preflight safeguard, not an OS privilege boundary.

## Once-only host provisioning (operator-reviewed)

The quality runner never builds/pulls an image. Provision a reviewed Python 3.11/Pillow/Git image in a separately authorized local host setup:

```powershell
docker build --pull=false -t betterinstincts-policy:py311-pillow -f tooling/host-quality/Dockerfile .
docker image inspect betterinstincts-policy:py311-pillow
entire status --json
entire checkpoint list --json
```

The checked-in Dockerfile installs dependencies at **image-build time** only; runtime check execution has `--network=none`, `--read-only`, `--cap-drop=ALL`, no-new-privileges, unprivileged UID, memory/PID/CPU bounds, read-only source/Git mounts and disposable writable tmpfs. Check and record local image digest for an immutable deployment. The bootstrap process does not run `entire enable`, `entire configure` or `entire login`.

**Public repository privacy gate:** Entire checkpoint push must independently report disabled in `entire status --json`. Do not allow session transcripts, prompts, secrets, real game saves or private desktop evidence into the public BetterInstincts Git refs. Use a separate private remote or local-only retention only through explicitly approved operator configuration, outside this runner. If the CLI schema changes or privacy state is unknown, the runner denies without guessing.

## Run offline quality inside a disposable container

Identify the exact reviewed base commit (for example, from `git merge-base main HEAD`). Then, as an explicit operator-authorized execution rather than agent-owned Cursor shell:

```powershell
# Review the repository revision, then copy the exact approved launcher to
# an operator-controlled directory OUTSIDE the agent-editable checkout.
$trusted = Join-Path $env:LOCALAPPDATA 'BetterInstincts\trusted-host'
New-Item -ItemType Directory -Force -Path $trusted
Copy-Item .\scripts\local_quality.py (Join-Path $trusted 'local_quality.py')
$reviewedLauncherBlob = 'c5aac4cfcf500f268a11cdb036d6586210c3a7c2'
$installedLauncherBlob = git hash-object (Join-Path $trusted 'local_quality.py')
if ($installedLauncherBlob -ne $reviewedLauncherBlob) { throw 'Launcher differs from the reviewed Git blob' }
# The blob SHA above is pinned to this PR revision. Re-review before changing it.

$base = git merge-base main HEAD
# Use the exact commit reviewed independently, not an unchecked agent-supplied HEAD.
$reviewedHead = '<reviewed-40-character-commit-sha>'
python (Join-Path $trusted 'local_quality.py') run --repo . --base-sha $base --expected-head $reviewedHead --authorize --engine docker
```

The runner requires a clean checkout, a separately reviewed launcher source outside the repository, an existing base SHA, an exact operator-reviewed HEAD SHA, enabled Entire CLI, verifiable local-only checkpoints, a preinstalled sandbox image, and exactly the checked-in manifest. It executes the **verified immutable image ID**, not an untrusted mutable image tag, and rejects host executable paths shadowed by the agent-editable repository. It writes a private JSON receipt at:

`%LOCALAPPDATA%\BetterInstincts\host-quality\<head-prefix>-<pid>.json`

or on Linux under `$XDG_STATE_HOME/BetterInstincts/host-quality/` (default `~/.local/state`). Output contains exact commit/base, manifest hash, per-check exit codes and hashes, Entire before/after query digests, and independent proof dimensions. No raw transcripts, raw check stdout, credentials, screenshots, or public proof uploads.

The command **must not** be run through an agent Cursor project shell hook: that hook intentionally refuses execution of mutable repository Python code with normal Windows privileges. Use a reviewed standalone operator-controlled launcher or Moonwake's independently authorized isolated execution lane. The repository's local test script is not a security product and cannot protect against an adversarial system administrator or a tampered Docker engine.

## Fifth Gear / sunset sequence

- **P141:** compared local direct execution, duplicate orchestrator, hosted replacements, Entire-only and isolated-host options; selected isolated host plus Moonwake continuity. See `plans/active/BI-ENTIRE-LOCAL-QUALITY-20261111.md`.
- **P95:** one host gate, existing Moonwake agent/feedback loop, distinct Entire checkpoint provenance, exact CLI proof.
- **P82:** invalid manifest, command drift, missing Entire/privacy, absent image, unsafe archive, unsupported host, file receipts and no-privilege sandbox falsifiers in `tests/test_local_quality.py`.
- **P08:** locally observe Docker and Entire CLI, match physical host run to exact source SHA, prove a benign Cursor allow/deny canary separately; live Sims BI-002 remains open and independent.
- **P07:** review, pass full independent regression checks, and integrate only when authorized.
- **P124:** no second loop or scheduler, one acceptance manifest, no duplicate GitHub Actions dependency at runtime.

**Do not remove the only current GitHub Actions workflow until a real host run proves every command in this manifest passed under equivalent isolation, actual Entire status/checkpoints were observed, and the owner explicitly accepts the replacement.** Once that happens, the local manifest remains canonical and the workflow can be removed in a separate scoped PR. Removing Actions without a host fallback would reduce the quality floor; that's not elimination of dependency, it's elimination of proof.

**Proof dimensions:** REPO_WRITTEN, UNIT_TESTS_PASSED, GITHUB_CI_PASSED, MAIN_MERGED, LOCAL_SANDBOX_EXECUTED, ENTIRE_CHECKPOINT_OBSERVED, LOCAL_CURSOR_HOOK_ACTIVE, WINDOWS_HUMAN_INTERRUPT_OBSERVED, GAMEPLAY_CERTIFIED are distinct fields and MUST NOT be collapsed.
