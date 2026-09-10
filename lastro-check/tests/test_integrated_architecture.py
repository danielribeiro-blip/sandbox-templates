import ast
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "candidate" / "lastro"
if not ROOT.exists():
    ROOT = BASE / "lastro"


class ArchitectureTests(unittest.TestCase):
    def _imports(self, path: Path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append(node.module)
        return found

    def test_runtime_has_no_reconciliation_or_provenance_dependency(self):
        for path in (ROOT / "runtime").glob("*.py"):
            for imported in self._imports(path):
                self.assertNotIn("reconciliation", imported)
                self.assertNotIn("provenance", imported)
                self.assertNotIn("output_safety", imported)

    def test_reliability_layer_has_no_runtime_dependency(self):
        paths = [ROOT / "provenance.py", ROOT / "output_safety.py", ROOT / "reconciliation" / "matching_policy.py"]
        for path in paths:
            for imported in self._imports(path):
                self.assertNotIn("lastro.runtime", imported)

    def test_no_payment_sdk_imported(self):
        for path in ROOT.rglob("*.py"):
            imports = self._imports(path)
            self.assertFalse(any(name.startswith(("stripe", "paypal", "mercadopago")) for name in imports))


if __name__ == "__main__":
    unittest.main()
