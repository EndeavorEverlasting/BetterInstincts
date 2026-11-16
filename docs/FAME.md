# Fame and streaming drones

The Fame policy runs through the existing installed native player runtime. The
exact-build EA adapter supplies the current object and Sim state, enabled
interactions, and independent outcomes. Issue
[#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171) owns
local source inspection, binding and gameplay certification.

## Track and recover the assigned drone

1. Bind the specific streaming drone by opaque native object ID, model,
   household and assigned Sim. Retain its last-known zone, location and
   position reference when work, school, travel or unloading removes it from
   the current view. Keep the same binding through recharge and return.
2. Record a stream stop only on a new native observation of the same device.
   Keep battery, location and activity distinct. Battery Full and an airborne
   object are separate observations. A follower notification can describe an
   earlier activity. A favorite heart helps identify the inventory icon.
3. Before an imminent home departure or on low battery, propose End Stream
   and verify it before proposing Put in Inventory. An urgent need, a queued
   player action or an absent Sim takes priority. Let the device recharge until
   the native state says it is ready. No fixed recharge duration.
4. For a public-ground landing, wait for charge and an observed Begin Stream
   affordance. Verify that the same drone is streaming and following this Sim,
   and require a current route back to the verified home lot. After both are
   home, stop and stow the same drone. Each action has its own native result.
   This is the recovery route observed by the operator. Direct dragging from
   public ground and screen-based off-lot effects are excluded.
5. A remembered drone or incomplete search keeps acquisition blocked. A native
   search that completed without finding an owned drone and explicit acquisition
   permission can route to normal Build/Buy acquisition. The existing household
   budget and FLOOR_2 room census and Library checkpoint still own the
   transaction. This runtime produces the acquisition advisory only.

EA tuning files can identify states and interactions on a specific installed
build. An authorized save snapshot can supply last-known coordinates, not live
activity or a current affordance. Vision is a last-resort location aid using the
existing world-traversal two-frame evidence rules. Neither offline input can
activate the native policy. This change adds no save reader or vision worker.

Lithium battery is the first maintenance priority, then reliable components.
The HD camera is a creator upgrade. All three require an enabled native
interaction plus current Handiness and observed stock. See the
[streaming-drone interactions and upgrade requirements](https://simscommunity.info/2018/11/17/the-sims-4-get-famous-all-about-media-production-skill-objects/).

## Per-Sim Fame decisions

The adapter supplies the Sim's selected goal, Fame participation, current
rank, points, owned perks and observed eligible offers. Ownership and cost
are reconciled after one native purchase. The first unowned perk in the
selected branch is the candidate. Hold the points when its rank, predecessor,
reputation, cost or exact enabled affordance is unverified.

| Goal | Progression |
| --- | --- |
| Career and skills | Noticeable → CelebuSerum → Established Name → Career Hopper → Easy Street |
| Media and royalties | Corporate Partnership → Influencer → All-Nighter → Trailblazer → Lifestyle Brand |
| Social and visibility | Networking → PR Agency → Fan Favorite → Instant Besties → Squad |
| Good reputation | Giving Back → Rally → Star Treatment |
| Bad reputation | Who's Bad → Play the Villain → Feud Bringer |

Reputation branches begin at rank three and require the corresponding
reputation and an explicit goal. A Sim staying out of the spotlight keeps that
choice. Noticeable is the first option for a career-and-skills goal when rank
one and the native affordance are confirmed. Quirks do not count as purchasable
perks. See [Fame perks and prerequisite paths](https://simsvip.com/2018/10/23/the-sims-4-get-famous-celebrity-system-reputation-fame-perks-and-quirks/).

Training considers current, reachable options for the selected goal. It
uses a Dirichlet prior with parameters (3, 1, 1) over beneficial, neutral and
downside outcomes. Counts from correlated, player-uninterrupted native outcomes
update the three parameters for the same Sim, action and verified context
within the current run. It ranks candidates by posterior expected utility per
estimated active Sim-minute with utilities (+1, 0, −2). The prior and utilities
are policy starting values, not observed game frequencies. This keeps weak
history from granting access to a locked action or overriding work, school,
needs, or player control. Streaming can earn Fame and followers. Media
publishing can provide a separate payout and Media Production progression.
See [EA's Media Production guide](https://help.ea.com/en/articles/the-sims/the-sims-4/media-production-skill/).

## Native callback contract and verification

The optional archive flag is `--installed-fame` with
`--installed-player-runtime` and an exact-build, source-bound
`installed_fame_binding_ref`. The existing runtime calls
`read_fame(frame, tracked_object_id)`, `submit_fame(proposal, frame)`, and
`read_fame_outcome(proposal, frame)`. Reads can continue during player
control. Dispatch requires paired fresh idle frames, same input generation
and a revalidated form of the same proposal. The native adapter performs the
final atomic queue, actor, scene, target and affordance checks. An uncertain
submit remains reserved, and a later result must correlate with the exact
opportunity and a new capture. A running stream releases the effect slot
after native confirmation so departure and battery handling can proceed.
Only its eventual outcome can train the ranking.

Run `python -m unittest tests.test_fame tests.test_native_ecology_bundle -v`
for offline replay and isolated archive import. On the Windows Sims host,
inspect the exact-build Get Famous object state, interaction tests, Fame
tracker and perk resources on an admitted disposable household. Then exercise
charge → public landing → restart → follow → home → inventory and a rank-one
perk with independent evidence. Include work/school departure, a second
same-model drone, a Sim staying out of the spotlight, player takeover during
recovery, existing native callbacks, and package rollback. Keep the live
receipts local.
