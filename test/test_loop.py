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


@pytest.mark.parametrize('method', ['recv', 'recv_into'])
@pytest.mark.parametrize('delay', [False, True])
async def test_delayed_sock_recv(method, delay, event_loop):
    async def delayed_write(wsock):
        await asyncio.sleep(1)
        wsock.send(b'Hello')

    rsock, wsock = async_solipsism.socketpair()
    task = event_loop.create_task(delayed_write(wsock))
    if not delay:
        await task
    if method == 'recv':
        data = await event_loop.sock_recv(rsock, 10)
    else:
        data = bytearray(10)
        n = await event_loop.sock_recv_into(rsock, data)
        data = data[:n]
    assert data == b'Hello'
    assert event_loop.time() == 1.0
    rsock.close()
    wsock.close()
    await task

@pytest.mark.parametrize('size', [10, 10**7])
async def test_sock_sendall(size, event_loop):
    async def delayed_read(rsock):
        n = 0
        while True:
            try:
                data = rsock.recv(16384)
            except BlockingIOError:
                await asyncio.sleep(1)
            else:
                if not data:
                    break
                assert data == b'?' * len(data)
                n += len(data)
        return n

    rsock, wsock = async_solipsism.socketpair()
    task = event_loop.create_task(delayed_read(rsock))
    await event_loop.sock_sendall(wsock, b'?' * size)
    wsock.close()
    n = await task
    assert n == size


async def test_stream():
    ((reader1, writer1), (reader2, writer2)) = await async_solipsism.stream_pairs()
    writer1.write(b'Hello world\n')
    data = await reader2.readline()
    assert data == b'Hello world\n'
    writer1.close()
    writer2.close()
