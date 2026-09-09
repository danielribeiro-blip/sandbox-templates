from __future__ import annotations
import html, json
from pathlib import Path

def reconciliation_html(summary: dict[str, object], output_path: str | Path) -> None:
    counts = summary.get("exception_counts", {})
    rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{v}</td></tr>" for k, v in sorted(counts.items()))
    doc = f'''<!doctype html><meta charset="utf-8"><title>Lastro Check Report</title>
<style>body{{font-family:system-ui;margin:40px;max-width:900px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;text-align:left}}.k{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.c{{border:1px solid #ddd;padding:16px;border-radius:12px}}small{{color:#666}}</style>
<h1>Lastro Check — reconciliation summary</h1>
<div class="k"><div class="c"><b>Transactions</b><br>{summary.get('transactions')}</div><div class="c"><b>OK</b><br>{summary.get('ok')}</div><div class="c"><b>Exceptions</b><br>{summary.get('exceptions')}</div></div>
<h2>Financial exposure</h2><p>Potential gap: <b>{html.escape(str(summary.get('potential_financial_gap')))}</b></p>
<p>Unmatched bank entries: <b>{summary.get('unmatched_bank_entries')}</b> · total <b>{html.escape(str(summary.get('unmatched_bank_total')))}</b></p>
<h2>Exception taxonomy</h2><table><thead><tr><th>Exception</th><th>Count</th></tr></thead><tbody>{rows or '<tr><td colspan="2">None</td></tr>'}</tbody></table>
<p><small>This report is an operational reconciliation artifact. It does not replace accounting, audit or legal review.</small></p>'''
    Path(output_path).write_text(doc, encoding="utf-8")
