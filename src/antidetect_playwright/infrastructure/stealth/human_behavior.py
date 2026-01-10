"""Human-like behavior simulation."""

import asyncio
import random
from typing import Callable, Awaitable

from playwright.async_api import Page, Mouse


async def human_delay(min_ms: int = 50, max_ms: int = 200) -> None:
    """Random human-like delay."""
    delay = random.randint(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def human_typing_delay() -> None:
    """Delay between keystrokes."""
    await asyncio.sleep(random.uniform(0.05, 0.15))


async def type_like_human(page: Page, selector: str, text: str) -> None:
    """Type text with human-like timing."""
    element = await page.wait_for_selector(selector)
    if not element:
        raise ValueError(f"Element not found: {selector}")

    await element.click()
    await human_delay(100, 300)

    for char in text:
        await page.keyboard.type(char)
        await human_typing_delay()


async def click_like_human(page: Page, selector: str) -> None:
    """Click with human-like mouse movement."""
    element = await page.wait_for_selector(selector)
    if not element:
        raise ValueError(f"Element not found: {selector}")

    box = await element.bounding_box()
    if not box:
        await element.click()
        return

    target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
    target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

    await move_mouse_human(page, target_x, target_y)
    await human_delay(50, 150)
    await page.mouse.click(target_x, target_y)


async def move_mouse_human(
    page: Page,
    target_x: float,
    target_y: float,
    steps: int = 10,
) -> None:
    """Move mouse in a human-like curved path."""
    current_pos = await page.evaluate("() => ({ x: 0, y: 0 })")
    start_x, start_y = current_pos.get("x", 0), current_pos.get("y", 0)

    control_x = (start_x + target_x) / 2 + random.uniform(-50, 50)
    control_y = (start_y + target_y) / 2 + random.uniform(-50, 50)

    for i in range(steps + 1):
        t = i / steps

        x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t**2 * target_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t**2 * target_y

        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))


async def scroll_like_human(
    page: Page,
    direction: str = "down",
    amount: int = 500,
) -> None:
    """Scroll with human-like behavior."""
    step_size = random.randint(50, 150)
    current = 0

    while current < amount:
        scroll = min(step_size, amount - current)
        if direction == "down":
            await page.mouse.wheel(0, scroll)
        else:
            await page.mouse.wheel(0, -scroll)

        current += scroll
        await asyncio.sleep(random.uniform(0.02, 0.08))


async def random_mouse_movement(page: Page, count: int = 3) -> None:
    """Perform random mouse movements to simulate human presence."""
    viewport = await page.viewport_size() or {"width": 1920, "height": 1080}

    for _ in range(count):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await move_mouse_human(page, x, y)
        await human_delay(200, 500)
