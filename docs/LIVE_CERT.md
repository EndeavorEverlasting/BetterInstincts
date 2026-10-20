# Local gameplay certification evidence loop — contract v1

## What exists
`scripts/live_cert.py` is a **local-only evidence recorder and evaluator**. It never reads Sims game files, installs a mod, inspects Sims processes, polls the filesystem, or collects telemetry. It stores at most 150 bounded rows under `dist/live-cert/<run-id>/` in the repository, excluded from Git. A completed numerical evaluation is **not** a game certificate; it returns `MEASUREMENTS_PASS_REVIEW_REQUIRED` for independent review.

## Local agent quickstart (fill values from actual installed game)
From repo root (Python 3.11+; game Python is separate):
```sh
python -m scripts.live_cert init --run-id bi002-local-001 --game-version 1.121.342.1030 --platform windows --sims4studio-build VERIFIED_LOCAL_BUILD
python -m scripts.live_cert status --run-id bi002-local-001
```
**Example version is instructional only**; replace with the exact main-menu version. Before any command: select disposable save and explicit Mods root; record game version, enabled packs, S4S version, targeted hunger tuning and worktree status. No automatic game path discovery.

After **each actually observed** baseline, modified and rollback trial:
```sh
python -m scripts.live_cert record --run-id bi002-local-001 --stage baseline --trial 1 --seconds-to-eat 100 --min-hunger 0.2 --sim-lag-ms 50 --player-interruptions 0 --action-loops 0 --exceptions 0 --observation-ref capture:local-baseline-1
python -m scripts.live_cert status --run-id bi002-local-001
```
The numeric values in this example are **synthetic instructions**. Never reuse them as factual measurements. Minimum real observations: >=5 baseline, >=5 modified, >=1 rollback, with stable scenario and distinct capture references. Observations should include evidence captures/timecoded video or experiment notes actually made while the game was running. Use the same units and event definitions across test versions.

After building the game mod and recording its actual hash and vanilla tuning hash:
```sh
python -m scripts.live_cert attest --run-id bi002-local-001 --package-sha256 ACTUAL_64_HEX --tuning-source-sha256 ACTUAL_64_HEX --tuning-resource-id ACTUAL_GAME_RESOURCE --capture-ref evidence:review-001 --disposable-save-confirmed --user-selected-mods-root-confirmed
python -m scripts.live_cert evaluate --run-id bi002-local-001
```
The last command creates `dist/live-cert/<run-id>/report.json` and exits nonzero if incomplete/failing; even a zero exit is **only reviewed numeric observations**. For publication, human maintainer must verify the actual game, tuning, package, evidence and exact patch before signing a separate certification record.

## Machine-observable progress and harness hooks
- **INIT** creates a bounded run manifest; CLI refuses overwritten run IDs.
- **RECORD** appends validated stage/trial rows and emits the updated counts/verdict as JSON; duplicate stages/trials, negative metrics, unsafe paths and excessively large event streams fail.
- **STATUS** returns completion counts and `next_gate`, without mutating; agents can run this after each trial to report progress. No background daemon.
- **ATTEST** adds manually verified identifiers/hashes; does not forge or infer data.
- **EVALUATE** writes bounded report, returns numerical pass/fail/incomplete, never emits `CERTIFIED`.
- **PR/CI** validate contracts/synthetic regressions and older certified profiles; a local gameplay recording is not reclassified by CI as observed runtime proof.

## Metrics (predeclared for BI-002)
Median time to begin eating improves by >=15% over >=5 vanilla trials, no player queue interruptions, no action loops or exceptions, modified median observed lag <= max(120% baseline, baseline+5ms), rollback smoke safe. Results are a prototype measure, not universal balance judgment. If vanilla already performs well or the experiment harms gameplay, report falsification and revisit the behavior choice with recorded evidence.

## Privacy and storage
The run receipt contains no OS user paths, save name, household IDs, Sims data, personal names or background collections. Put capture identifiers, **not personal URLs/private screenshots**, in observations. Keep raw media out of Git. A local agent may summarize sanitized evidence in a PR; it must not commit generated `dist/` or personal save data. No automatic upload or hidden telemetry.
