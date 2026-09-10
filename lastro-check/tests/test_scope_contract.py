from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scope_contract_preserves_domain_agnostic_product_identity():
    payload = json.loads((ROOT / "docs" / "SCOPE_CONTRACT_v1.json").read_text(encoding="utf-8"))

    assert payload["schema"] == "lastro.scope.contract.v1"
    assert payload["lastro"]["definition"] == "independent verification and evidence infrastructure"
    assert payload["lastro_check"]["definition"] == "domain-agnostic verification mechanism"

    verifier_codes = {item["code"] for item in payload["current_implementation"]["implemented_verifiers"]}
    assert verifier_codes == {"receivables", "documents"}

    assert payload["baseline"]["role"] == "executable_compatibility_baseline_not_product_scope_definition"
    assert "LASTRO == receivables reconciliation" in payload["governance"]["forbid_scope_narrowing"]
    assert "Lastro Check == receivables reconciliation + document inventory" in payload["governance"]["forbid_scope_narrowing"]


def test_scope_contract_keeps_four_product_level_verdicts():
    payload = json.loads((ROOT / "docs" / "SCOPE_CONTRACT_v1.json").read_text(encoding="utf-8"))
    assert payload["lastro_check"]["verification_contract"]["product_level_verdicts"] == [
        "CONFIRMED",
        "DIVERGENT",
        "AMBIGUOUS",
        "NOT_PROVABLE",
    ]


def test_scope_reading_order_puts_constitution_before_implementation_docs():
    payload = json.loads((ROOT / "docs" / "SCOPE_CONTRACT_v1.json").read_text(encoding="utf-8"))
    order = payload["repository_reading_order"]
    assert order[0] == "lastro-check/PRODUCT_SCOPE.md"
    assert order[1] == "lastro-check/docs/SCOPE_CONTRACT_v1.json"
