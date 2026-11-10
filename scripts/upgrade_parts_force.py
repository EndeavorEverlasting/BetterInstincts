#!/usr/bin/env python3
"""Household DIY parts budget + upgrade-parts spam-buy CLI.

Always-ready DIY stock lives in each Sim's pocket inventory (N members).
Preferred scalable path: Spawn Crafting Supplies bulk; phone/computer Order fills gaps.

Examples:
  python -m scripts.upgrade_parts_force catalog
  python -m scripts.upgrade_parts_force budget
  python -m scripts.upgrade_parts_force how-to-buy
  python -m scripts.upgrade_parts_force plan --part robot_salvage_parts --quantity 20
  python -m scripts.upgrade_parts_force household --members 4 --path spawn --checklist
  python -m scripts.upgrade_parts_force certify --members 4 --observations obs.json
  python -m scripts.upgrade_parts_force record --run-id diy-parts-lab-001 --members 4 --member-slot 0 --part-id robot_salvage_parts --observed-count 50
  python -m scripts.upgrade_parts_force status --run-id diy-parts-lab-001
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.upgrade_parts_force import (
    UpgradePartsForceError,
    acquisition_source_catalog,
    next_observed_menu_choice,
    plan_acquisition_routes,
    plan_computer_order_domain,
    budget_snapshot,
    catalog_snapshot,
    evaluate_diy_parts_cert,
    how_to_buy,
    plan_household_parts_budget,
    plan_parts_force,
    record_part_observation,
    status_cert,
    steps_to_operator_checklist,
)


def _print(obj: object) -> int:
    print(json.dumps(obj, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog", help="List upgrade-part catalog + path summaries")
    sub.add_parser("budget", help="Show DIY kit pocket-stock targets")

    sub.add_parser("sources", help="Show observed-route domains and instant/queued source classes")
    acquire = sub.add_parser("acquisition", help="Preview actor-safe household source acquisition (NO clicks)")
    acquire.add_argument("--portraits", required=True, help="JSON array: {slot,portrait_id,observed:true}")
    acquire.add_argument("--requests", required=True, help="JSON array: {item,quantity}")
    acquire.add_argument("--selected-slots", type=int, nargs="*", default=None,
                         help="Optional exact observed portrait slot(s); default all")
    acquire.add_argument("--packs-observed", nargs="*", default=None,
                         help="Actual observed installed pack names (never assumed)")
    acquire.add_argument("--player-directed", action="store_true")

    order = sub.add_parser("order-domain", help="Plan any exact observed computer Order domain (NO clicks)")
    order.add_argument("--portraits", required=True, help="Observed portrait JSON array")
    order.add_argument("--domain", required=True, help="Target Order domain label")
    order.add_argument("--item", action="append", required=True, help="Desired exact item label, repeatable")
    order.add_argument("--selected-slots", type=int, nargs="*", default=None)
    order.add_argument("--player-directed", action="store_true")

    menu = sub.add_parser("menu-next", help="Resolve exactly one observed menu page (NO clicks)")
    menu.add_argument("--options", required=True, help="JSON array of current visible labels")
    menu.add_argument("--goal", required=True, help="Desired exact menu choice")
    menu.add_argument("--visited", help="Optional JSON array of previously seen page signatures")


    how = sub.add_parser("how-to-buy", help="Print phone/computer Order path")
    how.add_argument("--part", default="robot_salvage_parts")

    plan = sub.add_parser("plan", help="Emit evaluate-only spam-buy / spawn plan")
    plan.add_argument("--part", default="robot_salvage_parts")
    plan.add_argument("--quantity", type=int, default=None)
    plan.add_argument("--path", choices=["spawn", "phone", "computer"], default=None)
    plan.add_argument("--mode", default="live")
    plan.add_argument("--player-directed", action="store_true")
    plan.add_argument("--checklist", action="store_true")

    household = sub.add_parser("household", help="Plan DIY kit stock for every portrait (N)")
    household.add_argument("--members", type=int, required=True, help="Observed Live portrait count N")
    household.add_argument("--path", choices=["spawn", "phone", "computer"], default="spawn")
    household.add_argument("--quantity", type=int, default=None)
    household.add_argument("--mode", default="live")
    household.add_argument("--player-directed", action="store_true")
    household.add_argument("--checklist", action="store_true")

    certify = sub.add_parser("certify", help="Evaluate machine-readable cert from attested observations")
    certify.add_argument("--members", type=int, required=True)
    certify.add_argument(
        "--observations",
        required=True,
        help="JSON file: [{member_slot, parts:{part_id:count|null}}, ...]",
    )

    record = sub.add_parser("record", help="Record one attested pocket count into a cert run")
    record.add_argument("--run-id", required=True)
    record.add_argument("--members", type=int, default=None, help="Required on first record")
    record.add_argument("--member-slot", type=int, required=True)
    record.add_argument("--part-id", required=True)
    record.add_argument("--observed-count", type=int, required=True)

    status = sub.add_parser("status", help="Read cert.json for a run-id")
    status.add_argument("--run-id", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "catalog":
            return _print(catalog_snapshot())
        if args.cmd == "sources":
            return _print(acquisition_source_catalog())
        if args.cmd == "acquisition":
            portraits = json.loads(Path(args.portraits).read_text(encoding="utf-8"))
            requests = json.loads(Path(args.requests).read_text(encoding="utf-8"))
            return _print(plan_acquisition_routes(
                portraits=portraits,
                requests=requests,
                selected_slots=args.selected_slots,
                packs_observed=args.packs_observed,
                player_directed=bool(args.player_directed),
            ))
        if args.cmd == "order-domain":
            portraits = json.loads(Path(args.portraits).read_text(encoding="utf-8"))
            return _print(plan_computer_order_domain(
                portraits=portraits, domain=args.domain, item_labels=args.item,
                selected_slots=args.selected_slots,
                player_directed=bool(args.player_directed),
            ))
        if args.cmd == "menu-next":
            visible = json.loads(Path(args.options).read_text(encoding="utf-8"))
            visited = (json.loads(Path(args.visited).read_text(encoding="utf-8"))
                       if args.visited else ())
            return _print(next_observed_menu_choice(
                visible_options=visible, desired_choice=args.goal,
                visited_signatures=visited,
            ))

        if args.cmd == "budget":
            return _print(budget_snapshot())
        if args.cmd == "how-to-buy":
            return _print(how_to_buy(args.part))
        if args.cmd == "plan":
            result = plan_parts_force(
                part_id=args.part,
                quantity=args.quantity,
                path=args.path,
                game_mode=args.mode,
                player_directed=bool(args.player_directed),
            )
            if args.checklist:
                result = dict(result)
                result["operator_checklist"] = steps_to_operator_checklist(result)
            return _print(result)
        if args.cmd == "household":
            result = plan_household_parts_budget(
                members=args.members,
                path=args.path,
                quantity=args.quantity,
                game_mode=args.mode,
                player_directed=bool(args.player_directed),
            )
            if args.checklist:
                result = dict(result)
                result["operator_checklist"] = steps_to_operator_checklist(result)
            return _print(result)
        if args.cmd == "certify":
            obs_path = Path(args.observations)
            raw = json.loads(obs_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "members" in raw:
                observations = raw["members"]
            else:
                observations = raw
            return _print(evaluate_diy_parts_cert(members=args.members, observations=observations))
        if args.cmd == "record":
            return _print(
                record_part_observation(
                    run_id=args.run_id,
                    member_slot=args.member_slot,
                    part_id=args.part_id,
                    observed_count=args.observed_count,
                    members=args.members,
                )
            )
        if args.cmd == "status":
            return _print(status_cert(args.run_id))
    except UpgradePartsForceError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
