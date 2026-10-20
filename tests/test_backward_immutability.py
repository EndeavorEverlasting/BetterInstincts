import json
import tempfile
import unittest
from pathlib import Path
from scripts.check_backward_compat import check
from betterinstincts.compatibility import CompatibilityError

class ImmutabilityTests(unittest.TestCase):
    def test_certified_content_drift_rejected_even_if_catalog_row_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"compatibility/profiles").mkdir(parents=True)
            (root/"certifications").mkdir()
            row={"id":"old-verified","game_version":"1.111.2.1020","platform":"windows",
                 "module":"hunger","status":"certified","path":"compatibility/profiles/old-verified.json"}
            source=dict(row)
            source.update({"package_sha256":"a"*64,"tuning_source_sha256":"b"*64,"source_commit_sha":"c"*40,
                           "evidence_ref":"certifications/old-verified.json"})
            catalog={"schema":"betterinstincts.compatibility/v1","profiles":[row]}
            cert={"profile_id":"old-verified","status":"MAINTAINER_ACCEPTED","game_version":"1.111.2.1020","package_sha256":"a"*64,"source_commit_sha":"c"*40}
            (root/"compatibility/catalog.v1.json").write_text(json.dumps(catalog))
            (root/row["path"]).write_text(json.dumps(source))
            (root/"certifications/old-verified.json").write_text(json.dumps(cert))
            oldfiles={
                "compatibility/catalog.v1.json":json.dumps(catalog).encode(),
                row["path"]:json.dumps(source).encode(),
                "certifications/old-verified.json":json.dumps(cert).encode()
            }
            fake=lambda ref,path: oldfiles.get(path)
            self.assertEqual(check("test",root=root,old_reader=fake)["certified_preserved"],1)
            source["unreviewed_note"]="post-certification mutation"
            (root/row["path"]).write_text(json.dumps(source))
            with self.assertRaisesRegex(CompatibilityError,"CERTIFIED_PROFILE_CONTENT_CHANGED"):
                check("test",root=root,old_reader=fake)
    def test_previous_certification_evidence_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"compatibility/profiles").mkdir(parents=True)
            (root/"certifications").mkdir()
            row={"id":"v1","game_version":"1.111.2.1020","platform":"windows","module":"hunger",
                 "status":"certified","path":"compatibility/profiles/v1.json"}
            source=dict(row,package_sha256="a"*64,tuning_source_sha256="b"*64,source_commit_sha="c"*40,evidence_ref="certifications/v1.json")
            catalog={"schema":"betterinstincts.compatibility/v1","profiles":[row]}
            (root/"compatibility/catalog.v1.json").write_text(json.dumps(catalog))
            (root/row["path"]).write_text(json.dumps(source))
            (root/"certifications/v1.json").write_text(json.dumps({"profile_id":"v1","status":"MAINTAINER_ACCEPTED","game_version":"1.111.2.1020","package_sha256":"a"*64,"source_commit_sha":"c"*40}))
            data={p:(root/p).read_bytes() for p in ("compatibility/catalog.v1.json",row["path"],"certifications/v1.json")}
            (root/"certifications/v1.json").write_text(json.dumps({"profile_id":"v1","status":"MAINTAINER_ACCEPTED","game_version":"1.111.2.1020","package_sha256":"a"*64,"source_commit_sha":"c"*40,"changed":True}))
            with self.assertRaisesRegex(CompatibilityError,"CERTIFICATION_CONTENT_CHANGED"):
                check("test",root=root,old_reader=lambda ref,path:data.get(path))
if __name__=="__main__":
    unittest.main()
