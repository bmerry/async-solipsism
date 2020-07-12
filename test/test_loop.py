import asyncio

import pytest

import async_solipsism


pytestmark = [pytest.mark.asyncio]


@pytest.fixture
def event_loop():
    loop = async_solipsism.EventLoop()
    yield loop
    loop.close()


async def test_sleep(event_loop):
    assert event_loop.time() == 0.0
    await asyncio.sleep(2)
    assert event_loop.time() == 2.0
