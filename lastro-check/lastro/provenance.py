from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping


class IdentityQuality(str, Enum):
    SOURCE_PROVIDED = "SOURCE_PROVIDED"
    SYNTHETIC = "SYNTHETIC"
    ABSENT = "ABSENT"


@dataclass(frozen=True, slots=True)
class SourceRef:
    source_name: str
    source_sha256: str
    locator: str
    adapter: str
    adapter_version: str
    identity_quality: IdentityQuality = IdentityQuality.SOURCE_PROVIDED

    def __post_init__(self) -> None:
        if (
            not self.source_name
            or "/" in self.source_name
            or "\\" in self.source_name
            or Path(self.source_name).name != self.source_name
        ):
            raise ValueError("source_name must be a basename, not a path")
        if any(ord(char) < 32 for char in self.locator) or len(self.locator) > 512:
            raise ValueError("locator contains control characters or is too long")
        digest = self.source_sha256.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("source_sha256 must be a SHA-256 hex digest")
        if not self.locator.strip():
            raise ValueError("locator must identify a record, row, page, or source region")
        if not self.adapter.strip() or not self.adapter_version.strip():
            raise ValueError("adapter and adapter_version are required")


def sha256_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("source must be a regular non-symlink file")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_ref_for_file(
    path: Path,
    *,
    locator: str,
    adapter: str,
    adapter_version: str,
    identity_quality: IdentityQuality = IdentityQuality.SOURCE_PROVIDED,
) -> SourceRef:
    return SourceRef(
        source_name=path.name,
        source_sha256=sha256_file(path),
        locator=locator,
        adapter=adapter,
        adapter_version=adapter_version,
        identity_quality=identity_quality,
    )


def attach_source_ref(record: Mapping[str, Any], source_ref: SourceRef) -> dict[str, Any]:
    out = dict(record)
    out["source_ref"] = {
        **asdict(source_ref),
        "identity_quality": source_ref.identity_quality.value,
    }
    return out


def provenance_manifest(
    *,
    engine_version: str,
    sources: Iterable[SourceRef],
    outputs: Iterable[Path],
) -> dict[str, Any]:
    if not engine_version.strip():
        raise ValueError("engine_version is required")

    source_rows = [
        {**asdict(source), "identity_quality": source.identity_quality.value}
        for source in sources
    ]
    source_rows.sort(key=lambda row: (row["source_name"], row["locator"], row["adapter"]))

    output_rows = []
    seen_names: set[str] = set()
    for path in outputs:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"output must be a regular non-symlink file: {path}")
        if path.name in seen_names:
            raise ValueError(f"duplicate output basename in provenance manifest: {path.name}")
        seen_names.add(path.name)
        output_rows.append(
            {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        )
    output_rows.sort(key=lambda row: row["file"])

    return {
        "schema": "lastro.check.provenance.v1",
        "engine_version": engine_version,
        "sources": source_rows,
        "outputs": output_rows,
    }


def write_provenance_manifest(manifest: Mapping[str, Any], path: Path) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    return sha256_file(path)
