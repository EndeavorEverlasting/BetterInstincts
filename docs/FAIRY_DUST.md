# Fairy Home and Fairy Dust

An explicit Fairy Dust stock goal can supply the installed native player's spare
turns with one observed interaction. Existing needs, queued priorities and
player-directed activity retain precedence.

| Observed state | Policy |
| --- | --- |
| A reachable Fairy Home exposes enabled **Shake for Fairy Dust** | Propose one shake for the selected Sim. A Fairy Home can expose this to a Fairy or non-Fairy. |
| **Shake for Fairy Dust** is greyed out with the no-dust reason | If no other route is available, check again after roughly one in-game day. Only a fresh enabled menu authorizes a proposal. |
| The selected household Fairy has an available **Sleep** or **Rest** interaction that serves a current need | Propose one use. Once it completes, observe the menu and inventory again. |
| A verified, reachable NPC Fairy exposes **Ask for Fairy Dust** | Propose the direct request. This includes an NPC encountered on an already loaded lot away from home. |
| The actor already has enough dust, safety is unverified, or the game is paused | Hold the dust action and preserve the current game state. |

A Fairy Home has no catch or assignment step. An invited Fairy's voluntary use
can change home readiness, which the same menu observation detects. A dust
goal never substitutes invitation, travel, occult conversion or clock controls
for the next observed interaction.

EA documents the direct social request and a separate **Regenerate Emotional
Force** interaction at the home. The operator's roughly 24 in-game hour
placement estimate informs the recheck cadence. Exact placement-only
generation and immediate sleep/rest yield need local measurement. The current
inventory count and attributable readback govern completion, even after a
successful NPC interaction or home use with zero dust.

Sources [EA Fairy guide](https://help.ea.com/en/articles/the-sims/the-sims-4/fairy-guide/) and
[Simming Simplified Fairy Dust guide](https://simmingsimplified.com/get-fairy-dust-in-the-sims-4/).

## Adapter contract

The existing [installed player runtime](../betterinstincts/installed_player_runtime.py)
retains the five-second inactivity gate, fresh second frame, player queue and
one-attempt dispatch. The [Fairy Dust policy](../betterinstincts/fairy_dust.py)
receives data from only these optional exact-build adapter ports.

- `read_fairy_dust(frame)` returns `None` when there is no explicit dust
  goal. Otherwise supply `scope=frame.scope()`, `capture=frame.capture`,
  observed `pack`, current actor `dust_count`, `goal_count`, `needs_safe`,
  and `game_minute`. Optional `home` and `npc` rows have a verified `target`,
  `on_actor_lot` and `accessible`. Each `shake`, `use` or `ask` row supplies
  its observed `action`, `available`, `capture` and `opportunity` ID. For
  sleep/rest, also supply `actor_is_fairy` in the observation and
  `benefits_current_need` on the use row. For a direct request, confirm
  `npc_fairy` on the NPC row. The
  `NO_FAIRY_DUST` reason maps to the disabled tooltip. History for
  `last_empty_check_game_minute` must stay within the same run, actor and
  home. `runtime.dust_recheck` exposes a current capture-bound due minute
  when the cycle returns `WAIT_FOR_HOME_RECHECK`.
- `submit_fairy_dust(proposal, frame)` must atomically recheck the exact EA
  interaction, target, actor, queue, generation, and current opportunity.
  Supply a stable opportunity ID across fresh observations and across repeat
  reports of the same opportunity. Return `QUEUED` or verified `NO_EFFECT`.
  Uncertain results hold that actor's attempt for reconciliation. The
  selector skips spent opportunity IDs so another currently observed source
  can proceed once that actor's attempt clears.
- `read_fairy_dust_outcome(proposal, frame)` supplies matching completion and
  a capture distinct from both admission frames for that exact proposal,
  actor and game run. Only an
  independently attributable dust gain matching the actor's measured pocket
  delta yields `DUST_GAIN_OBSERVED`. Zero-dust home use yields
  `FAIRY_HOME_USED_RECHECK`. A verified terminal no-effect outcome with zero
  inventory change clears the attempt without permitting the same opportunity
  to replay. A mismatched outcome leaves the attempt pending for its actor.
  Other actors and ordinary actions can proceed under their existing gates.

## Verification

Run `python -m unittest tests.test_fairy_dust tests.test_installed_player_runtime tests.test_native_ecology_bundle -v`.
The package builder exposes `--installed-fairy-dust` alongside
`--installed-player-runtime` and requires a local
`installed_fairy_dust_binding_ref` tied to the exact-build hook proof.

For [the remaining native gate](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171),
inspect installed Enchanted by Nature tuning and bind the three ports on the
Windows game host. Use read-only tuning exports and
`python -m scripts.tuning_audit --xml EXPORTED_XML` to pin each action.
Record the installed build, pack, interaction ID, actor and target, simulation
minute, and before/after observation IDs in an authorized disposable save.

| Trial | Evidence to capture |
| --- | --- |
| Newly placed home, left unused | Empty tooltip and Shake availability at placement and after roughly one unpaused in-game day. Record any earlier enabled observation and any change in the actor's pocket after shaking. |
| Selected Fairy uses an equivalent home | Exact Sleep or Rest menu option, starting need, completion, and an immediate menu and pocket readback. Compare with the unused home's elapsed simulation time. |
| Non-Fairy directly asks a reachable NPC Fairy | Exact Ask interaction and recipient, queue acknowledgement, and attributable pocket change or a verified zero-dust outcome. |
| Player takeover and rollback | Preserve a player-directed queue, then confirm the existing responder still works. Remove only the test package and verify the disposable save loads. |

The source tests and archive fixture establish the adapter contract. In-game
Fairy Dust behavior still requires those trials.
