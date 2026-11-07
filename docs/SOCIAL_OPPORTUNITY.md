# Social opportunity — Sims-library occult gate — P95

Machine owner: [`contracts/social-opportunity.v1.json`](../contracts/social-opportunity.v1.json).
Evaluator: `python -m scripts.social_opportunity` / `betterinstincts.social_opportunity`.
Journey spine: [`docs/TEEN_DAY_JOURNEY.md`](TEEN_DAY_JOURNEY.md).

## Design brief

- **Subject:** Invite-over / classmate OK–Cancel dialogs.
- **Audience:** host + operator when a social prompt appears.
- **Job:** Look up the invitee in the **Sims library** (relationship / known-Sims observation). Match must be **unique**. App decides OK vs Cancel from evidenced occult status — never from name vibe.
- **Not:** EA occult API certification; vision-invented vampire flags; auto-OK.

## LOCAL_OBSERVED (2026-11-07)

“Should Charlee invite over classmate Morgan?” — occult UNKNOWN. Operator: app must library-lookup Morgan; decision must not be ambiguous. Capture: `operator:invite-morgan-occult-unknown-20261107`.

## Decision rule

| Library lookup | Occult | Dialog |
| --- | --- | --- |
| not run | — | `SOCIAL_LOOKUP_REQUIRED` → lookup; **no OK** |
| NOT_FOUND / AMBIGUOUS_NAME | — | **Cancel** |
| FOUND_UNIQUE | UNKNOWN | **Cancel** |
| FOUND_UNIQUE | VAMPIRE / OTHER_OCCULT | **Cancel** |
| FOUND_UNIQUE | HUMAN / KNOWN_SAFE_NON_VAMPIRE | **OK allowed** |

## Proof ceiling

`HOST_SOCIAL_OPPORTUNITY_SAFETY_NOT_EA_OCCULT_API`.
