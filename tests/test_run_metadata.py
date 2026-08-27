from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.append_history import append
from scripts.build_run_metadata import build, validate, write_checksums


class RunMetadataTests(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        out = root / "out"
        out.mkdir()
        (root / "METHODOLOGY.md").write_text("method 2.0.0\n")
        (root / "sites.txt").write_text("https://media.ye\n")
        (out / "govye-domains.txt").write_text(
            "one.gov.ye\ntwo.gov.ye\n"
        )
        (out / "targets.txt").write_text("https://one.gov.ye\n")
        (out / "govye-discovery.csv").write_text(
            "checked_at,host,selected_url,final_url,http_status,content_type,sources,error\n"
            "2026-08-27T00:00:00+00:00,one.gov.ye,https://one.gov.ye,https://one.gov.ye,200,text/html,inventory,\n"
            "2026-08-27T00:00:00+00:00,two.gov.ye,,,0,,inventory,dns\n"
        )
        warc = out / "one.warc.gz"
        warc.write_bytes(b"warc")
        (out / "manifest.csv").write_text(
            "captured_at,site,queued_pages,archive,result,wget_exit_code,bytes,discovery,response_records,revisit_records\n"
            f"20260827T000000Z,https://one.gov.ye,1,one.warc.gz,archived,0,{warc.stat().st_size},full,2,3\n"
        )
        (out / "site-status.csv").write_text(
            "checked_at,url,final_url,http_status,content_type,error\n"
        )
        return out

    def test_metadata_reconciles_targets_manifest_warcs_and_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            metadata = build(root, out, "a" * 40, "123")
            write_checksums(out)
            result = validate(root, out)
            self.assertTrue(result["metadata_ok"])
            self.assertEqual(metadata["coverage"]["candidates"], 2)
            self.assertEqual(metadata["coverage"]["unreachable_candidates"], 1)
            self.assertEqual(metadata["archive"]["response_records"], 2)
            self.assertEqual(metadata["archive"]["revisit_records"], 3)
            self.assertIn(
                "run-metadata.json",
                (out / "SHA256SUMS").read_text(),
            )

    def test_reconciliation_detects_target_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            build(root, out, "a" * 40, "123")
            write_checksums(out)
            (out / "targets.txt").write_text("https://changed.gov.ye\n")
            with self.assertRaises(ValueError):
                validate(root, out)

    def test_history_migration_marks_legacy_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            build(root, out, "a" * 40, "123")
            index = root / "index.csv"
            index.write_text(
                "release,completed_at,targets,warcs,observed_govye,reachable_govye,response_records,revisit_records\n"
                "archive-old,2026-01-01T00:00:00Z,1,1,2,1,2,3\n"
            )
            append(
                index,
                "archive-new",
                "2026-08-27T00:00:00Z",
                out / "run-metadata.json",
            )
            with index.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["metadata_version"], "legacy-unversioned")
            self.assertEqual(rows[1]["metadata_version"], "2.0.0")
            self.assertEqual(rows[1]["workflow_commit"], "a" * 40)


if __name__ == "__main__":
    unittest.main()
