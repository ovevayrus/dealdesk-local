"""FastAPI app: chatbot UI, chat API, demo actions, and direct tool endpoints.

Single-user demonstration on synthetic data; binds to 127.0.0.1 by default.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, llm
from .agent import Agent
from .boundary import LocalDemoBoundary
from .config import LOCAL_MODEL, Settings, get_settings
from .costs import REFERENCE_QUOTE_ID
from .state import Store
from .tools import TOOL_NAMES, DemoTools, run_tool

STATIC_DIR = Path(__file__).resolve().parent / "static"
log = logging.getLogger("dealdesk")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ToolRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_demo_boundary()
    store = Store(settings.db_path)
    tools = DemoTools(settings, store)
    agent = Agent(settings, tools)

    async def watch_feeds() -> None:
        while True:
            await asyncio.sleep(settings.watch_interval_seconds)
            try:
                for result in await asyncio.to_thread(tools.poll_incoming_feeds):
                    store.add_message("event", {"kind": "cost_update", "cost_update": result})
                    log.info("Scheduled watcher applied %s", result["feed"]["feed_version"])
            except Exception:  # Keep the demo watcher alive; the error is visible in the server log.
                log.exception("Scheduled feed watcher failed")

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(watch_feeds()) if settings.watch_interval_seconds > 0 else None
        yield
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="DealDesk Local (synthetic demo)", version=__version__, lifespan=lifespan)
    app.add_middleware(LocalDemoBoundary, host=settings.host)
    app.state.settings, app.state.store, app.state.tools, app.state.agent = settings, store, tools, agent

    def status() -> dict[str, Any]:
        feed = tools.active_feed()
        return {
            "app": "DealDesk Local",
            "version": __version__,
            "synthetic_data": True,
            "single_user_demo": True,
            "mode": settings.mode,
            "mode_label": ("Local model endpoint" if settings.mode == LOCAL_MODEL else "Scripted demo mode"),
            "model": settings.llm_model or None,
            "model_endpoint": settings.llm_base_url if settings.mode == LOCAL_MODEL else None,
            "model_status": llm.model_status(settings),
            "demo_date": settings.today().isoformat(),
            "active_feed": {k: feed.get(k) for k in ("feed_version", "as_of_date", "stress_scenario")},
            "watcher": {"enabled": settings.watch_interval_seconds > 0,
                        "interval_seconds": settings.watch_interval_seconds,
                        "folder": str(settings.incoming_feed_dir)},
            "external_agent": {
                "skill": "openclaw/skills/dealdesk-local/SKILL.md",
                "tool_calls_observed": store.get("external_tool_calls", 0),
                "last_caller": store.get("external_last_caller"),
                "verified_on_device": False,
            },
        }

    def snapshot() -> dict[str, Any]:
        return {
            "status": status(),
            "messages": store.messages(),
            "quote_versions": store.quote_versions(REFERENCE_QUOTE_ID),
            "review_events": store.review_events(),
        }

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return status()

    @app.get("/api/state")
    def get_state() -> dict[str, Any]:
        return snapshot()

    @app.post("/api/chat")
    def post_chat(request: ChatRequest) -> dict[str, Any]:
        text = request.message.strip()
        if not text:
            raise HTTPException(status_code=422, detail="Message is empty.")
        store.add_message("user", {"text": text})
        reply = agent.respond(text)
        store.add_message("assistant", reply)
        return {"reply": reply, "state": snapshot()}

    @app.post("/api/cost-update")
    def post_cost_update() -> dict[str, Any]:
        result = tools.apply_demo_cost_update()
        store.add_message("event", {"kind": "cost_update", "cost_update": result})
        return {"result": result, "state": snapshot()}

    @app.post("/api/reset")
    def post_reset() -> dict[str, Any]:
        tools.reset()
        return snapshot()

    @app.get("/api/documents/{doc_id}")
    def get_document(doc_id: str) -> dict[str, Any]:
        from .documents import get_document as load

        document = load(doc_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Unknown document.")
        return document

    @app.post("/api/tools/{name}")
    def call_tool(name: str, request: ToolRequest,
                  x_dealdesk_caller: str | None = Header(default=None)) -> dict[str, Any]:
        """Named, validated tools for a local agent runtime (e.g. an OpenClaw skill); no shell or network tools."""
        if name not in TOOL_NAMES:
            raise HTTPException(status_code=404, detail=f"Unknown tool. Available: {sorted(TOOL_NAMES)}")
        caller = re.sub(r"[^a-z0-9_-]", "", (x_dealdesk_caller or "external-agent").lower())[:32] or "external-agent"
        try:
            return run_tool(tools, store, name, request.arguments, caller)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def main() -> None:
    import uvicorn

    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    print(f"DealDesk Local (synthetic, single-user demo) on http://{settings.host}:{settings.port}  "
          f"mode={settings.mode}")
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
