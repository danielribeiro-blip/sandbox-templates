"""Render a reviewed evidence matrix; never infer legal compliance from documents."""
import argparse
import csv
import hashlib
import html
import io
import json
from pathlib import Path


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: texto obrigatório")
    return value


def evaluate(data):
    if data.get("schema_version") != "1.0":
        raise ValueError("schema_version deve ser 1.0")
    required_text(data.get("case_id"), "case_id")
    for flag in ("synthetic", "source_set_complete", "company_documents_reviewed", "review_approved"):
        if type(data.get(flag)) is not bool:
            raise ValueError(f"{flag}: boolean obrigatório")
    rows = data.get("requirements")
    if not isinstance(rows, list) or not rows:
        raise ValueError("requirements: matriz não pode estar vazia")
    seen = set()
    for row in rows:
        for field in ("id", "requirement", "source", "locator", "action", "owner", "due"):
            required_text(row.get(field), field)
        if row["id"] in seen:
            raise ValueError("id duplicado")
        seen.add(row["id"])
        if type(row.get("critical")) is not bool:
            raise ValueError("critical: boolean obrigatório")
        if row.get("status") not in {"CONFIRMADA", "PENDENTE", "CONTROVERTIDA", "INFERIDA"}:
            raise ValueError("status inválido")
        if row.get("compliance") not in {"ATENDE", "NAO_ATENDE", "DESCONHECIDO"}:
            raise ValueError("compliance inválido")
        if row["compliance"] != "DESCONHECIDO":
            if row["status"] != "CONFIRMADA":
                raise ValueError("conclusão de atendimento exige fonte CONFIRMADA")
            required_text(row.get("evidence"), "evidence")
    gaps = [r["id"] for r in rows if r["status"] != "CONFIRMADA" or r["compliance"] != "ATENDE"]
    blockers = [r["id"] for r in rows if r["critical"] and r["status"] == "CONFIRMADA" and r["compliance"] == "NAO_ATENDE"]
    incomplete = not all(data[f] for f in ("source_set_complete", "company_documents_reviewed", "review_approved"))
    if data["review_approved"]:
        required_text(data.get("reviewer"), "reviewer")
        required_text(data.get("reviewed_at"), "reviewed_at")
    # Incomplete review cannot masquerade as a final positive or negative decision.
    decision = "PENDENTE" if incomplete else "NO-GO" if blockers else "GO CONDICIONAL" if gaps else "GO"
    return {"case_id": data["case_id"], "decision": decision, "synthetic": data["synthetic"],
            "blockers": blockers, "pending_actions": gaps, "requirements": rows,
            "limitation": "Resultado condicionado à matriz e revisão declaradas. Não valida autenticidade, completude ou habilitação por si só."}


def safe_cell(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


def render(data):
    result = evaluate(data)
    fields = ("id", "requirement", "source", "locator", "status", "compliance", "evidence", "action", "owner", "due")
    csv_output = io.StringIO(newline="")
    writer = csv.writer(csv_output)
    writer.writerow(fields)
    writer.writerows([safe_cell(row.get(f, "")) for f in fields] for row in result["requirements"])
    esc = lambda text: html.escape(str(text), quote=True)
    table = "".join("<tr>" + "".join(f"<td>{esc(row.get(f, ''))}</td>" for f in fields) + "</tr>" for row in result["requirements"])
    label = "DEMONSTRAÇÃO SINTÉTICA — " if result["synthetic"] else ""
    page = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LicitaGate — {esc(result['case_id'])}</title>
<style>body{{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 20px;color:#15263b}}h1{{font-size:32px}}.decision{{background:#edf2f7;padding:20px;border-left:5px solid #176b67}}table{{border-collapse:collapse;font-size:13px;width:100%}}td,th{{border:1px solid #ccd4dd;padding:10px;text-align:left;vertical-align:top}}.scroll{{overflow:auto}}@media print{{body{{margin:0}}table{{font-size:9px}}}}</style>
<h1>LicitaGate</h1><p>{label}{esc(result['case_id'])}</p>
<div class="decision"><strong>{result['decision']}</strong><p>Impedimentos confirmados: {esc(', '.join(result['blockers']) or 'nenhum registrado')}. Ações pendentes: {len(result['pending_actions'])}.</p></div>
<p>{esc(result['limitation'])}</p><div class="scroll"><table><thead><tr>{''.join('<th>'+f+'</th>' for f in fields)}</tr></thead><tbody>{table}</tbody></table></div>
<p>Fonte e localizador permitem conferir cada item. O responsável indicado deve resolver as pendências antes da decisão externa.</p></html>'''
    return {"decision.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            "matrix.csv": csv_output.getvalue(), "report.html": page}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="Diretório novo; nunca sobrescreve uma entrega")
    args = parser.parse_args()
    raw = args.input.read_bytes()
    data = json.loads(raw)
    outputs = render(data)
    # Evaluate before writing; exclusive directory creation preserves prior evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, content in outputs.items():
        payload = content.encode("utf-8")
        (args.output / name).write_bytes(payload)
        hashes[name] = hashlib.sha256(payload).hexdigest()
    (args.output / "provenance.json").write_text(json.dumps({
        "schema_version": "1.0", "input_sha256": hashlib.sha256(raw).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs": hashes, "note": "Hashes verificam bytes; não certificam veracidade ou identidade."}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"decision": evaluate(data)["decision"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
