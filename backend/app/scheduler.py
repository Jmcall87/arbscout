from __future__ import annotations

import asyncio
from typing import Any

from . import db
from .models import AuditEntry
from .scanner import scan_once


async def run(app: Any) -> None:
    """Periodic scan loop. Failures are logged and the loop continues."""
    while True:
        interval = max(30, int(app.state.settings.scan_interval_seconds))
        await asyncio.sleep(interval)
        try:
            await scan_once(
                app.state.settings,
                app.state.venues,
                app.state.items,
                app.state.http,
                app.state.browser,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            db.append_audit(
                app.state.settings.db_path,
                AuditEntry(
                    event="scheduled_scan_failed",
                    detail=f"{type(exc).__name__}: {exc}",
                    mode=app.state.settings.mode,
                    allowed=False,
                ),
            )
