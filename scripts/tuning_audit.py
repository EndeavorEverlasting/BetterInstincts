#!/usr/bin/env python3
"""Read ONE explicitly provided XML tuning export; emit bounded metadata, never EA XML."""
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_BYTES = 2_000_000
MAX_ELEMENTS = 30_000
MAX_CANDIDATES = 25
HINTS = ("hunger", "autonomy", "score", "commodity", "motive", "need")

class TuningAuditError(ValueError):
    pass

def inspect(path):
    path=Path(path)
    if not path.is_file() or path.is_symlink():
        raise TuningAuditError("INPUT_MUST_BE_ONE_EXPLICIT_REGULAR_XML_FILE")
    if path.suffix.lower() != ".xml":
        raise TuningAuditError("INPUT_MUST_BE_XML")
    if path.stat().st_size > MAX_BYTES:
        raise TuningAuditError("INPUT_TOO_LARGE")
    content=path.read_bytes()
    if len(content)>MAX_BYTES or b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise TuningAuditError("UNSAFE_XML")
    try:
        root=ET.fromstring(content)
    except ET.ParseError as exc:
        raise TuningAuditError("INVALID_XML") from exc
    elements=list(root.iter())
    if len(elements)>MAX_ELEMENTS:
        raise TuningAuditError("TOO_MANY_XML_ELEMENTS")
    identity={key:str(root.attrib[key])[:120] for key in ("c","i","m","n","s") if key in root.attrib}
    found=[]
    for index,node in enumerate(elements):
        # Only short attribute labels and fingerprints, NOT raw game text or files.
        found_hints=[hint for hint in HINTS if hint in (node.tag+" "+str(node.attrib)).lower()]
        if found_hints:
            found.append({"node_index":index,"tag":str(node.tag)[:80],
                          "attributes":sorted(str(k)[:40] for k in node.attrib)[:12],
                          "hints":found_hints})
        if len(found)>=MAX_CANDIDATES:
            break
    return {"status":"EXTRACTED_METADATA_ONLY", "resource":identity, "sha256":hashlib.sha256(content).hexdigest(),
            "bytes":len(content),"elements":len(elements),"hunger_related_candidates":found,
            "proof_ceiling":"EXPORTED_XML_METADATA_NOT_GAMEPLAY_OR_VALID_PACKAGE"}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--xml",required=True,help="One explicit, user-selected exported tuning XML (read-only)")
    args=p.parse_args(argv)
    try:
        print(json.dumps(inspect(args.xml),sort_keys=True))
    except (TuningAuditError,OSError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)}))
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
