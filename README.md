# A solipsist event loop

async-solipsism provide a Python asyncio event loop that does not interact with
the outside world at all. This is ideal for writing unit tests that intend to
mock out real-world interactions. It makes for tests that are reliable
(unaffected by network outages), reproducible (not affected by random timing
effects) and portable (run the same everywhere).

## Features

### Clock

A very handy feature is that time runs infinitely fast! What's more, time
advances only when explicitly waiting. For example, this code will print out
two times that are exactly 60s apart, and will take negligible real time to
run:

```python
print(loop.time())
await asyncio.sleep(60)
print(loop.time())
```

This also provides a handy way to ensure that all pending callbacks have a
chance to run: just sleep for a second.

The simulated clock has microsecond resolution, independent of whatever
resolution the system clock has. This helps ensure that tests behave the same
across operating systems.

Sometimes buggy code or a buggy test will await an event that will never
happen. For example, it might wait for data to arrive on a socket, but forget
to insert data into the other end. If async-solipsism detects that it will
never wake up again, it will raise a `SleepForeverError` rather than leaving
your test to hang.

### Sockets

While real sockets cannot be used, async-solipsism provides mock sockets that
implement just enough functionality to be used with the event loop. Sockets
are obtained by calling `async_solipsism.socketpair()`, which returns two
sockets that are connected to each other. They can then be used with event
loop functions like `sock_sendall` or `create_connection`.

Because the socket implementation is minimal, you may run into cases where
the internals of asyncio try to call methods that aren't implemented. Pull
requests are welcome.

Each direction of flow implements a buffer that holds data written to the one
socket but not yet received by the other. If this buffer fills up, write calls
will raise `BlockingIOError`, just like a real non-blocking socket. This can
be used to test that your protocol properly handles flow control. The size of
these buffers can be changed with the optional `capacity` argument to
`socketpair`.

### Streams

As a convenience, it is possible to open two pairs of streams that are
connected to each other, with

```
((reader1, writer1), (reader2, writer2)) = await async_solipsism.stream_pairs()
```

Anything written to `writer1` will be received by `reader2`, and anything
written to `writer2` will be received by `reader1`.

### Servers

It is also possible to use the asyncio functions for starting servers and
connecting to them. You can supply any host name and port, even if they're not
actually associated with the machine! For example,

```python
server = await asyncio.start_server(callback, 'test.invalid', 1234)
reader, writer = await asyncio.open_connection('test.invalid', 1234)
```

will start a server, then open a client connection to it. The `reader` and
`writer` represent the client end of the connection, and the `callback` will
be given the server end of the connection.

The host and port are associated with the event loop, and are remembered until
the server is closed. Attempting to connect after closing the server, or to an
address that hasn't been registered, will raise a `ConnectionRefusedError`.

### Integration with pytest-asyncio

async-solipsism and pytest-asyncio complement each other well: just write a
custom `event_loop` fixture in your test file or `conftest.py` and it will
override the default provided by pytest-asyncio:

```python
@pytest.fixture
def event_loop():
    loop = async_solipsism.EventLoop()
    yield loop
    loop.close()
```

### Integration with pytest-aiohttp

A little extra work is required to work with aiohttp's test utilities, but it
is possible. The example below requires at least aiohttp 3.8.0.

```python
import async_solipsism
import pytest
from aiohttp import web, test_utils


@pytest.fixture
def event_loop():
    loop = async_solipsism.EventLoop()
    yield loop
    loop.close()


def socket_factory(host, port, family):
    return async_solipsism.ListenSocket((host, port if port else 80))


async def test_integration():
    app = web.Application()
    async with test_utils.TestServer(app, socket_factory=socket_factory) as server:
        async with test_utils.TestClient(server) as client:
            resp = await client.post("/hey", json={})
            assert resp.status == 404
```

Note that this relies on pytest-asyncio (in auto mode) and does not use
pytest-aiohttp. The fixtures provided by the latter do not support overriding
the socket factory, although it may be possible to do by monkeypatching. In
practice you will probably want to define your own fixtures for the client
and server.

If you need to run more than one test server concurrently, you'll need to
extend the socket factory to assign them each a different port
(async-solipsism does not currently handle mapping port 0 to an unused port).

## Limitations

The requirement to have no interaction with the outside world naturally
imposes some restrictions. Other restrictions exist purely because I haven't
gotten around to figuring out what a fake version should look like and
implementing it. The following are all unsupported:

- `call_soon_threadsafe`, except when called from the thread running the
  event loop (it just forwards to `call_soon`). Multithreading is
  fundamentally incompatible with the fast-forward clock.
- `getaddrinfo` and `getnameinfo`
- `connect_read_pipe` and `connect_write_pipe`
- signal handlers
- subprocesses
- TLS/SSL
- datagrams (UDP)
- UNIX domain sockets
- any Windows-specific features

`run_in_executor` is supported, but it blocks the event loop while the task
runs in the executor. This works fine for short-running tasks like reading
some data from a file, but is not suitable if the task is a long-running one
such as a sidecar server.

Calling functions that are not supported will generally raise
`SolipsismError`.

## Changelog

### 0.4

- Allow `call_soon_threadsafe` from the same thread.
- Don't warn when `SO_KEEPALIVE` is set on a socket.
- Update instructions for use with aiohttp.
- Add a pyproject.toml

### 0.3

- Fix `start_server` with an explicit socket.
- Update README with an example of aiohttp integration.

### 0.2

- Numerous fixes to make the fake sockets behave more like real ones.
- Sockets now return IPv6 addresses from `getsockname`.
- Implement `setsockopt`.
- Introduce `SolipsismWarning` base class for warnings.

### 0.1

First release.
