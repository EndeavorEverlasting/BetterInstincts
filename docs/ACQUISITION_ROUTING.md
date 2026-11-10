# Household acquisition: observed computer Order and non-computer sources

Owner: `contracts/upgrade-parts-force.v1.json#acquisition_routing` and `betterinstincts/upgrade_parts_force.py`. This is an additive part of the existing DIY parts host planner, **not** a second autonomous clicker or a replacement for the shared screen lease. The machine ontology owns `OBSERVED_MENU_ROUTE`, `ACQUISITION_SOURCE` and `ACTION_EFFECT_CLASS` (BI-ONT-026/027). All current source planners are **offline/evaluate-only**; no GUI action, shopping charge, OS peripheral setting or Sims save is mutated by the CLI.

## Canonical computer interaction call stack

1. Observe the active household's current portrait strip and select the **specific observed portrait** requiring resources. Validate identity before every independent effect. It is not safe to hardcode a named household, a fixed N, a fixed portrait rectangle, or assume that pressing Space always lands on the intended Sim.
2. **Left-click an observed computer or laptop** within an admitted Live context. Some Order actions may work while the active Sim is elsewhere: proximity is **not a prerequisite assumed by the planner**, but verify behavior in the installed game before treating it as instantaneous.
3. Inspect current pie options. If **Order** is visible, choose that exact item; otherwise, if **More Choices** is visibly available, take one page and observe **again**. The click count is *not* a template. A current operator observation indicates Order may itself be buried.
4. Within Order, choose the desired **observed** domain. For the standard base path this is **Purchase Upgrade Parts**. The operator often sees it after two More Choices clicks; this is a **hint**, not an instruction to click twice blindly. Other Order domains are possible only when actually visible. `next_observed_menu_choice` returns one exact observed target or a bounded, fresh More Choices step; repeated page signatures, exhausted pages, missing or ambiguous labels **DENY**.
5. Open the exact observed picker, iterate each **visible** requested item, select a supported observed quantity control or repeat a single-purchase path, admit each spend, and check both the actual item destination and funds delta. If the picker closes, **re-observe and reopen** instead of guessing which menu remained on screen. A click or plan never proves stock.
6. If targeting more Sims, select the next **observed portrait ID**, revalidate player/screen ownership, and repeat. When the player is using their mouse/keyboard or Sims scene changes, yield rather than hijacking control.

## Source routing and time/effect semantics

| Requested resource | Source domain | Effect hypothesis | What is proof? |
| --- | --- | --- | --- |
| Common, Electronic, Plumbing, Kitchen, Robot Salvage Upgrade Parts | Computer → Order → Purchase Upgrade Parts | `INSTANT_UI_CANDIDATE` — may be immediate despite selected Sim being away | Appropriate selected-Sim inventory plus Simoleon delta |
| Eco-Upgrade Parts (Eco Lifestyle) | Fabricator → Fabricate → Fabricated Eco-Upgrade Part | `SIM_QUEUED_AND_POSSIBLY_FAILED`; 15 bits + 10 pieces **per attempt** | Actual craft result and pocket inventory; not just recipe selected |
| Regular generator fuel | Obtain bits/pieces (e.g. Recycler, from approved recyclables), then observe generator's refill interaction | `RESOURCE_CONVERSION_THEN_REFILL`; not a conventional purchase item | Recycled resource and generator fuel level readback |
| Insect biofuel / biofuel-filled can | Insect Farm → care for insects → when ready, Collect Bio Fuel | `TIME_GATED_HARVEST`; readiness/health and collection matter | Source collection and destination amount; exact can label must be observed on game build |

The user's word **fuel** is ambiguous. Route generator refill resources to `generator_fuel`, and insect-farm biofuel to `insect_biofuel_filled_can` as distinct semantic IDs. Do not assert that an "insect biofuel-filled can" is sold by the computer, fabricated by Recycler, or has a specific live inventory label until observed. The Recycler is an upstream source of **bits/pieces**, not a verified source of bottled insect fuel. The candidate **instant UI** effect is not a universal 99% success claim: queue, delay, actor movement and actual output must be observed separately.

## Insect biofuel farm production — designed, NOT automated

For the screenshot-grounded **Collect Bio-Fuel / Nurture / Collect Cricket Flour / Clean Out Insect Farm** path, see [Insect Farm Biofuel](INSECT_FARM_BIOFUEL.md) and [the machine-readable phased design](../plans/active/BI-INSECT-FARM-BIOFUEL-DESIGN-20261110.v1.json). This design preserves an *N*-farm, any-portrait, health-aware source state machine, harvest-versus-food arbitration, queued actions, and separate generator inventory/fuel proof; **Clean Out** is never an autonomous maintenance action. These are research and implementation acceptance gates only: no harvest, cursor automation or new live service is coded or permitted by the design document. Exact game version and outcome evidence are pending.

## Runtime authority and non-goals

- Use `betterinstincts/screen_admit.py` and the existing cooperative player-presence/desktop owner, with fresh per-effect admission, observed on-lot target, current UI/menu/actor context, bounded navigation and no active operator input. The catalog is **not a live SendInput executor**.
- Do not enter Buy/Build to obtain these stocks without all floor/room save and library-checkpoint gates. No game cheats, speculative debug objects, EA Connect, arbitrary inventory writes, automatic money injection, service/driver resets or unapproved household spending.
- For a pack-dependent source, the installed pack must be observed. If a source is hidden by patch, mod, age/life stage or situation, report **SOURCE_NOT_OBSERVED** instead of substituting a different item or hitting More Choices indefinitely.
- Independent actual game certification is still required for the selected patch and relevant household; BI-002 hunger remains active and unaffected. A CLI source plan cannot satisfy BI-002, DIY pocket-stock certification, or local Cursor hook-activation proof.

## Read-only CLI (real observation inputs)

```powershell
python -m scripts.upgrade_parts_force sources
python -m scripts.upgrade_parts_force menu-next --options observed-menu.json --goal "Purchase Upgrade Parts" --visited prior-page-signatures.json
python -m scripts.upgrade_parts_force acquisition --portraits observed-portraits.json --requests requested-items.json --packs-observed "Eco Lifestyle" "Discover University" --selected-slots 0 1
python -m scripts.upgrade_parts_force order-domain --portraits observed-portraits.json --domain "Purchase Upgrade Parts" --item "Common Upgrade Parts" --item "Robot Salvage Parts"
```

`observed-menu.json` is an array of current visible labels (e.g. `["Order", "More Choices"]`), and `prior-page-signatures.json` is `next_history` from the previous invocation (omit on the first page). `observed-portraits.json` is an array of `{"slot":0,"portrait_id":"observed-ui-identity","observed":true}` for the **current** household, not a saved hardcoded Sims roster. `requested-items.json` is an array of `{"item":"eco parts","quantity":1}` records. Outputs always include `execute_allowed:false`.

## Supporting external evidence, not automatic game proof

- EA help: [Civil Designer — fabricate Eco-Upgrade Part from 15 bits and 10 pieces](https://help.ea.com/en/articles/the-sims/the-sims-4/the-sims-4-civil-designer-career/).
- EA gameplay: [Eco Lifestyle's Insect Farm provides generator biofuel](https://www.ea.com/games/battlefield/news/eco-lifestyle-gameplay).
- EA community: [Generator fuel can use recycled resource currency](https://forums.ea.com/discussions/the-sims-4-general-discussion-en/where-do-i-get-the-fuel-for-the-generators/2668272).
- Carl's Sims 4 Guide: [insect farm care, harvest readiness and generator biofuel](https://www.carls-sims-4-guide.com/expansionpacks/ecolifestyle/insect-farms.php).
- Operator's current menu observation: computer left-click, Order, varying More Choices, Purchase Upgrade Parts, instant-leaning UI behavior. Exact local patch behavior is a pending live observation.
