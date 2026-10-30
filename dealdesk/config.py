"""Runtime configuration from environment variables (and an optional local .env)."""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DIR = ROOT / "data" / "synthetic"
POLICY_DOC = ROOT / "docs" / "pricing-policy.md"

SCRIPTED = "scripted"
LOCAL_MODEL = "local_model"
DEFAULT_DEMO_DATE = "2026-10-25"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal KEY=VALUE loader; real environment variables take precedence."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_local_endpoint(url: str, extra_hosts: tuple[str, ...] = ()) -> bool:
    """Allow loopback, private-network, .local, or explicitly listed hosts only."""
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local") or host in extra_hosts:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    mode: str = SCRIPTED
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 60.0
    llm_allowed_hosts: tuple[str, ...] = ()
    demo_date: str = DEFAULT_DEMO_DATE
    watch_interval_seconds: float = 5.0
    state_dir: Path = field(default_factory=lambda: ROOT / "data" / "runtime")

    def validate_demo_boundary(self) -> None:
        try:
            loopback = self.host == "localhost" or ipaddress.ip_address(self.host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ValueError("DEALDESK_HOST must be a loopback address or localhost; this demo has no authentication.")
        if not 1 <= self.llm_timeout_seconds <= 60:
            raise ValueError("DEALDESK_LLM_TIMEOUT_SECONDS must be between 1 and 60.")

    @property
    def incoming_feed_dir(self) -> Path:
        return self.state_dir / "incoming_feeds"

    @property
    def db_path(self) -> Path:
        return self.state_dir / "dealdesk.sqlite3"

    def today(self) -> date:
        """Injected demo clock: a fixed synthetic date unless DEALDESK_DEMO_DATE=system."""
        return date.today() if self.demo_date == "system" else date.fromisoformat(self.demo_date)

    def llm_endpoint_error(self) -> str | None:
        if self.mode != LOCAL_MODEL:
            return None
        if not self.llm_model:
            return "DEALDESK_LLM_MODEL is not set."
        if not is_local_endpoint(self.llm_base_url, self.llm_allowed_hosts):
            return ("DEALDESK_LLM_BASE_URL is not a local or private-network host; "
                    "cloud endpoints are refused. Add a LAN host to DEALDESK_LLM_ALLOWED_HOSTS if needed.")
        return None


def get_settings() -> Settings:
    load_dotenv()
    env = os.environ
    mode = env.get("DEALDESK_MODE", SCRIPTED).strip().lower()
    if mode not in (SCRIPTED, LOCAL_MODEL):
        raise ValueError(f"DEALDESK_MODE must be '{SCRIPTED}' or '{LOCAL_MODEL}', not {mode!r}")
    state_dir = env.get("DEALDESK_STATE_DIR")
    return Settings(
        host=env.get("DEALDESK_HOST", "127.0.0.1"),
        port=int(env.get("DEALDESK_PORT", "8000")),
        mode=mode,
        llm_base_url=env.get("DEALDESK_LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/"),
        llm_model=env.get("DEALDESK_LLM_MODEL", ""),
        llm_api_key=env.get("DEALDESK_LLM_API_KEY", ""),
        llm_timeout_seconds=float(env.get("DEALDESK_LLM_TIMEOUT_SECONDS", "60")),
        llm_allowed_hosts=tuple(h.strip().lower() for h in env.get("DEALDESK_LLM_ALLOWED_HOSTS", "").split(",")
                                if h.strip()),
        demo_date=env.get("DEALDESK_DEMO_DATE", DEFAULT_DEMO_DATE),
        watch_interval_seconds=float(env.get("DEALDESK_WATCH_INTERVAL_SECONDS", "5")),
        state_dir=Path(state_dir) if state_dir else ROOT / "data" / "runtime",
    )
