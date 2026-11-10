"""Portable profiles: opaque identities must not leak one player's household into another."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from betterinstincts.diy_skill_force import (
    DiySkillForceError,
    completed_skill_ids_for_member,
    empty_completion_ledger,
    load_completion_ledger,
    plan_household_skill_force,
    record_skill_dispatched,
    save_completion_ledger,
)
from betterinstincts.household_judgment import (
    HouseholdJudgmentError, bind_household_scope,
)
from betterinstincts.installation_profiles import (
    InstallationProfileError, create_profile, household_ledger_path,
)
from scripts import diy_skill_force as cli


class HouseholdScopeTests(unittest.TestCase):
    def scope(self, profile="default", save="save-a", household="house-a", keys=None):
        return bind_household_scope(
            profile_id=profile, save_key=save, household_key=household,
            roster_keys=["portrait-001", "portrait-002"] if keys is None else keys,
        )

    def test_profile_save_household_and_portrait_independence(self):
        baseline = self.scope()
        self.assertEqual(baseline, self.scope())
        self.assertEqual(baseline["member_count"], 2)
        self.assertIsNone(baseline["execution_permit"])
        self.assertNotIn("save-a", str(baseline["member_keys"]))
        self.assertNotIn("portrait-001", str(baseline["member_keys"]))
        for candidate in (
            self.scope(profile="another"), self.scope(save="save-b"),
            self.scope(household="house-b"),
        ):
            self.assertNotEqual(candidate["scope_id"], baseline["scope_id"])
            self.assertNotEqual(candidate["member_keys"], baseline["member_keys"])
        changed_roster = self.scope(keys=["portrait-002", "portrait-001"])
        self.assertEqual(changed_roster["scope_id"], baseline["scope_id"])
        self.assertNotEqual(changed_roster["roster_fingerprint"], baseline["roster_fingerprint"])

    def test_arbitrary_household_size_without_named_sims(self):
        for n in (1, 2, 4, 9, 24):
            scope = self.scope(keys=[f"portrait-{i:03d}" for i in range(n)])
            plan = plan_household_skill_force(
                members=n, skill_ids=["handiness"], household_scope=scope,
                completion_ledger=empty_completion_ledger(),
            )
            self.assertEqual(len(plan["dispatch_units"]), n)
            self.assertEqual([u["member_key"] for u in plan["dispatch_units"]], scope["member_keys"])
            self.assertEqual(plan["identity_scope_id"], scope["scope_id"])

    def test_unstable_names_duplicates_missing_and_invalid_profiles_denied(self):
        for kwargs in (
            {"profile_id": "Upper"},
            {"save_key": "../escape"},
            {"household_key": "Family Name"},
            {"roster_keys": ["portrait-1", "portrait-1"]},
            {"roster_keys": ["Named Sim With Spaces"]},
            {"roster_keys": []},
        ):
            args = {
                "profile_id": "default", "save_key": "save-a",
                "household_key": "house-a", "roster_keys": ["portrait-1"],
            }
            args.update(kwargs)
            with self.subTest(args=args), self.assertRaises(HouseholdJudgmentError):
                bind_household_scope(**args)

    def test_cross_save_and_profile_ledger_skips_fail_closed(self):
        first = self.scope()
        ledger = empty_completion_ledger()
        ledger["scope_id"] = first["scope_id"]
        record_skill_dispatched(
            ledger, member_key=first["member_keys"][0],
            skill_id="handiness", skill_stat="Major_Handiness", level=10,
        )
        same = plan_household_skill_force(
            members=2, skill_ids=["handiness"], household_scope=first,
            completion_ledger=ledger,
        )
        self.assertTrue(same["dispatch_units"][0]["skip_dispatch"])
        self.assertFalse(same["dispatch_units"][1]["skip_dispatch"])
        for other in (self.scope(save="save-b"), self.scope(profile="another"),
                      self.scope(household="house-b")):
            with self.subTest(other=other["scope_id"]), self.assertRaisesRegex(
                DiySkillForceError, "CROSS_HOUSEHOLD_LEDGER_REUSE_FORBIDDEN"
            ):
                plan_household_skill_force(
                    members=2, skill_ids=["handiness"], household_scope=other,
                    completion_ledger=ledger,
                )
        legacy = empty_completion_ledger()
        record_skill_dispatched(
            legacy, member_key="old-session::idx::0",
            skill_id="handiness", skill_stat="Major_Handiness", level=10,
        )
        with self.assertRaisesRegex(DiySkillForceError, "CROSS_HOUSEHOLD"):
            plan_household_skill_force(
                members=2, skill_ids=["handiness"], household_scope=first,
                completion_ledger=legacy,
            )

    def test_private_ledger_placement_persistence_and_profile_isolation(self):
        with tempfile.TemporaryDirectory() as root:
            settings = Path(root) / "betterinstincts" / "settings.v1.json"
            first = self.scope()
            path = household_ledger_path(
                profile_id="default", scope_id=first["scope_id"], settings_file=settings,
            )
            self.assertEqual(path.parent.name, "default")
            self.assertFalse(path.exists())
            self.assertFalse(settings.exists())
            ledger = empty_completion_ledger()
            ledger["scope_id"] = first["scope_id"]
            record_skill_dispatched(
                ledger, member_key=first["member_keys"][0],
                skill_id="handiness", skill_stat="Major_Handiness", level=10,
            )
            save_completion_ledger(ledger, path)
            self.assertEqual(load_completion_ledger(path)["scope_id"], first["scope_id"])
            with self.assertRaises(InstallationProfileError):
                household_ledger_path(
                    profile_id="unknown", scope_id=first["scope_id"], settings_file=settings,
                )
            create_profile("another", settings)
            alternate = self.scope(profile="another")
            second_path = household_ledger_path(
                profile_id="another", scope_id=alternate["scope_id"], settings_file=settings,
            )
            self.assertNotEqual(path, second_path)
            self.assertFalse(second_path.exists())

    def test_cli_live_requires_scope_and_respects_private_custom_path(self):
        args = SimpleNamespace(
            save_key=None, household_key=None, profile_id=None,
            members=2, roster_key=["portrait-1", "portrait-2"], completion_ledger=None,
        )
        with self.assertRaisesRegex(cli.GateError, "SAVE_AND_HOUSEHOLD_SCOPE_REQUIRED"):
            cli._scoped_household_ledger(args, required=True)
        args.save_key = "save-a"
        with self.assertRaisesRegex(cli.GateError, "MUST_BE_SUPPLIED_TOGETHER"):
            cli._scoped_household_ledger(args)
        args.household_key = "house-a"
        with patch.object(cli, "view_installation_profile", return_value={"profile_id": "default"}), \
             patch.object(cli, "household_ledger_path", return_value=Path("/tmp/private/ledger.json")):
            scope, scoped_path = cli._scoped_household_ledger(args, required=True)
        self.assertEqual(scope["member_count"], 2)
        self.assertEqual(scoped_path, Path("/tmp/private/ledger.json"))
        assert scoped_path is not None
        self.assertEqual(cli._resolve_ledger_path(args, scoped_path), scoped_path)
        with self.assertRaisesRegex(cli.GateError, "CROSS_HOUSEHOLD"):
            cli._validate_scope_ledger(
                {"scope_id": self.scope(save="different")["scope_id"], "members": {}}, scope
            )

    def test_direct_live_helper_cannot_inherit_a_sample_session_or_unscoped_ledger(self):
        sig = inspect.signature(cli.execute_force_gaps)
        self.assertIs(sig.parameters["session_id"].default, inspect.Parameter.empty)
        with self.assertRaisesRegex(cli.GateError, "SCOPED_LOCAL_SESSION_AND_LEDGER_REQUIRED"):
            cli.execute_force_gaps(
                process_id=123, member_key="portrait-1",
                portrait_xy=(100, 100), session_id="host-session",
                console_strip_observed=True, completion_ledger_path=None,
            )


if __name__ == "__main__":
    unittest.main()
