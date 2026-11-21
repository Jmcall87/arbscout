from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

TRANSPARENT_AGENT = "ArbScoutResearch/1.0 (+market research agent)"


class BrowserSession:
    """
    Shared Playwright Chromium session for read-only public pages.

    This is deliberately transparent automation: it identifies itself in the
    user agent, honours robots.txt, and rate-limits per domain. It does not
    include stealth plugins, CAPTCHA solving, or fingerprint spoofing.
    """

    def __init__(self, user_agent: str = TRANSPARENT_AGENT) -> None:
        self.user_agent = user_agent
        self.available = False
        self.error = ""
        self._playwright: Any = None
        self._browser: Any = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}
        self._robots_cache: dict[str, Any] = {}

    async def start(self) -> None:
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox"],
            )
            self.available = True
            self.error = ""
        except Exception as exc:  # noqa: BLE001 - app must still serve the API
            self.error = f"{type(exc).__name__}: {exc}"
            self.available = False

    async def stop(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass

    async def new_page(self) -> tuple[Any, Any]:
        context = await self._browser.new_context(user_agent=self.user_agent)
        page = await context.new_page()
        return context, page

    async def acquire(self, domain: str, min_interval: float = 2.0) -> None:
        lock = self._locks.setdefault(domain, asyncio.Lock())
        async with lock:
            now = asyncio.get_running_loop().time()
            elapsed = now - self._last_request.get(domain, 0.0)
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            self._last_request[domain] = asyncio.get_running_loop().time()

    async def allowed(self, url: str, http: Any, user_agent: str | None = None) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots_cache:
            parser: Any = True
            try:
                response = await http.get(f"{origin}/robots.txt", timeout=5.0)
                if response.status_code == 200:
                    from urllib.robotparser import RobotFileParser

                    parsed_robots = RobotFileParser()
                    parsed_robots.parse(response.text.splitlines())
                    parser = parsed_robots
            except Exception:
                parser = True
            self._robots_cache[origin] = parser

        cached = self._robots_cache[origin]
        if cached is True:
            return True
        try:
            return bool(cached.can_fetch(user_agent or self.user_agent, url))
        except Exception:
            return False
