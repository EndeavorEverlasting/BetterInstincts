# Community learning and developer contribution pathway

Status: offline, opt-in contribution-candidate prototype. No network/federated training, developer credential grants, automatic PR, model adoption, or native Sims effect. BI-002 hunger certification stays active.

## Product objective and existing owner

A player can improve a **private local** model using separately admitted Sims observations. A contributor can then voluntarily propose a reproducible generalized improvement for review. It must work beyond their own Sim, household, save, machine, lot, game build and mods.

Existing training belongs to betterinstincts/semantic_vae.py; the local model intentionally remains world/context scoped. scripts/community_candidate.py is an export and review-only tool, **not another trainer**. It strips the world/save hash, installation profile, replay Bloom, sample IDs, private semantic vectors and names. It exports only fixed-shape numeric encoder/decoder weights, a transport digest and **untrusted self-reported aggregate metrics**.

**Important: model weights can still encode and reveal information about training data.** Export requires a separate explicit share-weights acknowledgement; before voluntary publication, the contributor should inspect the content and obtain a privacy/licensing review. There is no implicit contribution consent from enabling local training.

## Participation

- **Player:** gameplay and optional local learning; no default capture, network, or upload.
- **Contributor:** proposes a reviewed model, source change or test via GitHub. May submit without privileged repository access.
- **Approved developer:** explicitly approved by maintainers for a stated engineering scope; contributes reproducible tests and source, not unreviewed runtime changes.
- **Maintainer:** checks privacy, source rights, integrity, security, independently attested holdouts, player-control regressions, compatibility, releases and rollback. Only a maintainer may authorize developer privileges or production adoption.

Application for developer candidacy: open a GitHub issue with the proposed contribution domain, source provenance, prior work, license/rights, reproducibility method, negative tests and proposed independent-host validation. No training score automatically grants developer status. All unreviewed submissions are untrusted.

## Explicit local workflow

Local training is off by default. Enable only for the chosen existing installation profile:

    python -m scripts.semantic_vae status
    python -m scripts.semantic_vae enable --ack-local-data
    python -m scripts.semantic_vae train --snapshot VERIFIED_S.json --event VERIFIED_E.json --patch VERIFIED_P.json

The input files must be independently sourced and admitted as required by the original VAE. This CLI does not start a game observer. Then make a **separate** decision to export weights into a user-selected new local file (not the Git checkout):

    python -m scripts.community_candidate export --snapshot VERIFIED_S.json --out PRIVATE_CANDIDATE.json --ack-share-weights
    python -m scripts.community_candidate validate --candidate PRIVATE_CANDIDATE.json

For a named preexisting installation profile add --profile EXISTING_PROFILE to the export command. Export requires minimum 24 trained examples, 8 holdouts, and self-reported loss at least 0.01 nats better than a uniform baseline, solely to screen obviously unready candidates. These metrics are not independently authenticated.

Nothing automatically uploads, creates a PR, downloads an external candidate, modifies user saves, or imports contributed weights into a live game.

## Bounded JSON submission and research-only benchmarking

Schema: betterinstincts.community-learning.candidate/v1, algorithm SEMANTIC_VAE_5X5X3_V1, 75 binary channels, four latents. A strict JSON parser rejects duplicate keys, unknown fields, shape mismatches, nonfinite or out-of-range weights, oversized files, malformed metrics and altered tensor digests. No executable code, Python pickle, model operator graph, script hooks or opaque model binaries can enter this interface.

Reviewers may prepare two distinct, independently observed, privacy-reviewed holdout files. Each is a JSON object with exactly two fields: schema equal to betterinstincts.community-learning.holdout/v1, and vectors containing 8 to 64 arrays of **exactly 75 binary integers**. Use the established WALKABLE, BLOCKED, TARGET channel order, no names or raw screenshots.

    python -m scripts.community_candidate benchmark --candidate PRIVATE_CANDIDATE.json --holdout-a REVIEWED_A.json --holdout-b REVIEWED_B.json
    python -m unittest tests.test_community_candidate -v

The fixed VAE decoder is evaluated without training or side effects on both cohorts. The CLI rejects identical cohorts and reports per-cohort reconstruction improvement against a uniform-Bernoulli baseline. This is only a research screen; the CLI **cannot authenticate** that cohorts came from different real hosts or were not cherry-picked. A research PASS is not a malicious-model clearance, developer approval, proof of better gameplay, or production release.

## Promotion: generalize before integrating

Before upstream model adoption, maintainers must:

1. Independently verify provenance, legal rights, explicit share consent, no proprietary EA files or personal data, and susceptibility to model inversion.
2. Reproduce evaluation using trusted holdouts on at least **two distinct authorized host installations** and multiple source contexts per host; vary world/household, game version, packs and configuration where applicable. Require more evidence where impact or risk justifies it.
3. Run red-team/poisoning, trigger/backdoor, distribution-shift, novel-object, false-wall and hostile-model tests. Merely satisfying numeric bounds is insufficient. No automated validator can prove total absence of maliciousness.
4. Compare the existing approved reference and a simple baseline on independent examples; avoid per-cohort regressions. Evaluate true route/object utility, scene safety, false-positive graph edges, player interruptions, model latency, RAM and CPU, as well as reconstruction loss.
5. Require a code-reviewed, versioned reference artifact or generalized training improvement, separate compatibility matrix, documented rollback, and maintainer-approved release. Never automatically distribute a personal delta as the shared model.

**Generalization does not mean a single checkpoint forced onto every PC.** Shared transferable features, schema, training protocol, reference weights and evaluation fixtures can coexist with private per-installation adaptation. Private local weights remain isolated. Cross-user aggregation or federated training needs new consent, privacy, security and governance design and is not shipped here.

## Proof and safety ceiling

- LOCAL_CANDIDATE_EXPORTED_NOT_UPLOADED: a file produced on a consenting host, not a submission.
- STRUCTURAL_PASS_INDEPENDENT_REVIEW_REQUIRED: strictly formatted finite data, not safe or useful certification.
- RESEARCH_BENCHMARK_PASS_HUMAN_REVIEW_REQUIRED: two supplied datasets showed offline improvement, source independence unproven.
- ADOPTED: only a separate actual maintainer integration and release record can demonstrate adoption; this tool never produces that state.

All candidates have zero gameplay/OS effect authority. No model can create verified passages, override explicit player commands, select protected saves, cancel a queue, alter settings or close BI-002. Owners: contracts/community-learning.v1.json, contracts/semantic-vae.v1.json, docs/SEMANTIC_VAE.md, docs/VALIDATION.md, docs/NATIVE_GAMEPLAY_ARCHITECTURE.md.
