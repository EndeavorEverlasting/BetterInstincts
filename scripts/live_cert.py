#!/usr/bin/env python3
"""Bounded, local-only Sims 4 experiment receipts. No game API, installation or scanning."""
import argparse
import json
import re
import sys
from pathlib import Path

from betterinstincts.compatibility import VERSION_RE, PLATFORMS, SHA_RE
from betterinstincts.live_eval import evaluate, validate_trial, EvidenceError

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist/live-cert"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
SCHEMA = "betterinstincts.live-cert/v1"
MAX_EVENTS = 150
MAX_BYTES = 200000

def run_root(run_id, output=OUTPUT):
    if not RUN_ID_RE.fullmatch(run_id):
        raise EvidenceError("INVALID_RUN_ID")
    base = output.resolve()
    path = output / run_id
    if not path.resolve().is_relative_to(base):
        raise EvidenceError("UNSAFE_RUN_PATH")
    return path

def load(run_id, output=OUTPUT):
    root = run_root(run_id,output)
    meta = json.loads((root / "run.json").read_text(encoding="utf-8"))
    if meta.get("schema") != SCHEMA or meta.get("run_id") != run_id:
        raise EvidenceError("BAD_RUN_MANIFEST")
    observations = (root / "observations.jsonl")
    if observations.stat().st_size > MAX_BYTES:
        raise EvidenceError("RUN_EVIDENCE_OVERSIZE")
    lines = observations.read_text(encoding="utf-8").splitlines()
    if len(lines) > MAX_EVENTS:
        raise EvidenceError("TOO_MANY_OBSERVATIONS")
    trials = [json.loads(line) for line in lines if line.strip()]
    for row in trials:
        validate_trial(row)
    return meta,trials

def init(run_id, game_version, platform, studio_build, output=OUTPUT):
    if not VERSION_RE.fullmatch(game_version) or platform not in PLATFORMS:
        raise EvidenceError("INVALID_VERSION_OR_PLATFORM")
    if not isinstance(studio_build, str) or not 1 <= len(studio_build) <= 80:
        raise EvidenceError("STUDIO_BUILD_REQUIRED")
    path=run_root(run_id,output)
    # Explicit scoped output only. No arbitrary path, user profile or game dir access.
    path.mkdir(parents=True, exist_ok=False)
    meta={"schema":SCHEMA, "run_id":run_id, "game_version":game_version, "platform":platform,
          "sims4studio_build":studio_build, "disposable_save_confirmed":False,
          "user_selected_mods_root_confirmed":False, "package_sha256":None,
          "tuning_source_sha256":None, "tuning_resource_id":None, "capture_ref":None}
    (path/"run.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    (path/"observations.jsonl").write_text("",encoding="utf-8")
    return path

def record(run_id, row, output=OUTPUT):
    meta, trials = load(run_id,output)
    validate_trial(row)
    if len(trials)>=MAX_EVENTS:
        raise EvidenceError("TOO_MANY_OBSERVATIONS")
    if any(t["stage"]==row["stage"] and t["trial"]==row["trial"] for t in trials):
        raise EvidenceError("DUPLICATE_TRIAL")
    line=json.dumps(row,sort_keys=True)+"\n"
    target=run_root(run_id,output)/"observations.jsonl"
    if target.stat().st_size+len(line.encode("utf-8"))>MAX_BYTES:
        raise EvidenceError("RUN_EVIDENCE_OVERSIZE")
    with target.open("a",encoding="utf-8") as sink:
        sink.write(line)
    return evaluate(meta,trials+[row])

def attest(run_id, package_sha256, tuning_source_sha256, tuning_resource_id, capture_ref,
           save_confirmed=False, mods_root_confirmed=False, output=OUTPUT):
    meta,trials=load(run_id,output)
    if not all(isinstance(x,str) and SHA_RE.fullmatch(x) for x in (package_sha256,tuning_source_sha256)):
        raise EvidenceError("INVALID_PROOF_HASH")
    if not 1<=len(tuning_resource_id)<=120 or not 3<=len(capture_ref)<=160:
        raise EvidenceError("MISSING_GAME_PROOF_POINTER")
    if not save_confirmed or not mods_root_confirmed:
        raise EvidenceError("REQUIRED_LOCAL_ATTESTATION_MISSING")
    meta.update({"package_sha256":package_sha256, "tuning_source_sha256":tuning_source_sha256,
                 "tuning_resource_id":tuning_resource_id, "capture_ref":capture_ref,
                 "disposable_save_confirmed":True, "user_selected_mods_root_confirmed":True})
    (run_root(run_id,output)/"run.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    return evaluate(meta,trials)

def status(run_id, output=OUTPUT, save_report=False):
    meta,trials=load(run_id,output)
    report=evaluate(meta,trials)
    report["run_id"]=run_id
    report["game_version"]=meta["game_version"]
    report["platform"]=meta["platform"]
    report["next_gate"]=(
        "REVIEW_CAPTURE_AND_COMMIT_PATCH_PROFILE" if report["state"]=="MEASUREMENTS_PASS_REVIEW_REQUIRED"
        else "RECORD_OR_REPAIR_HUNGER_GAMEPLAY_TRIALS")
    if save_report:
        path=run_root(run_id,output)/"report.json"
        path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    create=sub.add_parser("init")
    create.add_argument("--run-id",required=True)
    create.add_argument("--game-version",required=True)
    create.add_argument("--platform",required=True,choices=sorted(PLATFORMS))
    create.add_argument("--sims4studio-build",required=True)
    rec=sub.add_parser("record")
    rec.add_argument("--run-id",required=True)
    rec.add_argument("--stage",required=True,choices=("baseline","modified","rollback"))
    rec.add_argument("--trial",required=True,type=int)
    rec.add_argument("--seconds-to-eat",required=True,type=float)
    rec.add_argument("--min-hunger",required=True,type=float)
    rec.add_argument("--sim-lag-ms",required=True,type=float)
    rec.add_argument("--player-interruptions",required=True,type=int)
    rec.add_argument("--action-loops",required=True,type=int)
    rec.add_argument("--exceptions",required=True,type=int)
    rec.add_argument("--observation-ref",required=True)
    attach=sub.add_parser("attest")
    attach.add_argument("--run-id",required=True)
    attach.add_argument("--package-sha256",required=True)
    attach.add_argument("--tuning-source-sha256",required=True)
    attach.add_argument("--tuning-resource-id",required=True)
    attach.add_argument("--capture-ref",required=True)
    attach.add_argument("--disposable-save-confirmed",action="store_true")
    attach.add_argument("--user-selected-mods-root-confirmed",action="store_true")
    for name in ("status","evaluate"):
        sub.add_parser(name).add_argument("--run-id",required=True)
    args=p.parse_args(argv)
    try:
        if args.command=="init":
            result={"state":"RUN_INITIALIZED","run_dir":str(init(args.run_id,args.game_version,args.platform,args.sims4studio_build).relative_to(ROOT))}
        elif args.command=="record":
            row={"stage":args.stage,"trial":args.trial,"seconds_to_eat":args.seconds_to_eat,
                 "min_hunger":args.min_hunger,"sim_lag_ms":args.sim_lag_ms,
                 "player_interruptions":args.player_interruptions,"action_loops":args.action_loops,
                 "exceptions":args.exceptions,"observation_ref":args.observation_ref}
            result=record(args.run_id,row)
        elif args.command=="attest":
            result=attest(args.run_id,args.package_sha256,args.tuning_source_sha256,
                          args.tuning_resource_id,args.capture_ref,
                          args.disposable_save_confirmed,args.user_selected_mods_root_confirmed)
        else:
            result=status(args.run_id,save_report=args.command=="evaluate")
    except (EvidenceError,FileExistsError,FileNotFoundError,ValueError,OSError) as exc:
        print(json.dumps({"state":"BLOCKED","reason":str(exc)}))
        return 2
    print(json.dumps(result,sort_keys=True))
    # A recorded "pass" never becomes "game certified" solely via this tool.
    if args.command=="evaluate" and result.get("state")!="MEASUREMENTS_PASS_REVIEW_REQUIRED":
        return 3
    return 0

if __name__=="__main__":
    sys.exit(main())
