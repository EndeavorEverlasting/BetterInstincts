# Awake household handoff

Parent remains BI-002. Manual observation used Windows Sims 4 1.121.361.1020 and the operator-directed open Live session.

| Sixth Gear stage | Disposition |
| --- | --- |
| P141 | Extend the existing household allocator. Portrait cycling alone misses needs and skills. A queue cancellation engine cannot establish player ownership from these observations. A new scheduler duplicates allocation and would still need native evidence. |
| P95 | Capture-bound member activity and selection feed the existing allocator and host turn. A verified sleeper, recharging Servo, or absent Sim yields attention to the first eligible awake actor. Select once, verify the selected identity, and recheck the exact affordance and queue before issuing the task. |
| P82 | Exercise sleeping and away actors, Servo motives, stale capture, unknown wake state, busy recovery and player direction in the existing host tests. |
| P08 | Manual game baseline observed. Candidate native execution remains blocked on a source-proven actor and queue adapter. |
| P07 | Implement the policy in the allocator and its normal host entry point. Deliver through the isolated feature branch. |
| P124 | Reuse existing eligibility, preferences, skills, and queue capacity. No parallel scheduler or desktop loop. |

## Manual play evidence and follow-up

- Friday 12:27 PM to 10:51 PM at normal speed, over 13 real minutes after conservative pause allowances. Checked all three portraits and paused at handoff without saving.
- Charlee returned from school at 3 PM with low Fun and a school discipline warning. Rejected the optional classmate invitation. The Fun icon produced a tooltip without a confirmed action. Phone, Entertainment, Play Game put a phone action in the queue and Fun rose. Later leisure brought it green. Bladder and Hunger icons led to a toilet and meal with corresponding green bars. Energy produced sleep and recovered to green. Read the queue and need trend separately before repeating an action.
- Olga's autonomous dancing raised a blocking Likes Dancing prompt. Declined it and play resumed. Handle known modals by semantic identity and current button state. Preserve unknown choices for review.
- The Servo self menu exposed Recharge. Olga recharged, then Bernice used More Choices, Servo, Tune Up on awake Olga. Durability returned from yellow to full green. Recharge protected Olga from concurrent care selection until awake. Bernice later recovered Charge in a sleep pod after using the Charge icon.
- Olga's computer offered job search but no existing career task. The available Write Skill Book option offered Guidebook to Archaeology. After queueing it, the game paused at Name the Book. Accepting the game-generated title started writing. Queue entry, modal completion, and actual engagement were distinct observations.
- Portrait selection and camera motion settled after the first returned frame. Double-click centered on the actor but an immediate world click opened the door menu as the camera moved. Closed the menu. Require settled camera readback and a newly verified target.
- No confirmed autonomous action displaced an operator-owned queue in this run. Preserve unknown ownership. Existing autonomy moderation and preference owners remain the route for further native proof.

Next live canary under issue #171: bind a disposable current-patch roster, verify a sleep transition, observe one actor handoff and one eligible task enqueue, then show the sleeping and player-owned queues remain intact. Record target engagement and rollback.

## 2026-11-14 continuation — sleep-to-portrait is independent of chores
The initial PR #229 only proposed a portrait when another eligible work allocation existed. The operator corrected the first parent gate: even with **no queued tasks**, sleeping/recharging/away means immediately rotate attention to the next verified AWAKE household portrait, wrap the original roster and reobserve the selected Sim's needs and queue. A critically hungry awake Sim must not be excluded by the chore allocation wellbeing floor. With one Sim/all asleep/no permitted awake Sim, preserve the paused/recovery state and never spin. Optional `attention_review` completion receipt (actor/capture/proof) advances another awake portrait one step, always requiring a new capture. `host_stack` remains the existing plan port; no native game input or installed logic is claimed, so issue #171 retains actual current-game actor selection as the local P08 gate.
