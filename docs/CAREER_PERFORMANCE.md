# Career performance budgeting (horizon BI-006 lane)

Teen **High School Student** daily homework routing lives under [`docs/TEEN_HOMEWORK.md`](TEEN_HOMEWORK.md) and `contracts/teen-homework.v1.json`.

**Async peer microsystem:** [`docs/CAREER_SERVICE.md`](CAREER_SERVICE.md) / `contracts/career-service.v1.json` keeps a sticky `CAREER_OBLIGATION` in tandem with need services so agents do not forget homework while recovering needs. Policy lanes still delegate to `teen_homework` / `school_day`.

That lane budgets the career-panel **homework** daily task for teens at home (lot-scan → put in inventory when the book is on a surface, then inventory/computer recovery, survival ordering). It is **BI-006-adjacent** career-performance scaffolding only — not adult employment promotion proof and not scenario **Get a career** (`docs/SCENARIO_GOALS.md`).

Proof ceiling remains offline host catalog + supplied observations until game-certified career progression evidence exists under horizon gates.

## Deterministic Work Hard → next-Sim attention

The source-only career port `career_service.evaluate_work_shift_tone` inspects one **current-capture** work shift for the **selected** household member, without replacing the teen homework microsystem. The policy is for confirmed `AT_WORK` **rabbit-hole** shifts, including qualifying part-time jobs, not an active-career appointment or a Sim still walking to work.

**Promotion opportunity:** An observed `promotion_requirements: MET`, `daily_task: COMPLETE` or `NOT_REQUIRED`, `performance: BELOW_TARGET`, and a truly available `WORK_HARD` tone create a candidate. The selected member must also clear the existing household's mood, temperament and personal-needs welfare floor, have an observed `NORMAL` tone owned by the game/host (not the player), and have an unreserved queue. The recommendation does **not** guarantee promotion or guess a performance gain. Unknown data, player-set tones, exhaustion, completed performance, missing prerequisites or unavailable options do not produce Work Hard.

**Sequence:** observed at work → `WORK_HARD_ADMISSION_REQUIRED` (advisory only) → independent exact-patch native effect admission → **fresh observation** of `current_tone: WORK_HARD` → existing household next-awake portrait handoff → fresh newly selected Sim/needs/queue assessment. A work tone that should not be changed simply releases attention to an eligible awake peer; an active career does **not** auto-release because that would abandon playable career duties. No portrait movement without a verified roster, and no arbitrary second scheduler.

The host exposes `CAREER_WORK_HARD_ADMISSION_REQUIRED` before `AWAKE_HOUSEHOLD_HANDOFF_READY` while preserving global player, scene, save, camera and overlay gates. Both plans have `execute_allowed: false`. `contracts/career-service.v1.json#work_shift_tone` and `contracts/household-economy.v1.json#work_shift` own the machine vocabulary; `tests/test_career_service.py` and `tests/test_household_economy.py` cover adversity. The coverage registry lists `career-work-hard-tone` as **SOURCE_PRESENT, NOT GAME_CERTIFIED**. Exact EA-native action and P08 Windows validation remain issue #171; BI-002 hunger remains active.

**External mechanic grounding (not native API proof):** [EA careers guide](https://help.ea.com/en/articles/the-sims/the-sims-4/the-sims-4-careers/) discusses promotion requirements, daily tasks and mood; the [Prima Sims 4 gameplay guide](https://primagames.com/eguides/the-sims-4-eguide/get-a-job/going-work) discusses choosing work tones from an at-work Sim portrait. Neither provides version-pinned EA script/tuning IDs or installs the feature.
