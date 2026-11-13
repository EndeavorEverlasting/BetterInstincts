# P97 — open-source prior art and gap analysis (2026-10-20)

**Capability:** smarter Sims 4 autonomy without invasive runtime replacements. **Local baseline:** repository initially contained only README/license/gitignore. The offline scorer is new and has no live integration.

## Bounded reference matrix
| Source | Implementation evidence | Classification | Disposition |
| --- | --- | --- | --- |
| [Lot 51 Core Library](https://github.com/lot51/core-library) (inspected main at f12c1b1bcfb4d0de37bead0f7235eaa840774ff7; MIT) | [services/events.py](https://github.com/lot51/core-library/blob/main/services/events.py) defines CoreEvent and EventService; README details shared event handlers, bounded dependency use and version checks. | OBSERVED_IMPLEMENTED (event API), DOCUMENTED_UNVERIFIED (player compatibility) | ADAPT event-driven hooks only if a script is needed. Do not bundle the core library. |
| [Sims 4 Community Library](https://github.com/DeviantGameMods/Sims4CommunityLibrary) (inspected main at db1ca99dc448589d4cb1ab315cf4a3bb26c115be) | [common_event_handler.py](https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Scripts/sims4communitylib/events/event_handling/common_event_handler.py), [console commands](https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Scripts/sims4communitylib/services/commands/common_console_command.py), and [modding walkthrough](https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Documents/GettingStartedModdingForSims4.md) show Python APIs and Sims 4 Studio tuning workflow. Example source carries CC BY 4.0 notice; license must be examined before copying code. | OBSERVED_IMPLEMENTED (API structures), DOCUMENTED_UNVERIFIED (target build compatibility) | ADOPT documentation workflow; ADAPT/UNKNOWN dependency, no copied code. |
| [XML Injector](https://scumbumbomods.com/xml-injector) | Maintainer documentation: snippets can add interactions without bespoke Python script, explicit game patch and test-package process. [CurseForge listing](https://www.curseforge.com/sims4/mods/xml-injector) shows project distribution, not source audit. | DOCUMENTED_UNVERIFIED (behavior) | ADAPT for interaction addition if needed; it is NOT a generic autonomy optimizer. Never bundle dependency. |
| [Smarter Self-Care](https://www.curseforge.com/sims4/mods/smarter-self-care) | Public distribution lists need-specific optional `.package` modules and pack compatibility notes; proprietary implementation not inspected. | DOCUMENTED_UNVERIFIED | ADOPT modular packaging/compatibility disclosure. REJECT duplication of features as product novelty. |
| [Better Sleep Autonomy](https://modthesims.info/d/663675) | Public description lists modular scheduling behavior factoring in traits/moods and explicit expansion requirements. Internal code uninspected. | DOCUMENTED_UNVERIFIED | ADAPT character-sensitive behavior later; no code reuse. |
| [Deeper Social Autonomy](https://www.curseforge.com/sims4/mods/deeper-social-autonomy) | Distribution describes trait/mood/relationship-responsive choices and game-version list. Code uninspected. | DOCUMENTED_UNVERIFIED | ADAPT personality-respecting priorities; defer overlap until verified. |
| [Sims 4 Studio workflow](https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Documents/GitHub/GettingStarted.txt) | Tutorial shows extraction of vanilla tuning to `.package` and editing XML; must verify current GUI/runtime in local game. | DOCUMENTED UNVERIFIED for current patch | ADOPT as first local lab workflow. |

## P97 supplement: multiversion mod support (2026-10-20)
| Source | Verifiable precedent | Adopt/adapt/reject |
| --- | --- | --- |
| [Lot51 Core](https://github.com/lot51/core-library/blob/main/README.md) and [Core 1.37 backward compatibility release](https://lot51.cc/mods/core-library/releases/1.37) | Project documents semantic mod versions, minimum library versions, and an actual fix for compatibility regression affecting older Sims patches. DOCUMENTED + dated release evidence, not verified locally. | ADOPT explicit version support/dependency floors; ADAPT to full game build + platform; do not bundle third-party core by default. |
| [Modders Reference XML comparisons](https://thesims4moddersreference.org/tutorials/creating-xml-compare/) | Describes per-game-patch tuning extraction and diffing without mixing earlier copies. DOCUMENTED workflow. | ADOPT local patch-specific diff and preserve old authored profiles; REJECT committing raw EA extracted files. |
| [Oops19 Patch XML](https://github.com/Oops19/TS4-PatchXML) | Maintainer documents version-scoped caches and independently owned config, including patch application failures. DOCUMENTED source. | ADAPT version-scoped config; REJECT unproven automatic XPath patch dependency. |
| [S4CL](https://github.com/DeviantGameMods/Sims4CommunityLibrary) | Documents minimum supported game patch rather than claiming any future game build works. DOCUMENTED. | ADOPT explicit release compatibility limits; UNKNOWN runtime applicability to hunger. |

**Solved internally now:** offline decision-policy and exact-version catalog/CI retention mechanism. **Available to emulate:** patch XML diffs, compatibility listings, semantic dependency version bounds. **Project-specific missing:** actual patch-specific package and reproducible game A/B observations. **Evidence gap:** actual tested versions, tuning entry IDs, mod conflicts and local game hooks. None may be substituted with offline fixtures.

## Solved vs gap map
- **AVAILABLE TO EMULATE EXTERNALLY:** per-need tuning modules, compatibility labeling, targeted game tuning workflow, common Python event APIs.
- **PROJECT-SPECIFIC GAP:** unified *configurable* model balancing urgent needs, income, career, traits, leisure, and player intentions, **without** duplicate or invasive autonomy loops.
- **EVIDENCE GAP:** target game patch, concrete hunger tuning entries, whether tuning alone can meet the first behavior acceptance criteria, interaction with MCCC/Smarter Self-Care, stable in-game metrics.
- **ALREADY SOLVED INTERNALLY:** none at project inception; offline decision-policy tests are now an experimental baseline, not a mod.

## Prioritized development gap
**Hunger autonomy only.** Extract specific current vanilla tuning; record resource IDs, scoring knobs, pack requirement, competing overrides, and observed baseline; use the smallest reversible change, then compare game saves and performance. Only add scripts if this mechanism is insufficient. Reject global simulation-tick loops and replacement of the entire autonomy engine.

## External boundaries
EA's [mod policy](https://help.ea.com/en/articles/the-sims/the-sims-4/mods-policy/) requires independently branded, free mods; optional donations/early access have restrictions. Marketplace Maker Program does not replace the separate free-mod policy. Credits, licenses, and runtime dependencies remain explicit. Avoid copying CC-by-licensed examples into MIT source without appropriate compliance.

## 2026-11-07 — P97 reviewed-player judgment learning

New requirement: learn operator-reviewed good gameplay opportunities in context and return *advisory* patterns, rather than assume a click is optimal. The existing `host_listener` already captures sanitized evaluations; its absence of safe learned recommendations is the project-specific gap. **Sources inspected at code level:** [Lot51 `services/events.py` @ f12c1b1](https://github.com/lot51/core-library/blob/f12c1b1bcfb4d0de37bead0f7235eaa840774ff7/services/events.py) (MIT; event callback registration — ADAPT only when genuine Sims hook is needed), [River `river/compose/pipeline.py` and progressive validation @ 4768de0](https://github.com/online-ml/river/blob/4768de0579f977315e65cd23ee658534c1d62c26/river/evaluate/progressive_validation.py) (BSD-3-Clause; predict-before-learn — ADOPT evaluation principle, no dependency), [hmmlearn `src/hmmlearn/base.py` @ e01a10e](https://github.com/hmmlearn/hmmlearn/blob/e01a10e99df1042e4c1e6b7c822fd292dd37502f/src/hmmlearn/base.py) (BSD-3-Clause; hidden-state model — DEFER until sufficient labels), and XML Injector distribution (DOCUMENTED_UNVERIFIED for learner; UNKNOWN). No external source code copied.

**Solved internally:** opt-in listener, player presence, host/scene safety and evaluator contracts. **Externally available:** incremental learning / prequential evaluation. **Selected local seam:** approved semantic demonstrations → bounded contextual first-order transition counts → conservative explainable advisory `learning_hint` on an existing opt-in listener tick, never screen actuation. **EVIDENCE_GAP:** genuine reviewed game examples and live positive effect. Full implementation evidence and decisions in [JUDGMENT_LEARNING.md](JUDGMENT_LEARNING.md).

## 2026-11-08 — P97 camera-safe traverse + visual observation

**Operator problem:** agents edge-scroll the Sims map/lot to gather data, then leave the mouse on the screen edge while coding so the camera keeps panning.

| Source | Implementation evidence | Classification | Disposition |
| --- | --- | --- | --- |
| Local sibling Automation `docs/VISUAL_INTELLIGENCE_STACK.md` | Observe≠act seam; normalized observation receipt; consumer owns actuation; OCR/OmniParser/VLM are interchangeable engines behind one API | OBSERVED_DOCUMENTED (local sibling repo) | **ADAPT** observe≠act + consumer authorization; **REJECT** cloning donor engines/weights into BetterInstincts |
| Local sibling TokenCorridor `docs/program/visual-intelligence-incubation-2026-10-11.md` | Deterministic pixel/DOM/OCR before optional VLM; screenshots untrusted; action authority separate | OBSERVED_DOCUMENTED | **ADAPT** escalation order (PrintWindow/luma before any CV escalation) |
| BetterInstincts `scripts/game_capture.py` + `viewport.py` | PrintWindow client bitmap without desktop screenshots; black-viewport ladder already uses interior right-drag/wheel | OBSERVED_IMPLEMENTED | **ADOPT** as primary see-without-edge-pan sensor |
| Microsoft OmniParser / PaddleOCR / Qwen3-VL source trees | Upstream catalogued by Automation; licenses and weights vary | DOCUMENTED_UNVERIFIED for BI | **REJECT** vendoring into this sprint; escalate only via Automation consumer bridge later if measured |

**Solved internally now:** `CAMERA_SAFE_TRAVERSE` contract, edge-band classification, capture-first plans that terminate at `SAFE_CURSOR_REST`, host_stack gate, admitted CLI. **Project-specific gap:** live disposable proof that SAFE_REST stops camera drift on the operator's resolution/DPI. **Evidence gap:** exact edge-band width per lab monitor; WASD/arrow camera mode availability. Details: [CAMERA_TRAVERSE.md](CAMERA_TRAVERSE.md).

## 2026-11-11 — P97 peripheral-safe agent execution: bounded prior-art inspection

**Local capability and baseline:** BetterInstincts already has a project-specific deny-by-default Cursor pre-effect hook, a peripheral-authority contract, and a static source checker. The narrow remaining gap was executable coverage outside the original `scripts/` and `betterinstincts/` trees, a precise unnamed-BLE-mouse identity model, and explicit separation of source checks from activated runtime enforcement. The parent need is *not* a Windows repair program inside Sims.

| Reference (inspected 2026-11-11) | Implementation evidence and confidence | Adopt/adapt/reject |
| --- | --- | --- |
| [Cline CLI approval implementation](https://github.com/cline/cline/blob/main/apps/cli/src/utils/approval.ts) and [CLI approval docs](https://github.com/cline/cline/blob/main/apps/cli/README.md) | `requestTerminalToolApproval` rejects non-TTY approval-required actions; desktop IPC unavailable returns `approved:false`. **OBSERVED_IMPLEMENTED** in published source; local host behavior **NOT TESTED**. | **ADAPT** tool-class deny-by-default, no unattended approval fallback. Do not require Cline dependency. |
| [PyAutoGUI failsafe implementation](https://github.com/asweigart/pyautogui/blob/master/pyautogui/__init__.py) and [failsafe documentation](https://pyautogui.readthedocs.io/en/latest/index.html#fail-safes) | Source exposes `FailSafeException`; docs state mouse-to-corner abort and default on. **OBSERVED_IMPLEMENTED** source feature, **DOCUMENTED_UNVERIFIED** on current Windows host. | **ADOPT** the rule not to disable existing safety interrupts; deny `pyautogui.FAILSAFE = False` in executable game/agent code. No code copied. |
| [Open Interpreter sandbox and approval contract](https://github.com/openinterpreter/openinterpreter/blob/main/docs/sandbox.md) | Explicit separate `sandbox_mode` and `approval_policy` controls, including warning that bypass flags remove both. **DOCUMENTED_UNVERIFIED** runtime. | **ADAPT** independent host permission boundary; a checked-in hook is not an OS sandbox. No code copied. |
| [GitHub Copilot hook reference](https://docs.github.com/en/copilot/reference/hooks-reference) | Provider documents per-tool preToolUse deny and that timeouts can proceed through normal permission path. **DOCUMENTED_UNVERIFIED** for user's Cursor host; not presented as a code implementation. | **ADAPT** activation/timeout failure-mode checks; **REJECT** static-hook-presence as proof of universal interception. |

**Available in real systems:** user-controlled tool approvals, explicit bounded sandboxes and local automation abort channels. **Already available in BetterInstincts:** effect-admission ontology, human presence gates, project Cursor hook, Windows repair delegation to SysAdminSuite, CI scanner and baseline tests. **Project-specific gap addressed here:** cross-path executable scanning, BLE early-name/appearance evidentiary semantics, and negative regression fixtures.

**Rejected alternatives:** (1) another Windows Bluetooth service guard in the Sims process; (2) “Mouse” label auto-pairing; (3) disabling Bluetooth, Print Screen, Escape/U, or PyAutoGUI failsafes to recover captures; (4) a new desktop daemon or generalized pointer logger; (5) treating GitHub CI or a configured Cursor hook as a privileged host sandbox. These would violate user ownership or misstate evidence.

**License/dependency boundary:** none of the cited third-party source is copied or bundled. Individual versions, licenses and release identities should be pinned **before** any future direct incorporation; this sprint uses patterns and independently authored checker code only. An open-source README or documentation claim alone is not local runtime proof.

**Selected integration:** P00 rev9 concepts + P01 extension to the *existing* source checker/contract + P82 hostile fixtures + P07 existing CI and reviewed PR + P124 single-owner consolidation. P08 physical host tests, real activated Cursor hook, SysAdminSuite recurrence trace and M343 diagnosis remain independent, unperformed host gates.


## 2026-11-12 — P97 natural SLAM reassessment mechanics (source review)

**Question:** make existing BetterInstincts camera survey predictable, useful, lower-motion and physically smoother without creating an unapproved desktop watcher. Local owner: `betterinstincts/observation_sweep.py` (prior revision used cubic easing, only the immediately previous view as history and two untyped evidence refs).

| Reference | Directly inspected implementation/research | Disposition |
| --- | --- | --- |
| [ROS Navigation2 simple_smoother.cpp](https://github.com/ros-navigation/navigation2/blob/main/nav2_smoother/src/simple_smoother.cpp) | **OBSERVED_IMPLEMENTED**: bounded iterations and max-time abort, directional segments, retain last feasible path on invalid cost; source Apache-2.0 header. Nav2's environment and costmap differ from Sims, so no package or source copied. | **ADAPT** bound computation, reject unsafe routes, retain previous usable state and do not force a movement. |
| [Macfarlane & Croft, jerk-bounded robotics trajectory planning](https://doi.org/10.1109/TRA.2002.807548) | **DOCUMENTED_RESEARCH**: fifth-order polynomials for low-jerk trajectories. Not a runnable Sims adapter; no source copied. | **ADAPT** independently implement quintic ease for continuous candidate waypoints. |
| [Active Visual Perception: Opportunities and Challenges](https://pmc.ncbi.nlm.nih.gov/articles/PMC13708967/) | **DOCUMENTED_RESEARCH**: information-gain versus movement cost, uncertainty, observation feedback and real-world feasibility constraints; not direct BetterInstincts code. | **ADAPT** reject non-novel moves, block when post-motion evidence is pending, remember recent viewpoints. |
| [WPILib license / trajectory ecosystem](https://github.com/wpilibsuite/allwpilib) | **LICENSE INSPECTED**, trajectory code not independently confirmed in this pass. | **UNKNOWN** direct mechanism; no code dependency or adoption. |

**Gap map:** existing room/semantic map and camera planning = **ALREADY_SOLVED_INTERNALLY**; bounded, source-aware feedback and jitter avoidance = **AVAILABLE_TO_EMULATE_EXTERNALLY**; Sims-native input and exact-build sensor admission = **PROJECT_SPECIFIC_GAP / P08**; actual EA lot geometry extraction = **EVIDENCE_GAP**. P141 compared (1) invisible OS watcher, **REJECT**; (2) new dense SLAM engine, **REJECT**; (3) quintic motion alone, **INSUFFICIENT**; (4) single existing planner with explicit motion-proposal opt-in, independently classed evidence, post-motion lock and recent-view memory, **SELECT**. No hidden daemon, camera input, recordings or EA binary hooks introduced. P95/P82/P08/P07/P124 verify this candidate under the strict proof ceiling: offline pure-function tests only until local game authority.
