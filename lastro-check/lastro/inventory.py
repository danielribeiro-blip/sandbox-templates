from __future__ import annotations
import csv, hashlib, json, mimetypes
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from .output_safety import safe_untrusted_text_cell

@dataclass
class FileRecord:
    relative_path: str
    file_name: str
    extension: str
    mime_type: str
    size_bytes: int
    modified_utc: str
    sha256: str
    duplicate_group: str

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def build_inventory(root: str | Path) -> tuple[list[FileRecord], dict[str, object]]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")
    raw = []
    hash_paths: dict[str, list[str]] = defaultdict(list)
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("symlink in inventory input")
        if not p.is_file():
            continue
        digest = sha256_file(p)
        rel = p.relative_to(root).as_posix()
        stat = p.stat()
        mime, _ = mimetypes.guess_type(p.name)
        raw.append((p, rel, digest, stat, mime or "application/octet-stream"))
        hash_paths[digest].append(rel)
    group_by_hash = {}
    n = 1
    for digest, paths in hash_paths.items():
        if len(paths) > 1:
            group_by_hash[digest] = f"DUP-{n:04d}"
            n += 1
    records = [
        FileRecord(
            relative_path=rel,
            file_name=p.name,
            extension=p.suffix.lower(),
            mime_type=mime,
            size_bytes=stat.st_size,
            modified_utc=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            sha256=digest,
            duplicate_group=group_by_hash.get(digest, ""),
        )
        for p, rel, digest, stat, mime in raw
    ]
    summary = {
        "root": str(root),
        "files": len(records),
        "bytes": sum(r.size_bytes for r in records),
        "unique_hashes": len(hash_paths),
        "duplicate_groups": len(group_by_hash),
        "duplicate_files": sum(len(v) for h, v in hash_paths.items() if len(v) > 1),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return records, summary

def write_inventory(records: list[FileRecord], summary: dict[str, object], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(FileRecord.__annotations__.keys()))
        writer.writeheader()
        for r in records:
            writer.writerow({k: safe_untrusted_text_cell(v) if k in {"relative_path", "file_name", "extension", "mime_type"} else v for k, v in asdict(r).items()})
    with (out / "manifest.json").open("w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "files": [asdict(r) for r in records]}, fh, ensure_ascii=False, indent=2)
    dups = defaultdict(list)
    for r in records:
        if r.duplicate_group:
            dups[r.duplicate_group].append(r.relative_path)
    with (out / "duplicates.json").open("w", encoding="utf-8") as fh:
        json.dump(dups, fh, ensure_ascii=False, indent=2)
