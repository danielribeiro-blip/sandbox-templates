from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable

from .domain import ArtifactRef, OrderRecord, OrderState, utc_now_iso

RECEIPT_SCHEMA = "lastro.fulfillment.receipt.v2"
PROVENANCE_SCHEMA = "lastro.check.provenance.v1"
MINIMUM_SUPPORTED_ENGINE_VERSION = "0.1.1"
_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _release_tuple(value: str) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = _VERSION_RE.fullmatch(value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _supported_engine_version(value: str) -> bool:
    parsed = _release_tuple(value)
    minimum = _release_tuple(MINIMUM_SUPPORTED_ENGINE_VERSION)
    assert minimum is not None
    return parsed is not None and parsed >= minimum


def collect_artifacts(paths: Iterable[str | Path], *, base_dir: str | Path) -> list[ArtifactRef]:
    base = Path(base_dir).resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)
    artifacts: list[ArtifactRef] = []
    seen_paths: set[str] = set()
    for raw in paths:
        path = Path(raw)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"artifact must be a regular non-symlink file: {path}")
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(base)
        except ValueError as exc:
            raise ValueError(f"artifact is outside base_dir: {path}") from exc
        stored = relative.as_posix()
        if stored in seen_paths:
            raise ValueError(f"duplicate artifact path: {stored}")
        seen_paths.add(stored)
        artifacts.append(ArtifactRef(path=stored, sha256=sha256_file(resolved), size_bytes=resolved.stat().st_size))
    artifacts.sort(key=lambda item: item.path)
    return artifacts


def _valid_sha256(value: str) -> bool:
    if not isinstance(value, str):
        return False
    digest = value.strip().lower()
    return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)


def build_receipt(order: OrderRecord, artifacts: list[ArtifactRef], *, engine_version: str, engine_distribution_sha256: str, provenance_artifact_path: str) -> dict:
    if order.state is not OrderState.READY_FOR_FULFILLMENT:
        raise ValueError("order must be READY_FOR_FULFILLMENT before receipt generation")
    if not artifacts:
        raise ValueError("at least one fulfillment artifact is required")
    if not _supported_engine_version(engine_version):
        raise ValueError(f"engine_version must be >= {MINIMUM_SUPPORTED_ENGINE_VERSION} and use a supported release format")
    if not _valid_sha256(engine_distribution_sha256):
        raise ValueError("engine_distribution_sha256 must be a SHA-256 hex digest")
    artifact_map = {item.path: item for item in artifacts}
    provenance_ref = artifact_map.get(provenance_artifact_path)
    if provenance_ref is None:
        raise ValueError("provenance artifact must be included in delivered artifacts")
    return {
        "schema": RECEIPT_SCHEMA,
        "generated_at": utc_now_iso(),
        "assurance": {"integrity": "sha256", "authenticity": "unsigned", "non_repudiation": False},
        "order": {"order_id": order.order_id, "offer_code": order.offer_code, "product_code": order.product_code, "customer": order.customer, "project": order.project, "state": order.state.value},
        "engine": {"version": engine_version, "distribution_sha256": engine_distribution_sha256.lower()},
        "provenance": {"artifact_path": provenance_ref.path, "sha256": provenance_ref.sha256},
        "artifacts": [asdict(item) for item in artifacts],
    }


def write_receipt(receipt: dict, destination: str | Path) -> Path:
    target = Path(destination)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing fulfillment evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _safe_artifact_path(receipt_dir: Path, value: str) -> Path | None:
    if not isinstance(value, str) or not value or any(ord(ch) < 32 for ch in value):
        return None
    if "\\" in value:
        return None
    win = PureWindowsPath(value)
    posix = PurePosixPath(value)
    if win.is_absolute() or win.drive or win.root:
        return None
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        return None
    candidate = receipt_dir.joinpath(*posix.parts).resolve()
    try:
        candidate.relative_to(receipt_dir.resolve())
    except ValueError:
        return None
    return candidate


def _load_receipt(receipt_path: str | Path) -> tuple[Path, dict, list[str]]:
    receipt_file = Path(receipt_path)
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return receipt_file, {}, [f"receipt could not be read: {exc}"]
    if not isinstance(receipt, dict):
        return receipt_file, {}, ["receipt root must be an object"]
    return receipt_file, receipt, []


def _validate_provenance_manifest(path: Path, *, expected_engine_version: str, delivered_artifact_hashes: dict[str, str]) -> list[str]:
    errors: list[str] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"provenance manifest could not be read: {exc}"]
    if not isinstance(payload, dict):
        return ["provenance manifest root must be an object"]
    if payload.get("schema") != PROVENANCE_SCHEMA:
        errors.append("unsupported provenance schema")
    if payload.get("engine_version") != expected_engine_version:
        errors.append("provenance engine version mismatch")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("provenance manifest must contain at least one source")
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"invalid provenance source entry: {index}")
            continue
        for key in ("source_name", "locator", "adapter", "adapter_version"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                errors.append(f"invalid provenance source field {key}: {index}")
        if not _valid_sha256(source.get("source_sha256", "")):
            errors.append(f"invalid provenance source SHA-256: {index}")
        if source.get("identity_quality") not in {"SOURCE_PROVIDED", "SYNTHETIC", "ABSENT"}:
            errors.append(f"invalid provenance identity_quality: {index}")
    outputs = payload.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        errors.append("provenance manifest must contain at least one output")
        outputs = []
    seen_outputs: set[str] = set()
    for index, output in enumerate(outputs):
        if not isinstance(output, dict):
            errors.append(f"invalid provenance output entry: {index}")
            continue
        filename = output.get("file")
        digest = output.get("sha256")
        size = output.get("bytes")
        if not isinstance(filename, str) or not filename.strip() or "/" in filename or "\\" in filename:
            errors.append(f"invalid provenance output filename: {index}")
            continue
        if filename in seen_outputs:
            errors.append(f"duplicate provenance output filename: {filename}")
        seen_outputs.add(filename)
        if not _valid_sha256(digest):
            errors.append(f"invalid provenance output SHA-256: {filename}")
        if type(size) is not int or size < 0:
            errors.append(f"invalid provenance output size: {filename}")
        delivered_hash = delivered_artifact_hashes.get(filename)
        if delivered_hash is None:
            errors.append(f"provenance output is not a delivered artifact: {filename}")
        elif delivered_hash != digest:
            errors.append(f"provenance output hash mismatch: {filename}")
    return errors


def verify_receipt(receipt_path: str | Path) -> list[str]:
    receipt_file, receipt, errors = _load_receipt(receipt_path)
    if errors:
        return errors
    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("unsupported receipt schema")
    assurance = receipt.get("assurance") or {}
    if assurance.get("integrity") != "sha256":
        errors.append("unsupported receipt integrity assurance")
    if assurance.get("authenticity") != "unsigned" or assurance.get("non_repudiation") is not False:
        errors.append("receipt assurance claims exceed supported unsigned integrity model")
    order = receipt.get("order")
    if not isinstance(order, dict):
        errors.append("missing order block")
    else:
        for key in ("order_id", "offer_code", "product_code", "customer", "state"):
            if not str(order.get(key, "")).strip():
                errors.append(f"missing order claim: {key}")
        if order.get("state") != OrderState.READY_FOR_FULFILLMENT.value:
            errors.append("receipt order state must be ready_for_fulfillment")
    engine = receipt.get("engine") or {}
    engine_version = engine.get("version")
    if not isinstance(engine_version, str) or not engine_version.strip():
        errors.append("missing engine version")
        engine_version = ""
    elif not _supported_engine_version(engine_version):
        errors.append(f"engine version is below minimum supported release {MINIMUM_SUPPORTED_ENGINE_VERSION}")
    if not _valid_sha256(str(engine.get("distribution_sha256", ""))):
        errors.append("invalid engine distribution SHA-256")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("receipt must contain at least one artifact")
        artifacts = []
    seen: set[str] = set()
    artifact_hashes: dict[str, str] = {}
    artifact_paths: dict[str, Path] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            errors.append("invalid artifact entry")
            continue
        path_value = str(item.get("path", ""))
        if path_value in seen:
            errors.append(f"duplicate artifact path in receipt: {path_value}")
            continue
        seen.add(path_value)
        path = _safe_artifact_path(receipt_file.parent, path_value)
        if path is None:
            errors.append(f"unsafe artifact path: {path_value}")
            continue
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing or unsafe artifact: {path}")
            continue
        expected_hash = str(item.get("sha256", ""))
        if not _valid_sha256(expected_hash):
            errors.append(f"invalid artifact SHA-256: {path_value}")
            continue
        if type(item.get("size_bytes")) is not int or path.stat().st_size != item.get("size_bytes"):
            errors.append(f"size mismatch: {path}")
        actual = sha256_file(path)
        if actual != expected_hash:
            errors.append(f"hash mismatch: {path}")
        artifact_hashes[path_value] = expected_hash
        artifact_paths[path_value] = path
    provenance = receipt.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("missing provenance binding")
    else:
        provenance_path = str(provenance.get("artifact_path", ""))
        provenance_hash = str(provenance.get("sha256", ""))
        if not provenance_path or provenance_path not in artifact_hashes:
            errors.append("provenance artifact is not part of delivered artifacts")
        elif artifact_hashes[provenance_path] != provenance_hash:
            errors.append("provenance hash does not match delivered artifact")
        elif provenance_path in artifact_paths:
            errors.extend(_validate_provenance_manifest(artifact_paths[provenance_path], expected_engine_version=engine_version, delivered_artifact_hashes=artifact_hashes))
    return errors


def verify_receipt_for_order(receipt_path: str | Path, order: OrderRecord, *, expected_engine_version: str, expected_engine_distribution_sha256: str) -> list[str]:
    errors = verify_receipt(receipt_path)
    _, receipt, load_errors = _load_receipt(receipt_path)
    if load_errors:
        return list(dict.fromkeys([*errors, *load_errors]))
    if not _supported_engine_version(expected_engine_version):
        errors.append(f"expected engine version is below minimum supported release {MINIMUM_SUPPORTED_ENGINE_VERSION}")
    claims = receipt.get("order")
    if not isinstance(claims, dict):
        return list(dict.fromkeys([*errors, "missing order block"]))
    expected_claims = {"order_id": order.order_id, "offer_code": order.offer_code, "product_code": order.product_code, "customer": order.customer, "project": order.project, "state": OrderState.READY_FOR_FULFILLMENT.value}
    for key, expected in expected_claims.items():
        if claims.get(key) != expected:
            errors.append(f"receipt order claim mismatch: {key}")
    engine = receipt.get("engine") or {}
    if engine.get("version") != expected_engine_version:
        errors.append("engine version mismatch")
    expected_hash = expected_engine_distribution_sha256.lower()
    if not _valid_sha256(expected_hash) or engine.get("distribution_sha256") != expected_hash:
        errors.append("engine distribution SHA-256 mismatch")
    return list(dict.fromkeys(errors))
