from pathlib import Path
import pytest
from lastro.money import money
from lastro.reconcile import read_csv,reconcile
from lastro.output_safety import safe_untrusted_text_cell
from scripts.build_distribution import stage_source
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('value',[None,'',' ','NaN','Infinity','-Infinity'])
def test_missing_or_nonfinite_money_never_becomes_zero(value):
    with pytest.raises(ValueError): money(value)

@pytest.mark.parametrize('text',['a,a\n1,2\n','a,b\n1\n','a,b\n1,2,3\n'])
def test_malformed_csv_is_rejected(tmp_path,text):
    p=tmp_path/'source.csv';p.write_text(text)
    with pytest.raises(ValueError):read_csv(p)

def test_no_false_ok_for_blank_amounts_or_repeated_sales():
    s,a,b=[read_csv(ROOT/'examples'/(n+'.csv')) for n in ('sales','acquirer','bank')]
    with pytest.raises(ValueError,match='duplicate sales'):
        reconcile(s+[s[0]],a,b)
    s[0]['gross_amount']=''
    with pytest.raises(ValueError,match='gross_amount is required'):
        reconcile(s,a,b)

def test_scope_authorities_travel_with_client_package(tmp_path):
    stage=tmp_path/'source';stage_source(ROOT,stage)
    assert (stage/'PRODUCT_SCOPE.md').read_bytes()==(ROOT/'PRODUCT_SCOPE.md').read_bytes()
    assert (stage/'docs/SCOPE_CONTRACT_v1.json').read_bytes()==(ROOT/'docs/SCOPE_CONTRACT_v1.json').read_bytes()

def test_formula_after_whitespace_is_neutralized():
    assert safe_untrusted_text_cell('  =1+1').startswith("'")
    assert money('0')==0
