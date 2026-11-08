"""CLI: recursive lot environment model (evaluate / persist only)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from betterinstincts.house_state import (
    HouseStateError,
    admit_mutation,
    attest_library_save,
    attest_save_as,
    load_contract,
    load_or_create,
    observe,
    persist_checkpoint,
    plan_next,
    recovery_advice,
    reject_blank_slate,
    save_model,
)


def _parse_entities(raw: str | None) -> dict:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise HouseStateError("ENTITIES_JSON_MUST_BE_OBJECT")
    return data


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    show = sub.add_parser("show-contract", help="Print house-state contract")
    show.set_defaults(fn="show")

    init_p = sub.add_parser("init", help="Load or create durable lot model")
    init_p.add_argument("--run-id", required=True)
    init_p.add_argument("--lot-id", required=True)
    init_p.add_argument("--capture", action="append", default=[])

    obs = sub.add_parser("observe", help="Merge observations into the same model")
    obs.add_argument("--run-id", required=True)
    obs.add_argument("--lot-id", required=True)
    obs.add_argument("--entities-json", default=None, help='JSON object of entity_id -> claim')
    obs.add_argument("--goal", action="append", default=[])
    obs.add_argument("--capture", action="append", default=[])
    obs.add_argument("--unknown", action="append", default=[])
    obs.add_argument("--note", default=None)
    obs.add_argument("--replace-goals", action="store_true")

    plan_p = sub.add_parser("plan", help="Plan next action from accumulated model")
    plan_p.add_argument("--run-id", required=True)
    plan_p.add_argument("--lot-id", required=True)

    admit_p = sub.add_parser("admit", help="Admit one mutation against current revision")
    admit_p.add_argument("--run-id", required=True)
    admit_p.add_argument("--lot-id", required=True)
    admit_p.add_argument("--action", required=True)
    admit_p.add_argument("--target", action="append", default=[])
    admit_p.add_argument("--expected-revision", type=int, default=None)

    save_as = sub.add_parser("attest-save-as", help="Record operator Save As attestation")
    save_as.add_argument("--run-id", required=True)
    save_as.add_argument("--lot-id", required=True)
    save_as.add_argument("--alias", required=True)
    save_as.add_argument("--capture-ref", required=True)
    save_as.add_argument("--operator-confirmed", action="store_true")

    lib = sub.add_parser(
        "attest-library-save",
        help="Record Build Mode Save-to-My-Library attestation (required before room mutate)",
    )
    lib.add_argument("--run-id", required=True)
    lib.add_argument("--lot-id", required=True)
    lib.add_argument("--building-id", required=True)
    lib.add_argument("--library-item-name", required=True)
    lib.add_argument("--capture-ref", required=True)
    lib.add_argument("--operator-confirmed", action="store_true")

    ckpt = sub.add_parser("checkpoint", help="Persist current model revision (continuity)")
    ckpt.add_argument("--run-id", required=True)
    ckpt.add_argument("--lot-id", required=True)
    ckpt.add_argument("--label", default="auto")

    rej = sub.add_parser("reject-blank-slate", help="Classify a discarded reassessment pattern")
    rej.add_argument("--pattern", required=True)

    rec = sub.add_parser("recovery", help="Operator recovery advice for wrecked lots")
    rec.add_argument("--has-known-good-save", action="store_true")
    rec.add_argument("--wreckage-only", action="store_true")

    args = p.parse_args(argv)
    try:
        if args.cmd == "show-contract":
            print(json.dumps(load_contract(), indent=2))
            return 0
        if args.cmd == "reject-blank-slate":
            print(json.dumps(reject_blank_slate({"pattern": args.pattern}), indent=2))
            return 0
        if args.cmd == "recovery":
            print(json.dumps(
                recovery_advice(
                    has_known_good_save=args.has_known_good_save,
                    wreckage_only=args.wreckage_only,
                ),
                indent=2,
            ))
            return 0

        model = load_or_create(
            args.run_id,
            args.lot_id,
            seed_captures=[f"capture:{c}" if not str(c).startswith("capture:") else c for c in getattr(args, "capture", [])]
            if args.cmd == "init"
            else None,
        )
        if args.cmd == "init":
            print(json.dumps({"state": "MODEL_ACTIVE" if model["revision"] else "MODEL_EMPTY", "model": model}, indent=2))
            return 0
        if args.cmd == "observe":
            caps = []
            for c in args.capture:
                caps.append(c if str(c).startswith("capture:") else f"capture:{c}")
            model = observe(
                model,
                entities=_parse_entities(args.entities_json),
                open_goals=args.goal,
                captures=caps,
                unknowns=args.unknown,
                note=args.note,
                replace_goals=args.replace_goals,
            )
            save_model(model)
            print(json.dumps({"state": "MODEL_ACTIVE", "revision": model["revision"], "entity_count": len(model["entities"])}, indent=2))
            return 0
        if args.cmd == "plan":
            print(json.dumps(plan_next(model), indent=2))
            return 0
        if args.cmd == "admit":
            print(json.dumps(
                admit_mutation(
                    model,
                    args.action,
                    targets=args.target,
                    expected_revision=args.expected_revision,
                ),
                indent=2,
            ))
            return 0
        if args.cmd == "attest-save-as":
            if not args.operator_confirmed:
                raise HouseStateError("SAVE_AS_REQUIRES_OPERATOR_CONFIRMATION")
            model = attest_save_as(
                model,
                alias=args.alias,
                capture_ref=args.capture_ref,
                operator_confirmed=True,
            )
            save_model(model)
            print(json.dumps({"state": "MODEL_ACTIVE", "save_as_attestation": model["save_as_attestation"]}, indent=2))
            return 0
        if args.cmd == "attest-library-save":
            if not args.operator_confirmed:
                raise HouseStateError("LIBRARY_SAVE_REQUIRES_OPERATOR_CONFIRMATION")
            model = attest_library_save(
                model,
                building_id=args.building_id,
                library_item_name=args.library_item_name,
                capture_ref=args.capture_ref,
                operator_confirmed=True,
            )
            save_model(model)
            print(json.dumps(
                {"state": "MODEL_ACTIVE", "library_checkpoint": model["library_checkpoint"]},
                indent=2,
            ))
            return 0
        if args.cmd == "checkpoint":
            print(json.dumps(persist_checkpoint(model, label=args.label), indent=2))
            return 0
        raise HouseStateError("UNKNOWN_COMMAND")
    except (HouseStateError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "HOUSE_STATE_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
