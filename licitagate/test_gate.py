import copy
import unittest
from gate import evaluate, render, safe_cell


def fixture():
    return {"schema_version": "1.0", "case_id": "SYNTHETIC", "synthetic": True,
            "source_set_complete": True, "company_documents_reviewed": True,
            "review_approved": True, "reviewer": "Revisor demonstrativo", "reviewed_at": "2026-09-09",
            "requirements": [{"id": "R1", "requirement": "Capacidade", "source": "TR sintético",
            "locator": "item 1", "critical": True, "status": "CONFIRMADA", "compliance": "ATENDE",
            "evidence": "Atestado sintético item 2", "action": "Conferir vigência", "owner": "Operações", "due": "Antes do envio"}]}


class GateTests(unittest.TestCase):
    def test_complete_review_go(self):
        self.assertEqual(evaluate(fixture())["decision"], "GO")

    def test_each_missing_review_flag_blocks_go(self):
        for flag in ("source_set_complete", "company_documents_reviewed", "review_approved"):
            data = fixture(); data[flag] = False
            self.assertEqual(evaluate(data)["decision"], "PENDENTE")

    def test_critical_failure(self):
        data = fixture(); data["requirements"][0]["compliance"] = "NAO_ATENDE"
        self.assertEqual(evaluate(data)["decision"], "NO-GO")

    def test_unknown_condition(self):
        data = fixture(); data["requirements"][0].update(status="PENDENTE", compliance="DESCONHECIDO", evidence="")
        self.assertEqual(evaluate(data)["decision"], "GO CONDICIONAL")

    def test_no_empty_or_duplicate_matrix(self):
        for rows in ([], fixture()["requirements"] * 2):
            data = fixture(); data["requirements"] = rows
            with self.assertRaises(ValueError): evaluate(data)

    def test_strict_boolean(self):
        for value in ("true", 1, None):
            data = fixture(); data["source_set_complete"] = value
            with self.assertRaises(ValueError): evaluate(data)

    def test_claim_needs_evidence(self):
        data = fixture(); data["requirements"][0]["evidence"] = ""
        with self.assertRaises(ValueError): evaluate(data)

    def test_inference_cannot_confirm_compliance(self):
        data = fixture(); data["requirements"][0]["status"] = "INFERIDA"
        with self.assertRaises(ValueError): evaluate(data)

    def test_html_escape(self):
        data = fixture(); data["requirements"][0]["requirement"] = '<script>alert(1)</script>'
        self.assertNotIn('<script>', render(data)["report.html"])

    def test_csv_formula_neutralized(self):
        self.assertTrue(safe_cell(' =HYPERLINK("bad")').startswith("'"))

    def test_reproducible(self):
        self.assertEqual(render(fixture()), render(copy.deepcopy(fixture())))


if __name__ == "__main__": unittest.main()
