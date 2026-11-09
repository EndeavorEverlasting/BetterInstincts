"""Playwright adapter: reuse an existing page; never spawn a competing browser.

Every click or fill is one queued step with a fresh page/locator check. The
cooperative queue owns screen admission; Playwright remains an injected port.
"""
from __future__ import annotations

from typing import Any

from betterinstincts.workflow_interop import CooperativeScreenQueue, QueuedStep


def enqueue_playwright_step(
    queue: CooperativeScreenQueue,
    *,
    work_id: str,
    page: Any,
    selector: str,
    expected_url: str,
    operation: str = "click",
    text: str | None = None,
    expected_value: str | None = None,
) -> None:
    """Add one deliberate UI effect to an ACTIVE cooperative session.

    Invalid/stale page or unexpected field content quarantines the intent for
    human review rather than replaying it. Selector and typed text are NOT
    logged by the queue. Never use Playwright's force-click override.
    """
    if operation not in {"click", "fill"}:
        raise ValueError("PLAYWRIGHT_OPERATION_UNSUPPORTED")
    if not isinstance(selector, str) or not selector.strip() or not isinstance(expected_url, str) or not expected_url:
        raise ValueError("PLAYWRIGHT_TARGET_REQUIRED")
    if operation == "fill" and (not isinstance(text, str) or not isinstance(expected_value, str)):
        raise ValueError("FILL_REQUIRES_EXPLICIT_TEXT_AND_EXPECTED_OLD_VALUE")

    async def validate() -> bool:
        if page.is_closed() or page.url != expected_url:
            return False
        locator = page.locator(selector)
        if not await locator.is_visible():
            return False
        if operation == "fill" and await locator.input_value() != expected_value:
            return False
        return True

    async def action(checkpoint) -> None:
        # Re-use the already-owned page. No launch/new context/bring_to_front.
        locator = page.locator(selector)
        await checkpoint()
        if operation == "click":
            await locator.click(timeout=2000)
        else:
            await locator.fill(text, timeout=2000)

    queue.enqueue(QueuedStep(work_id=work_id, validate=validate, action=action))
