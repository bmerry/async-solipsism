# Copyright 2020 Bruce Merry
#
# This file is part of async-solipsism.
#
# async-solipsism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# async-solipsism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with async-solipsism.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import concurrent.futures
import threading

import pytest

import async_solipsism


@pytest.fixture
def event_loop():
    loop = async_solipsism.EventLoop()
    yield loop
    loop.close()


async def test_sleep(event_loop):
    assert event_loop.time() == 0.0
    await asyncio.sleep(2)
    assert event_loop.time() == 2.0


def test_sleep_forever(event_loop):
    async def zzz():
        await asyncio.Future()

    with pytest.raises(async_solipsism.SleepForeverError):
        event_loop.run_until_complete(zzz())


@pytest.mark.parametrize(
    'method',
    [
        'recv',
        pytest.param('recv_into', marks=pytest.mark.skipif("sys.version_info < (3, 7)"))
    ]
)
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


async def test_connect_existing(event_loop, mocker):
    sock1, sock2 = async_solipsism.socketpair()
    transport1, protocol1 = await event_loop.connect_accepted_socket(
        mocker.MagicMock, sock1)
    transport2, protocol2 = await event_loop.create_connection(
        mocker.MagicMock, sock=sock2)
    transport1.write(b'Hello world\n')
    transport1.write_eof()
    transport1.close()
    protocol2.eof_received.return_value = None
    await asyncio.sleep(1)
    assert protocol2.method_calls == [
        mocker.call.connection_made(transport2),
        mocker.call.data_received(b'Hello world\n'),
        mocker.call.eof_received(),
        mocker.call.connection_lost(None)
    ]


async def test_stream():
    ((reader1, writer1), (reader2, writer2)) = await async_solipsism.stream_pairs()
    writer1.write(b'Hello world\n')
    data = await reader2.readline()
    assert data == b'Hello world\n'
    writer1.close()
    writer2.close()


@pytest.mark.parametrize('manual_socket', [False, True])
async def test_server(event_loop, manual_socket):
    def callback(reader, writer):
        server_conn.set_result((reader, writer))

    server_conn = event_loop.create_future()
    if manual_socket:
        listen_socket = async_solipsism.ListenSocket(('test.invalid', 1234))
        server = await asyncio.start_server(callback, sock=listen_socket)
    else:
        server = await asyncio.start_server(callback, 'test.invalid', 1234)
    c_reader, c_writer = await asyncio.open_connection('test.invalid', 1234)
    s_reader, s_writer = await server_conn
    c_socket = c_writer.get_extra_info('socket')
    s_socket = s_writer.get_extra_info('socket')
    assert c_socket.getpeername() == s_socket.getsockname() == ('test.invalid', 1234, 0, 0)
    assert s_socket.getpeername() == c_socket.getsockname() == ('::1', 1, 0, 0)

    c_writer.write(b'Hello world\n')
    assert await s_reader.readline() == b'Hello world\n'

    s_writer.write(b'Testing\n')
    assert await c_reader.readline() == b'Testing\n'
    c_writer.close()
    s_writer.close()
    server.close()
    await server.wait_closed()


async def test_close_server(event_loop):
    server = await asyncio.start_server(lambda reader, writer: None, 'test.invalid', 1234)
    server.close()
    await server.wait_closed()
    with pytest.raises(ConnectionRefusedError):
        await event_loop.create_connection('test.invalid', 1234)


async def test_create_connection_no_listener(event_loop):
    with pytest.raises(ConnectionRefusedError):
        await event_loop.create_connection('test.invalid', 1234)


async def test_run_in_executor_implicit(event_loop):
    thread_id = await event_loop.run_in_executor(None, threading.get_ident)
    assert isinstance(thread_id, int)
    assert thread_id != threading.get_ident()


async def test_run_in_executor_explicit(event_loop):
    my_executor = concurrent.futures.ThreadPoolExecutor(1)
    expected_thread_id = my_executor.submit(threading.get_ident).result()
    assert isinstance(expected_thread_id, int)
    thread_id = await event_loop.run_in_executor(my_executor, threading.get_ident)
    assert thread_id == expected_thread_id
    my_executor.shutdown()


@pytest.mark.skipif("sys.version_info < (3, 7)")
async def test_sendfile(event_loop, tmp_path):
    tmp_file = tmp_path / 'test_sendfile.txt'
    tmp_file.write_bytes(b'Hello world\n')
    ((reader1, writer1), (reader2, writer2)) = await async_solipsism.stream_pairs()
    with open(tmp_file, 'rb') as f:
        await event_loop.sendfile(writer1.transport, f)
    line = await reader2.readline()
    assert line == b'Hello world\n'


async def test_call_soon_threadsafe(event_loop):
    future = event_loop.create_future()
    event_loop.call_soon_threadsafe(future.set_result, 3)
    result = await future
    assert result == 3


async def test_call_soon_threadsafe_wrong_thread(event_loop):
    def thread_func():
        event_loop.call_soon_threadsafe(lambda: None)

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        with pytest.raises(async_solipsism.SolipsismError):
            pool.submit(thread_func).result()
