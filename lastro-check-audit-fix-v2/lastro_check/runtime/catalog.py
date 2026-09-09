from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain import OfferPolicy


class OfferCatalogError(ValueError):
    pass


def _require_bool(item: dict[str, Any], key: str, default: bool | None = None) -> bool:
    if key not in item:
        if default is None:
            raise OfferCatalogError(f"missing boolean field: {key}")
        return default
    value = item[key]
    if type(value) is not bool:
        raise OfferCatalogError(f"field {key} must be boolean")
    return value


def _require_positive_int(item: dict[str, Any], key: str) -> int:
    value = item.get(key)
    if type(value) is not int or value <= 0:
        raise OfferCatalogError(f"field {key} must be a positive integer")
    return value


def _require_text(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OfferCatalogError(f"field {key} must be non-empty text")
    return value.strip()


def load_offer_policies(path: str | Path) -> dict[str, OfferPolicy]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OfferCatalogError(f"offer catalog could not be read: {exc}") from exc
    if not isinstance(raw, dict):
        raise OfferCatalogError("offer catalog root must be an object")
    offers = raw.get("offers")
    if not isinstance(offers, list) or not offers:
        raise OfferCatalogError("offer catalog must contain a non-empty offers list")

    result: dict[str, OfferPolicy] = {}
    for item in offers:
        if not isinstance(item, dict):
            raise OfferCatalogError("each offer must be an object")
        policy = OfferPolicy(
            code=_require_text(item, "code"),
            amount_minor=_require_positive_int(item, "amount_minor"),
            currency=_require_text(item, "currency").upper(),
            product_code=_require_text(item, "product_code"),
            require_license_before_fulfillment=_require_bool(item, "require_license_before_fulfillment"),
            named_project_required=_require_bool(item, "named_project_required", True),
            require_license_expiry=_require_bool(item, "require_license_expiry", True),
        )
        if policy.code in result:
            raise OfferCatalogError(f"duplicate offer code: {policy.code}")
        result[policy.code] = policy
    return result
