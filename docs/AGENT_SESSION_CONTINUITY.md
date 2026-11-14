# Agent session continuity: a paused game is not a completed mission

**Owner:** BetterInstincts gameplay-specific interpretation of MoonWake's existing execution-boundary policy. This adds no new game controller, Codex stop hook, scheduler or host-effect authority.

## Incident and parent
The 2026-11-13 screenshot depicts Codex ending a gameplay turn after reporting about 13 minutes of play while The Sims 4 is paused. The operator explicitly authorized agent-led play, including unpausing when appropriate. That establishes gameplay intent, **not** current save identity, game focus, human inactivity, an effect permit, or BI-002 certification. An interim P08 block, a successful report, or elapsed time cannot close the parent.

## Decisions from a single explicit observation
- PREPARE_GAME_EFFECT_ADMISSION: observed paused Live Mode + verified disposable save + prior gameplay request + inactive player. Recheck current PID, scene, save, target, dual-idle probes and screen_admit for each separate game effect; this advisory never itself authorizes unpausing.
- OBSERVE_GAME: an eligible running game calls for a bounded passive outcome, motives and action-queue observation, not a blind replay.
- CONTINUE_OFFLINE: human activity, missing host or game/save uncertainty prevents screen effects but independent read-only work is available. Continue that work.
- REOBSERVE_HOST / INVESTIGATE_NEXT_GATE: no proven terminal gate exists; refresh safe observations, ability to use tools and next in-scope action.
- YIELD_TO_PLAYER: human active or unknown and no independent source work ready. Quiesce this turn safely, retain parent checkpoint and concrete resume trigger.
- BLOCKED_EXACT: protected save or independently evidenced inaccessible host with no ready independent work. Preserve active parent as blocked; do not claim success.
- COMPLETE_PROVEN: full original parent acceptance supported by nonempty real evidence references. A narrative report is not sufficient.

## Runner contract
The pure source is betterinstincts/agent_session_continuity.py. Its machine shape is contracts/agent-session-continuity.v1.json; regression suite is tests/test_agent_session_continuity.py. On an approved isolated runner with an explicit real JSON snapshot in the ignored dist tree:

    python -m betterinstincts.agent_session_continuity --input dist/game-host/session-continuity.json

Exit 20 means nonterminal; exit 2 means invalid evidence; exit 0 means either actual completion **or safe quiescence**. Inspect the returned decision and parent_complete: the exit code alone is not proof of mission completion. This CLI never clicks, unpauses, saves, changes OS settings, writes a checkpoint or launches an agent. Do not bypass existing Cursor shell/project safety guards to execute agent-edited Python on the operator desktop; run tests in an approved isolated runner or CI.

## Required local agent behavior
1. Recover the latest fixed operator parent, current in-game scene/household and active branches, then read AGENTS.md, the mandatory operating, ontology, doctrine, ledger and prompt documents, BI-002, and existing game-host guidance.
2. Preserve MoonWake Sixth Gear's exact P141 -> P95 -> P82 -> P08 -> P07 -> P124 contracts. P141 is in scope; its STOP is stage-local. If local P08 cannot lawfully execute, continue independent P07/P124 engineering; never call a remote GitHub provider a game host.
3. Treat PAUSED as a state of The Sims 4, not an end of the agent's job. Verify actual local save, scene, player inactivity, control permits and safe effect scope; only then perform one reversible authorized effect and independently observe the result.
4. Protect existing Sims saves and user control; do not fabricate device/game version, game effects, automation installation, six-stage execution or independent agents. Do not turn a protected save into a disposable save based on the appearance of the screen.
5. After each outcome, re-evaluate six needs, Sim queue, player-directed tasks and active goals; preserve interrupted goal state. Maintain BI-002 as ACTIVE until five vanilla and five modified hunger trials, patch identity, rollback and player queue safety are genuinely witnessed.
6. Before proposed termination, classify the next progress-bearing transition using the existing MoonWake execution_continuity policy and this gameplay-specific triage. Close only with actual acceptance or exact evidenced terminal/quiescence gate and resumption trigger.

## Proof ceiling
GitHub source, consultation and offline tests do not demonstrate a live Codex pre-stop hook, an authenticated local agent, current save identity, Sims gameplay effects or merge. Maintain CHANGED | PROVED | NEXT separately and attach actual checks, hashes and patch-specific local evidence.
