# Maintainer acceptance boundary

CODEOWNERS routes PR review to @EndeavorEverlasting for the high-risk files, but **does not enforce approval without a protected main branch / matching ruleset**. Turn on Require a pull request + Require review from Code Owners + required successful CI in GitHub repository settings if permitted by the account plan. Do not claim these protections are active until queried/proven in GitHub provider truth.

Never certify compatibility by editing JSON based only on generated screenshots, AI summaries, synthetic CI results or a numerical PASS. Reviewer must independently inspect the actual package, original local game version/platform, tuning resource/hash, recorded gameplay capture and rollback, independent patch behavior, package checksum, and older build preservation. Acceptance file must include the reviewed profile ID, game version, compiled package SHA256, source commit SHA, status `MAINTAINER_ACCEPTED`, and evidence/decision references. No old certified profile or acceptance contents may be changed; create a new ID for fixes.

If the maintainer is not present or the game host isn't accessible, BI-002 stays ACTIVE/BLOCKED with typed proof ceiling. A CODEOWNERS file, PR approval, or green workflow is **not itself** Sims gameplay proof.
