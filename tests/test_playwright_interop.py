"""Existing Playwright page is reused and checked after user idle."""
import tempfile
import unittest
from pathlib import Path

from betterinstincts.playwright_interop import enqueue_playwright_step
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.workflow_interop import CooperativeScreenQueue


class FakeLocator:
    def __init__(self):
        self.visible = True
        self.value = ""
        self.effects = []

    async def is_visible(self):
        return self.visible

    async def input_value(self):
        return self.value

    async def click(self, *, timeout):
        self.effects.append(("click", timeout))

    async def fill(self, value, *, timeout):
        self.effects.append(("fill", value, timeout))


class FakePage:
    def __init__(self):
        self.url = "https://example.invalid/operator"
        self.closed = False
        self.target = FakeLocator()
        self.locators = []

    def is_closed(self):
        return self.closed

    def locator(self, selector):
        self.locators.append(selector)
        return self.target


class PlaywrightInteropTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.age = 0
        self.page = FakePage()

        async def no_delay(seconds):
            pass

        self.queue = CooperativeScreenQueue(
            lambda: PresenceProbe(False, False, last_input_age_ms=self.age),
            lambda: True,
            lock_root=Path(self.tmp.name),
            sleep=no_delay,
        )

    async def test_click_never_launches_browser_and_waits_for_human(self):
        enqueue_playwright_step(
            self.queue, work_id="click1", page=self.page, selector="#confirm",
            expected_url=self.page.url,
        )
        self.assertEqual((await self.queue.run_once())["state"], "WAITING_FOR_USER")
        self.assertEqual(self.page.target.effects, [])
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.page.target.effects, [("click", 2000)])

    async def test_page_changes_before_resume_requires_revalidation(self):
        enqueue_playwright_step(
            self.queue, work_id="click2", page=self.page, selector="#confirm",
            expected_url=self.page.url,
        )
        self.age = 16000
        self.page.url = "https://example.invalid/other"
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertEqual(self.page.target.effects, [])

    async def test_fill_requires_expected_current_value(self):
        self.page.target.value = "operator changed"
        enqueue_playwright_step(
            self.queue, work_id="fill1", page=self.page, selector="#entry",
            expected_url=self.page.url, operation="fill",
            text="approved", expected_value="",
        )
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "NEEDS_REVALIDATION")
        self.assertEqual(self.page.target.effects, [])

    async def test_valid_fill_is_one_admitted_effect(self):
        enqueue_playwright_step(
            self.queue, work_id="fill2", page=self.page, selector="#entry",
            expected_url=self.page.url, operation="fill",
            text="approved", expected_value="",
        )
        self.age = 16000
        self.assertEqual((await self.queue.run_once())["state"], "COMPLETED")
        self.assertEqual(self.page.target.effects, [("fill", "approved", 2000)])

    async def test_force_actions_not_exposed(self):
        with self.assertRaises(ValueError):
            enqueue_playwright_step(
                self.queue, work_id="bad", page=self.page,
                selector="#x", expected_url=self.page.url, operation="force-click",
            )


if __name__ == "__main__":
    unittest.main()
