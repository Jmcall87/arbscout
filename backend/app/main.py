from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import db, scheduler
from .browser.session import BrowserSession
from .config import Settings
from .router import router
from .venues.registry import load_items, load_venues


@asynccontextmanager
async def lifespan(app: FastAPI):
    base = Settings.from_env()
    db.init_db(base.db_path)
    settings = base.apply_overrides(db.get_settings(base.db_path))

    venues = load_venues()
    items = load_items()
    http = httpx.AsyncClient(follow_redirects=True, timeout=15.0)
    browser = BrowserSession()
    await browser.start()

    app.state.settings = settings
    app.state.venues = venues
    app.state.items = items
    app.state.http = http
    app.state.browser = browser
    app.state.last_scan = None

    task = asyncio.create_task(scheduler.run(app))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await browser.stop()
        await http.aclose()


app = FastAPI(title="ArbScout", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


web_dir = os.getenv("ARBSCOUT_WEB_DIR", "/app/web")
app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
