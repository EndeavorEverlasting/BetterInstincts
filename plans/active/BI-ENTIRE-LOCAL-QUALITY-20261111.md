# P141 opportunity selection — Entire-backed BetterInstincts local verification

**Parent mission:** stop depending on GitHub Actions for execution of repo quality checks; preserve actual operator/Windows safety, AI-session continuity, and separate Sims gameplay certification. Existing local owner is Moonwake `scripts/entire_host_cycle.cjs`, not a new BetterInstincts agent loop. Baseline: BetterInstincts `main` 11e21e4533e49c4481e23db64d3db44fe9c9ad4f; one workflow `.github/workflows/ci.yml` owns offline tests, source/peripheral gates, and ontology chronology.

## Competing routes (P141)

1. **Run workflow commands directly on operator Windows — REJECT:** arbitrary checkout Python and agent-modifiable test code could affect host peripherals, profile data, and mouse/keyboard. Existing Cursor project guard intentionally denies unsafe local shell.
2. **Rebuild a second agent/Entire orchestrator in BI — REJECT:** Moonwake already owns the durable agent execution/Entire checkpoint loop, retries, receipts, local state and locks. Duplicating it creates split authority.
3. **Replace GitHub Actions with another hosted CI — DEFER:** swaps providers, doesn't certify physical Windows input, and leaves network dependence.
4. **Entire-native hosting/Trails as sole quality engine — DEFER:** Entire session/checkpoint provenance and optional cloud evals are useful, but no currently verified on-host Entire primitive replaces all existing Python checks and physical evidence.
5. **SELECT: one local sandboxed quality gate for BI plus Moonwake's Entire continuity:** source-pinned artifact, all existing workflow commands in a versioned manifest, strict parity checker until migration complete, disposable no-network/no-privilege sandbox, private local receipts and read-only Entire CLI probe. Accepted local checks can run without GitHub Actions. Physical P08 stays an independent Windows operator/session proof.

## P95 call stack / ownership

`git status/HEAD -> manifest validation -> legacy workflow parity -> Entire capability/privacy probe -> committed Git archive -> isolated container -> all commands -> sanitized result receipts -> separate P08 host proof`.

- BI: `contracts/local-quality-checks.v1.json` exact acceptance, `scripts/local_quality.py` host quality gate and private receipts, `tests/test_local_quality.py` safety and parity falsifiers, `docs/LOCAL_QUALITY.md` usage.
- Moonwake: `scripts/entire_host_cycle.cjs` retains coding-agent feedback, bounded retries, session/checkpoint continuity; do not vendor or rewrite it in BI.
- CI: GitHub Actions left as temporary, independent comparator until full local Windows validation; **not** the chosen execution runtime.
- Prohibitions: no auto `entire enable`/login/configure/push, scheduler installation, host settings, Bluetooth/device touches, changes to saves, user prompts/transcripts in public repository, or agents running tests with ordinary desktop permissions.

## Gates and falsifiers

P82: missing Entire or upload privacy evidence denies; missing sandbox image denies without pull; dirty checkout denies; agent-edited/added CI command missing from pinned manifest denies; unsafe tar members and mutable git commands deny; allowed read-only plan works. No host game/PID/keyboard controller is introduced.

P08: local Docker/Podman + installed Entire probe, real safe checkpoints, actual 100% manifest checks and red→green repair loop by Moonwake; separate benign local cursor-hook allow/deny and optional physical game canary. Provider-backed GitHub checks are not Windows host certification.

P07: consult ontology **in an earlier commit** and implement bounded source/tests/contracts. P124: one manifest, no duplicate runner framework; versioned maintenance path and checkpoint semantics.

**Sunset trigger:** Disable/remove `.github/workflows/ci.yml` only after equivalent local host run on exact candidate SHA, independently reviewed full coverage and durable local receipts; protect policy even if GitHub Actions no longer runs. Never silently downgrade existing gates.

**Integration status:** P141 investigation completed; selected scope admitted for offline implementation. Runtime install and observed Windows proof remain separately open.
