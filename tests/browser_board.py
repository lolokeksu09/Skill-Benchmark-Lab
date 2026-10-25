"""Chromium end-to-end tests for the local benchmark fixture.

Install: python -m pip install playwright==1.56.0
         python -m playwright install chromium
Run:     npm run test:browser
For system Chromium use CHROME_BIN=/usr/bin/chromium.
"""
import asyncio
import os
import pathlib
import socket
import urllib.request
import urllib.error
import subprocess
import time
import unittest
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BrowserBoardTests(unittest.IsolatedAsyncioTestCase):
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
        import urllib.request
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("Benchmark Node server exited during setup")
            try:
                with urllib.request.urlopen(self.base, timeout=.25) as resp:
                    if resp.status == 200:
                        return
            except Exception:
                time.sleep(.1)
        raise RuntimeError("Timed out starting Node fixture server")

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
        self.context = await self.browser.new_context(viewport={"width": 1280, "height": 820})
        self.page = await self.context.new_page()


    async def asyncTearDown(self):
        await self.browser.close()
        await self.play.stop()

    async def open_board(self):
        await self.page.goto(self.base, wait_until="domcontentloaded")
        await self.page.locator(".card").first.wait_for(timeout=5000)
        await self.page.get_by_role("status").filter(has_text="discussions").wait_for(timeout=5000)

    async def test_initial_loading_and_pagination_are_functional(self):
        await self.open_board()
        self.assertEqual(await self.page.locator(".card").count(), 8)
        await self.page.get_by_role("button", name="Load more").click()
        await self.page.wait_for_function("document.querySelectorAll('.card').length === 16")
        ids = await self.page.locator(".card").evaluate_all("els => els.map(e => e.dataset.id)")
        self.assertEqual(len(set(ids)), 16)

    async def test_mobile_375px_does_not_overflow_viewport(self):
        await self.page.set_viewport_size({"width": 375, "height": 760})
        await self.open_board()
        widths = await self.page.evaluate("({scroll: document.documentElement.scrollWidth, viewport: innerWidth})")
        self.assertLessEqual(widths["scroll"], widths["viewport"] + 1)
        self.assertGreater((await self.page.locator('.card').first.bounding_box())['width'], 200)

    async def test_malicious_title_and_summary_are_inert_text(self):
        await self.open_board()
        await self.page.get_by_role("searchbox", name="Search discussions").fill("danger")
        await self.page.get_by_role("status").filter(has_text="1 discussions").wait_for(timeout=5000)
        card = self.page.locator(".card").first
        self.assertIn('<img src=x onerror=', await card.locator("h2").inner_text())
        self.assertEqual(await card.locator("img,svg").count(), 0)
        self.assertIsNone(await self.page.evaluate("window.__pwned"))

    async def test_bookmark_button_has_name_and_reflects_successful_toggle(self):
        await self.open_board()
        button = self.page.locator(".card .bookmark").first
        self.assertEqual(await button.get_attribute("aria-label"), "Save post")
        self.assertEqual(await button.get_attribute("aria-pressed"), "false")
        await button.click()
        await self.page.wait_for_function("document.querySelector('.bookmark').getAttribute('aria-pressed') === 'true'")
        self.assertEqual(await button.get_attribute("aria-label"), "Remove saved post")

    async def test_failed_bookmark_write_rolls_back_and_reports_error(self):
        await self.open_board()
        await self.page.route("**/api/bookmarks/**", lambda route: route.fulfill(
            status=412, content_type="application/json", body='{"error":"stale version"}'
        ))
        button = self.page.locator(".card .bookmark").first
        await button.click()
        await self.page.get_by_role("status").filter(has_text="Could not save").wait_for(timeout=5000)
        self.assertEqual(await button.get_attribute("aria-pressed"), "false")
        self.assertEqual(await button.get_attribute("aria-label"), "Save post")

    async def test_stale_search_results_never_override_newest_query(self):
        async def intercept(route):
            if "q=discussion" in route.request.url:
                await asyncio.sleep(.7)
            await route.continue_()
        await self.page.route("**/api/feed?**", intercept)
        await self.open_board()
        box = self.page.get_by_role("searchbox", name="Search discussions")
        await box.fill("discussion")
        await box.fill("danger")
        await self.page.get_by_role("status").filter(has_text="1 discussions").wait_for(timeout=5000)
        await asyncio.sleep(1.0)
        ids = await self.page.locator(".card").evaluate_all("els => els.map(e => e.dataset.id)")
        self.assertEqual(ids, ["p-xss"])

    async def test_failed_unsave_restores_previous_saved_state(self):
        """Failed un-save must preserve previously saved=true; each test has a fresh server."""
        await self.open_board()
        button = self.page.locator(".card .bookmark").first
        self.assertEqual(await button.get_attribute("aria-pressed"), "false")
        await button.click()
        await self.page.wait_for_function(
            "document.querySelector('.bookmark').getAttribute('aria-pressed') === 'true' "
            "&& !document.querySelector('.bookmark').disabled"
        )
        await self.page.route("**/api/bookmarks/**", lambda route: route.fulfill(
            status=412, content_type="application/json", body='{"error":"stale version"}'
        ))
        await button.click()
        await self.page.get_by_role("status").filter(has_text="Could not save").wait_for(timeout=5000)
        self.assertEqual(await button.get_attribute("aria-pressed"), "true")
        self.assertEqual(await button.get_attribute("aria-label"), "Remove saved post")

    async def test_keyboard_enter_and_space_activate_bookmark(self):
        await self.open_board()
        button = self.page.locator(".card .bookmark").first
        await button.focus()
        await self.page.keyboard.press("Enter")
        await self.page.wait_for_function(
            "document.querySelector('.bookmark').getAttribute('aria-pressed') === 'true' "
            "&& !document.querySelector('.bookmark').disabled"
        )
        await self.page.keyboard.press("Space")
        await self.page.wait_for_function(
            "document.querySelector('.bookmark').getAttribute('aria-pressed') === 'false' "
            "&& !document.querySelector('.bookmark').disabled"
        )
        self.assertEqual(await button.get_attribute("aria-label"), "Save post")

    async def test_loading_all_pages_does_not_duplicate_cards(self):
        await self.open_board()
        expected = (16, 24, 30)
        for count in expected:
            await self.page.get_by_role("button", name="Load more").click()
            await self.page.wait_for_function(
                "(n) => document.querySelectorAll('.card').length === n", arg=count, timeout=5000
            )
        ids = await self.page.locator(".card").evaluate_all("els => els.map(e => e.dataset.id)")
        self.assertEqual(len(ids), 30)
        self.assertEqual(len(set(ids)), 30)
        self.assertTrue(await self.page.get_by_role("button", name="Load more").is_hidden())

    async def test_failed_search_keeps_previous_cards_and_announces_error(self):
        await self.open_board()
        self.assertEqual(await self.page.locator(".card").count(), 8)
        await self.page.route("**/api/feed?**", lambda route: route.fulfill(
            status=500, content_type="application/json", body='{"error":"temporary issue"}'
        ))
        await self.page.get_by_role("searchbox", name="Search discussions").fill("danger")
        await self.page.get_by_role("status").filter(has_text="Could not load").wait_for(timeout=5000)
        self.assertEqual(await self.page.locator(".card").count(), 8)

    async def test_keyboard_focus_on_bookmark_is_visible(self):
        await self.open_board()
        await self.page.get_by_role("searchbox", name="Search discussions").focus()
        await self.page.keyboard.press("Tab")
        self.assertEqual(await self.page.evaluate("document.activeElement?.className"), "bookmark")
        style = await self.page.evaluate("getComputedStyle(document.activeElement).outlineStyle")
        self.assertNotEqual(style, "none")


if __name__ == '__main__':
    unittest.main()
