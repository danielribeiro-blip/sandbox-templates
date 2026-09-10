import csv
import tempfile
import unittest
from pathlib import Path

from lastro.output_safety import escape_html_text, safe_untrusted_text_cell, write_safe_csv, write_sha256_manifest
from lastro.provenance import IdentityQuality, attach_source_ref, provenance_manifest, source_ref_for_file, write_provenance_manifest


class ProvenanceOutputTests(unittest.TestCase):
    def test_source_hash_and_locator_survive_without_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.csv"
            source.write_text("id,value\n1,2\n", encoding="utf-8")
            ref = source_ref_for_file(source, locator="row:2", adapter="csv", adapter_version="1", identity_quality=IdentityQuality.SOURCE_PROVIDED)
            self.assertEqual(ref.source_name, "input.csv")
            self.assertEqual(len(ref.source_sha256), 64)
            self.assertEqual(ref.locator, "row:2")
            attached = attach_source_ref({"event_id": "1"}, ref)
            self.assertEqual(attached["source_ref"]["source_name"], "input.csv")

    def test_provenance_manifest_links_sources_outputs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            output = root / "result.json"
            source.write_text("a", encoding="utf-8")
            output.write_text("{}", encoding="utf-8")
            ref = source_ref_for_file(source, locator="row:1", adapter="csv", adapter_version="1")
            manifest = provenance_manifest(engine_version="0.1.1", sources=[ref], outputs=[output])
            self.assertEqual(manifest["sources"][0]["source_name"], "input.csv")
            self.assertEqual(manifest["outputs"][0]["file"], "result.json")
            path = root / "provenance.json"
            digest = write_provenance_manifest(manifest, path)
            self.assertEqual(len(digest), 64)
            with self.assertRaises(FileExistsError):
                write_provenance_manifest(manifest, path)

    def test_csv_formula_neutralization_is_field_aware_and_schema_strict(self):
        self.assertEqual(safe_untrusted_text_cell("=1+1"), "'=1+1")
        self.assertEqual(safe_untrusted_text_cell("plain"), "plain")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            write_safe_csv(
                path,
                fieldnames=["memo", "amount"],
                rows=[{"memo": "=SUM(A1:A2)", "amount": -10.5}],
                untrusted_text_fields=["memo"],
            )
            with path.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))
            self.assertTrue(row["memo"].startswith("'="))
            self.assertEqual(row["amount"], "-10.5")
            bad = Path(tmp) / "bad.csv"
            with self.assertRaises(ValueError):
                write_safe_csv(bad, fieldnames=["a"], rows=[{"a": 1, "b": 2}], untrusted_text_fields=[])

    def test_html_is_escaped(self):
        self.assertEqual(escape_html_text('<img src=x onerror="x">'), '&lt;img src=x onerror=&quot;x&quot;&gt;')

    def test_sha_manifest_refuses_duplicate_names_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a" / "x.txt"
            b = root / "b" / "x.txt"
            a.parent.mkdir(); b.parent.mkdir()
            a.write_text("a", encoding="utf-8"); b.write_text("b", encoding="utf-8")
            with self.assertRaises(ValueError):
                write_sha256_manifest([a, b], root / "hashes.txt")
            write_sha256_manifest([a], root / "hashes.txt")
            with self.assertRaises(FileExistsError):
                write_sha256_manifest([a], root / "hashes.txt")


if __name__ == "__main__":
    unittest.main()
