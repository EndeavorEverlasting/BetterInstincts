#!/usr/bin/env python3
"""Offline exact game-version compatibility query; no game directory access."""
import argparse
import json
import sys
from pathlib import Path
from betterinstincts.compatibility import load_catalog, select_profile, CompatibilityError, PLATFORMS, MODULES

ROOT=Path(__file__).resolve().parents[1]

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--game-version",required=True)
    p.add_argument("--platform",required=True,choices=sorted(PLATFORMS))
    p.add_argument("--module",required=True,choices=sorted(MODULES))
    p.add_argument("--profile-id")
    args=p.parse_args(argv)
    try:
        doc=load_catalog(ROOT)
        result=select_profile(doc,args.game_version,args.platform,args.module,args.profile_id)
    except (CompatibilityError,OSError,ValueError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)}))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="SELECTED" else 3

if __name__=="__main__":
    sys.exit(main())
