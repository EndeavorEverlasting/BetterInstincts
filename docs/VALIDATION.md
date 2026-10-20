# Validation and release gates

## Offline (safe in any host)
From repo root:
```sh
python -m unittest discover -s tests -v
python scripts/validate_doctrine.py
python scripts/check_tracked_assets.py
python -m scripts.check_backward_compat --base-ref <git-base-sha>
python -m betterinstincts.priority
```
No network, EA installation, privileged permissions, or external Python packages needed. CI proves only these offline checks, never game compatibility.

## Local cert progress and compatibility (game evidence UNPROVEN)
Follow [the live-cert CLI instructions](LIVE_CERT.md) and [BI-002's executable gates](../plans/active/BI-002.execution.v1.json). Agents record observed trials, query status after every trial and deliver gameplay capture references. `MEASUREMENTS_PASS_REVIEW_REQUIRED` is **not a certificate**. CI protects older certified patch profiles; it cannot observe Sims or validate the package's in-game functionality. UNKNOWN_VERSION and UNVERIFIED must never be promoted silently.

## Gameplay gate (UNPROVEN)
Record date, OS, base-game patch, installed DLC, Mods manifest, Sims 4 Studio build, tested package hash, explicit install destination (chosen by user), and a disposable test save. Never touch original/production saves. Perform repeatable baseline+modified sessions on the same reset state; avoid stale script caches when game instructions require clearing them. Keep reproducible notes/sanitized error logs. Stop and roll back if action loops, frozen queues, unexpected forced interactions, cross-household effects, performance regression or lost gameplay.

Minimum manual acceptance for BI-002:
- One narrow urgent-hunger autonomy behavior materially improves over vanilla under comparable conditions.
- Player-directed action is not cancelled, reordered, or interrupted by our module.
- With feature disabled/removed, behavior returns to baseline; save loads.
- No unexplained exception, recurring spam, or significant slowdown.
- Identify collisions with Smarter Self-Care, MCCC, Better Sleep Autonomy and applicable overrides; test separate mod combinations rather than assert blanket compatibility.
- Package installs/uninstalls in a documented, explicit directory; no unexpected disk writes.

## Publication gate
Release only if a playable build actually passed the gameplay gate on a named patch, has install/uninstall instructions, known limitations, license/dependency disclosures, changelog and rollback instructions. Label untested patches **unknown**. New EA patches require rerunning compatibility proof. Report built != locally tested != merged != live-proven.
