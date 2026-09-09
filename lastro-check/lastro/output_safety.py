from __future__ import annotations

import csv
import hashlib
import html
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def safe_untrusted_text_cell(value: Any) -> str:
    """Neutralize formula-like prefixes in untrusted textual fields only."""
    text = "" if value is None else str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def escape_html_text(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def write_safe_csv(
    path: Path,
    *,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
    untrusted_text_fields: Iterable[str],
) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames)
    field_set = set(fields)
    if len(field_set) != len(fields):
        raise ValueError("fieldnames must be unique")
    text_fields = set(untrusted_text_fields)
    unknown = text_fields.difference(field_set)
    if unknown:
        raise ValueError(f"unknown untrusted_text_fields: {sorted(unknown)}")

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            extra = set(row).difference(field_set)
            if extra:
                raise ValueError(f"unexpected fields in row: {sorted(extra)}")
            serialized = {}
            for field in fields:
                value = row.get(field, "")
                serialized[field] = (
                    safe_untrusted_text_cell(value) if field in text_fields else value
                )
            writer.writerow(serialized)
    return sha256_file(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sha256_manifest(paths: Iterable[Path], manifest_path: Path) -> None:
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {manifest_path}")
    items = []
    seen_names: set[str] = set()
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"artifact must be a regular non-symlink file: {path}")
        if path.name in seen_names:
            raise ValueError(f"duplicate artifact basename: {path.name}")
        seen_names.add(path.name)
        items.append((path.name, sha256_file(path)))
    items.sort()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in items),
        encoding="utf-8",
    )
