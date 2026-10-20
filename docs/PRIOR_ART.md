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
