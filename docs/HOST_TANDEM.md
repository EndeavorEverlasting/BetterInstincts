# Needs and gardening in tandem

`betterinstincts.host_tandem.run_tandem_session` is an explicitly invoked async
session over the existing host listener. Needs observation continues while a
gardening interaction awaits its outcome. The Sim still receives one interaction
at a time. There is no new needs scorer, persistent goal registry or daemon.

The caller supplies four trusted ports: asynchronous `observe`, asynchronous
`execute`, asynchronous `interrupt_owned`, and the existing real presence `probe`.
`execute(command, snapshot)` starts one interaction and awaits its observed
outcome. Returning an input acknowledgement is insufficient. An outcome must
identify the actor, action and actual outcome observation. Callback cancellation
must cooperate promptly and must never translate into cancelling a Sim queue.

The session requires an explicitly ACTIVE listener session and an exact
`actor_ref`. Every observation must bind that same actor. A caller must keep one
writer per actor/session; cooperating screen executors must also use the existing
exclusive per-game-PID screen lease and fresh admission before each input. These
callback ports are an integration seam, not installed desktop adapters or a
playable mod. No live session is started by importing this module.

## Arbitration and continuation

Each fresh observation passes through the listener, player-presence gate, host
stack, canonical needs evaluation and gardening peer. While a gardening action
is pending, the observer continues independently. Only an exact current
`host_activity_ref` plus `host_activity_owner: HOST` can exempt that owned action
from the generic busy gate. Player and unknown actions retain their protection.

A currently observed need remedy can suspend owned gardening. The interruption
port must independently verify ownership, obtain screen admission, and return
`HOST_ACTION_INTERRUPTED` with the exact actor, action and current capture before
any remedy starts. Unknown ownership or an incomplete interruption receipt
cannot authorize another action. New homework similarly suspends owned
gardening and returns a responsibility handoff rather than competing for control.

Pending needs actions cannot be interrupted by gardening. After an observed
outcome, a fresh snapshot must revalidate the next action. A completed remedy
with no observed improvement cannot blindly repeat the same remedy. The garden
goal remains pending throughout; outcome observation alone does not prove need
recovery, gardening completion or responsibility safety.

Fresh player activity ends host control without cancelling the player's queue.
Actor changes, observer/action timeouts and unproven outcomes stop continuation.
Stopping a Python task ends its observation continuation, not the Sim action.
The receipt retains a pending-action reference where applicable for reobservation.

## Bounds and proof

`contracts/host-listener.v1.json` owns the limits: at most the remaining listener
tick budget (64 maximum), 1–120 seconds between observations, observation timeout
15 seconds by default (30 maximum), action timeout 120 seconds (600 maximum), and
64 in-memory events. Trusted async ports must honor cancellation; these timeouts
cannot forcibly terminate an uncooperative external adapter.

`python -m unittest tests.test_host_tandem -v` exercises actual coroutine overlap,
sleep preemption and gardening resumption, player priority, unknown ownership,
homework handoff, ineffective-rest suppression, actor changes, ACK rejection and
timeouts. These are offline observations of callback behavior. Real game ports,
live recovery and a completed gardening afternoon remain unproved. BI-002 stays
ACTIVE, including its separate five-vanilla/five-modified hunger, rollback and
player-queue evidence gates.
