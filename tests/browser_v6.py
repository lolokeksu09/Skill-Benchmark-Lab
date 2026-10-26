"""Two high-signal real-Chromium checks for the V6 candidate contract."""
import asyncio
import os
import pathlib
import socket
import subprocess
import time
import unittest
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


class V6BrowserChecks(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen(
            ["node", "src/server.mjs"], cwd=ROOT,
            env={**os.environ, "PORT": str(self.port)},
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("V6 fixture server exited during setup")
            try:
                import urllib.request
                with urllib.request.urlopen(self.base, timeout=.25) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(.1)
        raise RuntimeError("Timed out starting V6 fixture server")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        if self.proc.stderr:
            self.proc.stderr.close()

    async def asyncSetUp(self):
        self.play = await async_playwright().start()
        options = {"headless": True, "args": ["--no-sandbox", "--no-proxy-server", "--proxy-bypass-list=<-loopback>"]}
        if os.environ.get("CHROME_BIN"):
            options["executable_path"] = os.environ["CHROME_BIN"]
        self.browser = await self.play.chromium.launch(**options)
        self.context = await self.browser.new_context(viewport={"width": 375, "height": 780})
        self.page = await self.context.new_page()

    async def asyncTearDown(self):
        await self.browser.close()
        await self.play.stop()

    async def open_board(self):
        await self.page.goto(self.base, wait_until="domcontentloaded")
        await self.page.locator(".card").first.wait_for(timeout=5000)

    async def test_rendering_is_safe_accessible_and_responsive(self):
        failures = []
        def check(condition, message):
            if not condition:
                failures.append(message)

        await self.open_board()
        await self.page.get_by_role("searchbox", name="Search discussions").fill("danger")
        await self.page.wait_for_function("document.querySelectorAll('.card').length === 1")
        card = self.page.locator(".card").first
        injected = await card.locator("img, svg, script, iframe").count()
        check(injected == 0, f"untrusted content created {injected} injected elements")
        button = card.locator(".bookmark")
        check(await button.get_attribute("aria-label") == "Save post", "bookmark has no useful accessible name")
        check(await button.get_attribute("aria-pressed") == "false", "bookmark aria-pressed does not reflect initial state")
        widths = await self.page.evaluate("({scroll: document.documentElement.scrollWidth, viewport: innerWidth})")
        check(widths["scroll"] <= widths["viewport"] + 1, f"horizontal overflow: {widths}")
        self.assertEqual(failures, [], "\n".join(failures))

    async def test_rollback_and_rapid_load_more_guard(self):
        failures = []
        def check(condition, message):
            if not condition:
                failures.append(message)

        await self.open_board()
        button = self.page.locator(".card .bookmark").first
        await button.click()
        await self.page.wait_for_function("document.querySelector('.bookmark')?.getAttribute('aria-pressed') === 'true'")

        async def fail_un_save(route):
            await route.fulfill(status=412, content_type="application/json", body='{"error":"stale version"}')
        await self.page.route("**/api/bookmarks/**", fail_un_save)
        await button.click()
        await self.page.wait_for_timeout(200)
        check(await button.get_attribute("aria-pressed") == "true", "failed un-save did not restore previous saved=true state")
        await self.page.unroute("**/api/bookmarks/**")

        cursor_requests = []
        async def delay_load_more(route):
            if "cursor=" in route.request.url:
                cursor_requests.append(route.request.url)
                await asyncio.sleep(.3)
            await route.continue_()
        await self.page.route("**/api/feed?**", delay_load_more)
        more = self.page.get_by_role("button", name="Load more")
        await more.dblclick()
        await self.page.wait_for_function("document.querySelectorAll('.card').length >= 16", timeout=5000)
        await self.page.wait_for_timeout(500)
        ids = await self.page.locator(".card").evaluate_all("cards => cards.map(card => card.dataset.id)")
        check(len(cursor_requests) == 1, f"rapid double-click issued {len(cursor_requests)} cursor requests")
        check(len(ids) == len(set(ids)), "rapid double-click rendered duplicate cards")
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
