from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")

def money(value: object) -> Decimal:
    if value is None:
        raise ValueError("monetary value is required")
    s = str(value).strip().replace("R$", "").replace(" ", "")
    if not s:
        raise ValueError("monetary value is required")
    # Accept 1.234,56 and 1234.56 without guessing incorrectly for simple values.
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        value_decimal = Decimal(s)
        if not value_decimal.is_finite():
            raise ValueError("monetary value must be finite")
        return value_decimal.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"invalid monetary value: {value!r}") from exc

def fmt(value: Decimal) -> str:
    return f"{value.quantize(CENT):.2f}"
