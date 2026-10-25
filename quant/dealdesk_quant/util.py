import hashlib
import json
import re
from pathlib import Path

from .errors import QuantError

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def load_json(path) -> dict:
    return json.loads(Path(path).read_text())


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj).encode()).hexdigest()[:16]


def file_hash(path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def check_month(value, field) -> str:
    if not isinstance(value, str) or not MONTH_RE.match(value):
        raise QuantError("INVALID_MONTH", f"{field} must be YYYY-MM, got {value!r}", field)
    return value


def check_date(value, field) -> str:
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise QuantError("INVALID_DATE", f"{field} must be YYYY-MM-DD, got {value!r}", field)
    return value


def month_index(m: str) -> int:
    y, mo = m.split("-")
    return int(y) * 12 + int(mo) - 1


def index_month(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def add_months(m: str, n: int) -> str:
    return index_month(month_index(m) + n)


def days_between(d1: str, d2: str) -> int:
    from datetime import date
    a = date.fromisoformat(d1)
    b = date.fromisoformat(d2)
    return (b - a).days
