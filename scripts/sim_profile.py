"""CLI for supplied active-Sim profile inspection (skills, preferences, traits, whims)."""
import argparse
import json
import sys

from betterinstincts.sim_profile import SimProfileError, evaluate_sim_profile, load_contract


def _csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _skills(raw: str) -> list:
    """Accept 'gardening' or 'gardening:3,cooking:2'."""
    out = []
    for part in _csv(raw):
        if ":" in part:
            name, level = part.rsplit(":", 1)
            out.append({"name": name.strip(), "level": int(level)})
        else:
            out.append(part)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sim-name", default=None)
    p.add_argument("--life-stage", default=None)
    p.add_argument("--traits", default="", help="Comma-separated Simology traits")
    p.add_argument("--aspiration", default=None)
    p.add_argument("--aspiration-track", default=None)
    p.add_argument("--skills", default="", help="gardening or gardening:3,cooking:1")
    p.add_argument("--likes", default="")
    p.add_argument("--dislikes", default="")
    p.add_argument("--whims", default="", help="Active whim/desire labels")
    p.add_argument("--emotion", default=None)
    p.add_argument("--moodlets", default="")
    p.add_argument("--needs-json", default=None)
    p.add_argument("--show-contract", action="store_true")
    p.add_argument("--show-discovery-map", action="store_true")
    args = p.parse_args(argv)
    try:
        cfg = load_contract()
        if args.show_contract:
            print(json.dumps(cfg, indent=2))
            return 0
        if args.show_discovery_map:
            print(json.dumps(cfg["player_discovery_map"], indent=2))
            return 0
        needs = json.loads(args.needs_json) if args.needs_json else None
        result = evaluate_sim_profile(
            sim_name=args.sim_name,
            life_stage=args.life_stage,
            traits=_csv(args.traits),
            aspiration=args.aspiration,
            aspiration_track=args.aspiration_track,
            skills=_skills(args.skills),
            likes=_csv(args.likes),
            dislikes=_csv(args.dislikes),
            whims=_csv(args.whims),
            emotion=args.emotion,
            moodlets=_csv(args.moodlets),
            needs=needs,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (SimProfileError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"state": "SIM_PROFILE_EVAL_FAILED_CLOSED", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
