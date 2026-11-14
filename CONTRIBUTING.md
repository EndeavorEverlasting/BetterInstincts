# Contributing to BetterInstincts

Thanks for helping make The Sims 4 autonomy smarter and more enjoyable for everyone.

## Propose an improvement

Contribute through reviewed GitHub issues and pull requests. Read AGENTS.md, docs/DOCTRINE.md, docs/VALIDATION.md and the existing domain owner before changing gameplay logic. Follow the ontology consultation, native-gameplay route and regression-harness requirements. Offline pass does not imply game certification.

## Community learning and developer candidacy

You may use **opt-in local training** to improve your own model without ever sharing information. See docs/COMMUNITY_LEARNING.md to make a separately consented, inert JSON learning candidate, validate it, and prepare independently reproducible evidence.

To become an approved developer, propose your intended contribution domain and scope in a GitHub issue. Include your relevant work, source provenance and legal rights, reproduction and test plan, negative cases, privacy/security treatment, and how the improvement generalizes to **other** hosts, households, game builds and player preferences. Maintainers explicitly decide developer candidacy and repository permissions. Nobody needs privileged write access just to propose a contribution.

## Privacy and security

Never submit Sims saves, household/Sim names, personal OS data, raw screenshots, tokens, unconsented weights, unlicensed EA assets, executable model payloads or hidden harvested observations. A candidate validator is not a security clearance. Review must include independent cross-host holdouts, poisoning/backdoor and privacy analysis, compatibility and rollback. Contributions are untrusted until explicitly accepted; no candidate grants game/OS effect authority or automatically ships to players.

## Portable reviewed training cases

For a contribution that does not reveal a trained weight tensor, use the opt-in semantic case exporter described in docs/COMMUNITY_LEARNING.md. It converts already reviewed local judgment examples into a strict allowlisted JSON bundle. It drops all source observation identifiers and does not send data anywhere. Review the exported bundle before proposing a PR; never commit the source examples.

Proposed data-only bundles belong under community/submissions/ as individually reviewed files. CI checks schema/digest/replay integrity only. A passing audit neither proves cross-host effectiveness nor approves model adoption; maintainers independently review rights, privacy, harmful outcomes, conflicting labels and holdouts. You can contribute via a fork and pull request; a GitHub collaborator invitation is a separate human decision.
