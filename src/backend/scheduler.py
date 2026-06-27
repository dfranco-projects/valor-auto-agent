from __future__ import annotations

import asyncio
import logging

from valor_auto_agent import saved

log = logging.getLogger(__name__)


async def run_scheduler(interval_seconds: int = 60) -> None:
    """poll for due saved searches and run them; runs for the app's lifetime."""
    log.info("saved-search scheduler started (tick=%ds)", interval_seconds)
    while True:
        try:
            for sid in saved.due_saved():
                try:
                    alerts = await saved.run_saved(sid)
                    if alerts:
                        log.info("saved search %s -> %d new alerts", sid, len(alerts))
                except Exception as e:
                    log.warning("saved search %s run failed: %r", sid, e)
        except Exception as e:
            log.warning("scheduler tick failed: %r", e)
        await asyncio.sleep(interval_seconds)
