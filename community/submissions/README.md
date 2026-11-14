# Manually reviewed portable training evidence

Only opt-in, sanitized, data-only semantic-case JSON bundles proposed in pull requests belong here. Do not commit local `reviewed-examples` input files, original observation refs, names, screenshots, game saves, model weights, EA files, profiles or secret data.

Create a bounded bundle with `python -m scripts.community_cases export --reviewed-examples PRIVATE.json --out NEW_PRIVATE.json --ack-share-reviewed-cases`, inspect the output yourself and submit only the sanitized bundle after a deliberate sharing decision.

`python -m scripts.community_cases audit-repo` validates schema, field allowlists, integrity digests, size and replay bounds. A successful audit is **not** consent/provenance attestation, a privacy guarantee, acceptance into training, developer approval or Sims gameplay certification. Maintainers review proposed submissions and separately control adoption.
