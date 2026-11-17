# PS-0241 universal activity chains in the installed runtime

The next gate is exact-build Windows EA evidence under [#171](https://github.com/EndeavorEverlasting/BetterInstincts/issues/171).
Read [the installed adapter contract](../../docs/ACTIVITY_CHAIN.md#installed-runtime-adapter)
and [native authority](../../docs/NATIVE_GAMEPLAY_ARCHITECTURE.md).

## Source sprint

An isolated BetterInstincts branch from current `main` joins the owned
activity-chain policy, installed player callback and package gate. Existing
microsystems keep their domain policy, shared portrait selection and native
queue behavior. The activity chain handles only an available callback turn.
Protected saves, player/OS input, exact EA source, BI-002 and open ecology PRs
are outside this source sprint. The tracked consultation predates behavioral
changes. The source test boundary uses a controlled adapter.

Prepare source validation with:

```sh
python -m unittest tests.test_activity_chain tests.test_decision_horizon tests.test_installed_player_runtime tests.test_native_ecology_bundle -v
python -m scripts.check_horizon
python -m scripts.check_native_gameplay_authority --base-ref "$(git rev-parse origin/main)"
```

## Exact-build Windows gate

1. Confirm the pinned checkout, local game patch, DLC and mod versions.
   Identify a disposable lab save and capture the vanilla control and rollback
   baseline. Keep the existing startup and per-portrait procedures.
2. Inspect the installed EA interaction, queue, save-scope and outcome APIs
   read-only. Bind the existing callback port with that source evidence and a
   supported embedded Python interpreter. Package the exact inspected source
   using `python -m scripts.native_ecology_bundle build --help` to locate the
   existing build arguments and the activity-chain flags.
3. In the disposable save, observe automatic installed registration and
   run a stock-or-purchase → personal inventory → verified travel → craft →
   observed career result chain. Record the actor, resources, before/after
   capture references, queue, game-time and settlement for each effect.
4. Test a paused plan, a shorter work or needs window, player takeover, a
   portrait switch during an unsettled effect, and a lost acknowledgment.
   Confirm arrivals, purchases and inventory outcomes independently before
   advancing. Observe an existing native domain goal as protected control.
5. Qualify restart recovery using durable save-scoped intent and current
   outcome evidence before broad activation. Rerun the complete changed
   behavior and protected control, then uninstall the owned bundle and verify
   rollback. Keep BI-002's native hunger A/B and rollback independently open.
