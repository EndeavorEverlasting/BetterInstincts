# P04 canonical handoff — BI-SCENE-MAP / BetterInstincts game host

**Canonical owner:** [BetterInstincts](https://github.com/EndeavorEverlasting/BetterInstincts), `main`. Read in this order: `AGENTS.md` → `docs/DOCTRINE.md` → `docs/LEDGER.md` → `docs/SCENE_INTELLIGENCE.md` → `docs/GAME_HOST.md` → `docs/LIVE_CERT.md` → `plans/active/BI-002.execution.v1.json` → `plans/active/BI-SCENE-MAP.md` → this handoff and `BI-SCENE-MAP.dispatch.v1.json`. This is the **single BI-SCENE-MAP handoff**, not a substitute for the older BI-GAME-HOST and BI-MODLAB handoffs.

## CHANGED | PROVED | NEXT

**CHANGED:** P00/P01/P95 and Trifecta (P08 → P82 → P07) applied to the existing game-host repository. [PR #15](https://github.com/EndeavorEverlasting/BetterInstincts/pull/15) merged at `709646ce11cc1ee1fb80848f66c9130230b3721f`, from PR head `aed48729072aa3a96a9d73dde8dc6bbcca15d4da`. Implemented 35 exact-version scene candidates in `contracts/game-scenes.v1.json`, a dual-source cue classifier and manual-only transition planner; typed save classes and private identity-binding guard; a chosen-save UI click interlock in `scripts/game_host.py`; scene/save CLI probes, test fixtures, root governance and explicit CI contract guard. No user-facing UI, game mod, save scanner, or in-game hook shipped.

**PROVED:** [PR-head CI #42373216350](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42373216350) SUCCESS with 139 offline tests, doctrine, graph/save contract, horizon, prior-version immutability, asset leakage, whitespace and compile checks. [Post-merge CI #42373287837](https://github.com/EndeavorEverlasting/BetterInstincts/actions/runs/42373287837) SUCCESS on `709646ce`. The initial genuine Windows Sims process and CAS were observed earlier under [PR #13](https://github.com/EndeavorEverlasting/BetterInstincts/pull/13), exact menu patch `1.121.361.1020` DX11. **No** Live Mode capture, genuine hunger baseline, calibrated scene classifier, actual save origin proof, full scene census or game version certification was observed by this cloud runtime. Catalog `CANDIDATE_UNVERIFIED` is not screen proof; local save registry `OPERATOR_ATTESTED_SELECTION_ONLY` is not save-file forensics.

**NEXT:** LOCAL_AGENT_RUNTIME on the actual Windows game host must first finish CAS → disposable household → lot → Live Mode, verify the real capture and run the existing BI-002 game-host confirmation/baseline commands. In parallel only where actual workers exist, begin a *read-only* exact-patch scene calibration ledger. Do not divert the parent hunger trial into making polished screenshot templates for every DLC overlay. Sims 4 Studio remains unobserved and is **not** necessary for five vanilla hunger baselines; it is necessary before modified-package tuning evidence.

## LAUNCH ORDER — real local agent, no phantom parallel workers

1. Re-enter the **existing** canonical BetterInstincts checkout. `git fetch --all --prune`, `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, inspect current open PRs and local worktrees. Preserve uncommitted work. This ChatGPT runtime has GitHub-provider access, **not** the user's actual Windows desktop, game process or personal file system; do not assume old process PID 15152 remains alive.
2. Run `python -m scripts.check_scene_contract`, `python -m unittest discover -s tests -v`, `python -m scripts.check_horizon`, `python scripts/validate_doctrine.py`. Confirm unchanged pre-existing game-host and BI-002 contracts. Do not upload raw private manifests or game screenshots to public GitHub.
3. Inspect the real Sims UI and focus. Previously observed `bi002-first-boot` stopped at **CAS story quiz** after the New Game click; the screen may have changed. Manual operator may need to choose **No thanks!**, make a disposable adult Sim, place it on an empty lot and enter Live Mode. Never press Resume or browse user saves on the agent's behalf. Do not replay the prior New Game click against an unknown screen.
4. For each scene actually visible, record local private screenshots/capture refs and exact patch, resolution, graphics/display mode, language, world/DLC variant, overlay/focus status, and two **independent authentic cues**. Store bounded evidence only under ignored repo `dist/`. Build real cue adapters *later*: current tokens such as `cas:story_quiz` are **semantic placeholders** and must not be claimed as image recognizers. Maintain `UNKNOWN` whenever two scenes match or the patch is uncalibrated. Observe main menu → CAS → world → neighborhood → lot → Live Mode before broad Gallery/Library exploration; add new scene variants incrementally and compare prior accepted evidence.
5. Save protection: before navigating **Load Game** or selecting a chosen slot, classify owner/source. Any user-created, unknown, colliding, stale or unregistered slot is `USER_PROTECTED`/`UNKNOWN_PROTECTED`. Lab naming `BI_TMP_` (disposable) or `BI_CONT_` (continuation) is only a hint. Require a *separate private, uniquely bound* origin manifest with an actual lab-creation run ID, exact save ID, current authorized run ID, patch, current capture and explicit operator attestation. The existing chosen-save navigation rejects absent/mismatched manifests **before any click**. No automated Delete, Overwrite, Resume, game-save scanning or file alteration even for disposable.
6. Only after the intended newly created disposable household is visibly in Live Mode and a real screenshot ref exists, run:

   ```powershell
   python -m scripts.game_host status --run-id bi002-first-boot
   python -m scripts.game_host confirm --run-id bi002-first-boot --disposable-confirmed --game-version 1.121.361.1020 --capture-ref capture:live-mode-001
   python -m scripts.game_baseline --run-id bi002-first-boot
   python -m scripts.live_cert status --run-id bi002-first-boot
   ```

   **Do not** reuse the example capture ref until the local agent has actually captured it. If the original session is no longer valid, follow `docs/GAME_HOST.md` to create a new bounded session; preserve first-boot evidence rather than rewriting its receipts.
7. Record at least **five real vanilla hunger trials**, each with measured seconds-to-eat, minimum hunger, lag, player interruptions, loops, exceptions and a real observation ref using `python -m scripts.live_cert record --stage baseline --trial N ...`. Keep `Sims4Studio=NOT_OBSERVED` until independently inspected. Then inspect actual tuning, create one reversible package under ignored `dist/`, run five modified trials plus rollback and independent maintainer review. Keep BI-002 ACTIVE until that full proof chain finishes.

## P95 design and executable stack proof

- **Success (offline):** `scene_map CLI → load_catalog → validate exact patch → classify independent cues → transition proposal → MANUAL_ONLY`. Evidence is CLI/synthetic, not a screenshot or click.
- **Failure (offline):** ambiguous/one-cue/unknown patch → `AMBIGUOUS_OR_UNKNOWN` or `UNKNOWN_PATCH`, scene `unknown`, transition blocked.
- **Save success (synthetic only):** `chosen navigate → private save_registry → lab-only exact identity, version, run and capture → GUI click and click-level receipt`; still not live game verification.
- **Save failure (synthetic):** same selected ID with user-origin, naming spoof, stale capture, version drift, missing record or duplicate → `SAVE_SELECTION_PROTECTED` with **zero GUI clicks**.
- **Alternatives rejected for now:** blind coordinate clicks (focus drift seen in CAS); flat filename→scene click map (no ownership/ambiguity); whole-game UI recognition before one real gameplay baseline (goal drift). Typed scene graph + save policy is the selected seam.

## Runtime partition / P04 disposition

| Lane | HOST | Status / ceiling |
| --- | --- | --- |
| P00 governance + P01 harness + P95 thin program | CURRENT_CHAT_RUNTIME, GitHub provider | MERGED; contract and tests read back |
| P07 repo integration, P82 falsifiers | CURRENT_CHAT_RUNTIME / CI_OR_REMOTE_RUNNER | PR #15 and post-merge CI PASS |
| P08 gameplay and scene captures | LOCAL_AGENT_RUNTIME (Windows game host) | CAS previously observed; Live Mode UNPROVEN |
| Save ownership decision / user input | OPERATOR_OR_PHYSICAL_RUNTIME | Human review required; no automatic personal-save selection |
| BI-002 hunger trials and tuning | LOCAL_AGENT_RUNTIME with operator | 0/5 vanilla, 0/5 modified, rollback NOT OBSERVED |
| P04 handoff continuation | CURRENT_CHAT_RUNTIME → LOCAL_AGENT_RUNTIME | Tracked handoff/typed dispatcher; provider URL is not local execution |

No actual local parallel agents launched in this chat. Keep scene catalog and patch evidence append-only where certification is involved; never silently upgrade to latest. Older compatibility catalog remains intact. Source IDs from design discussion (`impeccable`, `UP-60B0939CC`, `UP-60FBA76B5`, `UP-F8DA7EE77`) remain pointers only; no UI shipped.

## Explicit first local command

`python -m scripts.check_scene_contract`

Run from the existing BetterInstincts checkout after the safe git-status preflight. Continue with the actual CAS → disposable Live Mode gate rather than declaring the live sprint complete because the scene catalog and handoff exist.
