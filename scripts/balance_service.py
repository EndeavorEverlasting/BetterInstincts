"""CLI for balance/imbalance microsystem evaluation (tandem wellness)."""
import argparse
import json
import sys

from betterinstincts.balance_service import (
    BalanceServiceError,
    evaluate_balance_service,
    load_contract,
)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--balance-level", default=None)
    p.add_argument("--ailment", default=None)
    p.add_argument("--emotion", default=None)
    p.add_argument("--moodlet", action="append", default=[])
    p.add_argument("--inventory-has-holistic-cure", action="store_true")
    p.add_argument("--apothecary-stall", action="store_true")
    p.add_argument("--apothecary-skill", type=int, default=None)
    p.add_argument("--meditate-available", action="store_true")
    p.add_argument("--houseplants", action="store_true")
    p.add_argument("--hunger", type=float, default=0.8)
    p.add_argument("--bladder", type=float, default=0.8)
    p.add_argument("--energy", type=float, default=0.8)
    p.add_argument("--hygiene", type=float, default=0.8)
    p.add_argument("--fun", type=float, default=0.8)
    p.add_argument("--social", type=float, default=0.8)
    p.add_argument("--prior-json", default=None)
    p.add_argument("--show-contract", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.show_contract:
            print(json.dumps(load_contract(), indent=2))
            return 0
        prior = json.loads(args.prior_json) if args.prior_json else None
        needs = {
            "hunger": args.hunger,
            "bladder": args.bladder,
            "energy": args.energy,
            "hygiene": args.hygiene,
            "fun": args.fun,
            "social": args.social,
        }
        result = evaluate_balance_service(
            needs,
            balance_level=args.balance_level,
            ailment=args.ailment,
            emotion=args.emotion,
            moodlets=args.moodlet,
            inventory_has_holistic_cure=(
                True if args.inventory_has_holistic_cure else None
            ),
            apothecary_stall_available=args.apothecary_stall,
            apothecary_skill_level=args.apothecary_skill,
            natural_living_meditate_available=args.meditate_available,
            houseplants_available=args.houseplants,
            prior_state=prior,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (BalanceServiceError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(
            json.dumps({"state": "BALANCE_SERVICE_FAILED_CLOSED", "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
