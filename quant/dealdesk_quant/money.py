"""Decimal money helpers. Floats never touch a price, cost, or margin."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, getcontext, InvalidOperation

getcontext().prec = 28

CENT = Decimal("0.01")
ZERO = Decimal("0")


def D(value) -> Decimal:
    """Parse a money or ratio value. Strings and ints only; floats are rejected."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("booleans are not numbers")
    if isinstance(value, float):
        raise TypeError("pass money as a string, not a float")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"not a decimal value: {value!r}") from exc


def ceil_cent(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_CEILING)


def round_cent(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def ratio(x: Decimal, places: int = 6) -> str:
    return str(x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def pct(x: Decimal, places: int = 2) -> str:
    return str((x * 100).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def money(x: Decimal) -> str:
    return str(round_cent(x))
