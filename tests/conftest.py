"""pytest configuration for tiktok-ads-mcp tests."""

import asyncio
import pytest


def pytest_configure(config):
    """Ensure a default event loop exists for tests using asyncio.get_event_loop()."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
