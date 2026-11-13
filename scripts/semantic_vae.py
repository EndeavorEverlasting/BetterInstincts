"""Local semantic VAE: explicit enroll/status/train; never monitors gameplay.

Usage:
  python -m scripts.semantic_vae enable --ack-local-data
  python -m scripts.semantic_vae status --snapshot selected-snapshot.json
  python -m scripts.semantic_vae train --snapshot S.json --event E.json --patch P.json
  python -m scripts.semantic_vae disable
  python -m scripts.semantic_vae status --profile named-local-profile

JSON observations must originate from separately admitted, verified adapters.
This CLI neither captures Sims UI nor starts a background job.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from betterinstincts.installation_profiles import (
    InstallationProfileError, set_toggle, view,
)
from betterinstincts.semantic_vae import (
    SemanticVAEError, load_local_model, record_if_enabled,
)

MAX_INPUT_BYTES = 64_000
SETTING = "learning.semantic_vae"


def _read(path: str) -> dict:
    source = Path(path)
    if (source.is_symlink() or not source.is_file()
            or source.stat().st_size > MAX_INPUT_BYTES):
        raise ValueError("UNSAFE_LOCAL_EVIDENCE_PATH")
    content = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("EVIDENCE_OBJECT_REQUIRED")
    return content


def run(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    enable = sub.add_parser("enable", help="Explicitly enroll active local profile")
    enable.add_argument("--ack-local-data", action="store_true",
                        help="Allow local verified semantic samples and learned weights")
    disable = sub.add_parser("disable", help="Stop future local training; preserve current local data")
    purge = sub.add_parser("purge", help="Delete only one exact local scope model and samples")
    purge.add_argument("--snapshot", required=True)
    purge.add_argument("--ack-delete-local-data", action="store_true")
    status = sub.add_parser("status", help="Inspect opted-in state or exact model")
    status.add_argument("--snapshot")
    train = sub.add_parser("train", help="One independently verified game sample")
    for k in ("snapshot", "event", "patch"):
        train.add_argument("--" + k, required=True)
    for command in (enable, purge, status, train):
        command.add_argument("--profile", help="Existing installation profile; defaults to active")
    disable.add_argument("--profile", help="Existing installation profile; defaults to active")
    opts = parser.parse_args(argv)
    # Validate an explicit profile before mutation or read. Inactive profiles
    # remain separately addressable without switching the active user profile.
    selected = view(profile_id=opts.profile)["profile_id"]
    if opts.command == "enable":
        if opts.ack_local_data is not True:
            raise ValueError("EXPLICIT_LOCAL_DATA_ACK_REQUIRED")
        set_toggle(SETTING, True, profile_id=selected)
        return {"state": "ENABLED", "profile": selected,
                "proof_ceiling": "LOCAL_CONSENT_ONLY_NOT_SENSOR_ACTIVATION"}
    if opts.command == "disable":
        set_toggle(SETTING, False, profile_id=selected)
        return {"state": "DISABLED_DATA_RETAINED", "profile": selected}
    if opts.command == "purge":
        if opts.ack_delete_local_data is not True:
            raise ValueError("EXPLICIT_DELETE_CONFIRM_REQUIRED")
        from betterinstincts.semantic_vae import purge_local_model
        return purge_local_model(_read(opts.snapshot), explicit_confirm=True,
                                 profile_id=selected)
    if opts.command == "status":
        state = view(profile_id=selected)
        answer = {"state": "ENABLED" if state["settings"][SETTING] else "DISABLED",
                  "profile": state["profile_id"], "capture_active": False,
                  "no_network": True}
        if opts.snapshot:
            model = load_local_model(_read(opts.snapshot), profile_id=selected)
            answer.update(trained=model["trained"], heldout=model["heldout"],
                          retained_examples=len(model["samples"]))
        return answer
    return record_if_enabled(_read(opts.snapshot), _read(opts.event),
                             _read(opts.patch), profile_id=selected)


def main() -> int:
    try:
        print(json.dumps(run(), sort_keys=True))
        return 0
    except (SemanticVAEError, InstallationProfileError, OSError,
            ValueError, KeyError, TypeError) as exc:
        print("SEMANTIC_VAE_BLOCKED: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
