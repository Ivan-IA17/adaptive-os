"""
REST API server (aiohttp) — exposes orchestrator control over HTTP.
Binds to 127.0.0.1:7979 only (never externally accessible).

Endpoints:
  GET  /status          → orchestrator status + current profile
  POST /switch/{profile} → manual profile switch
  POST /ask             → conversational interface (body: {"question": "..."})
  GET  /profiles        → list available profiles
"""

from __future__ import annotations

import json
import logging

from aiohttp import web

from adaptive_os.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

KNOWN_PROFILES = ["work", "gaming", "creative", "server", "study"]


def build_app(orchestrator: Orchestrator) -> web.Application:
    app = web.Application()

    async def get_status(request: web.Request) -> web.Response:
        data = await orchestrator.status()
        return web.json_response(data)

    async def switch_profile(request: web.Request) -> web.Response:
        profile = request.match_info["profile"]
        if profile not in KNOWN_PROFILES:
            return web.json_response(
                {"error": f"Unknown profile '{profile}'. Available: {KNOWN_PROFILES}"},
                status=400,
            )
        result = await orchestrator.manual_switch(profile)
        return web.json_response(result)

    async def ask(request: web.Request) -> web.Response:
        try:
            body = await request.json()
            question = str(body.get("question", ""))
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        if not question.strip():
            return web.json_response({"error": "Question cannot be empty"}, status=400)

        result = await orchestrator.ask(question)
        return web.json_response(result)

    async def list_profiles(request: web.Request) -> web.Response:
        return web.json_response({"profiles": KNOWN_PROFILES})

    async def get_report(request: web.Request) -> web.Response:
        report = await orchestrator.weekly_report()
        return web.json_response({"report": report})

    app.router.add_get("/status", get_status)
    app.router.add_post("/switch/{profile}", switch_profile)
    app.router.add_post("/ask", ask)
    app.router.add_get("/profiles", list_profiles)
    app.router.add_get("/report", get_report)

    return app


async def start_server(orchestrator: Orchestrator, host: str = "127.0.0.1", port: int = 7979) -> None:
    app = build_app(orchestrator)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("API server listening on http://%s:%d", host, port)
