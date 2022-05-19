# Copyright 2020, 2022 Bruce Merry
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
import subprocess
import threading

from . import selector, socket as _socket
from .exceptions import SolipsismError


__all__ = ('EventLoop', 'stream_pairs')


class EventLoop(asyncio.selector_events.BaseSelectorEventLoop):
    def __init__(self):
        super().__init__(selector=selector.Selector())
        self._selector = selector.Selector()
        self._clock_resolution = self._selector.clock.resolution
        # Map from (host, port) pair to ListenSocket
        self.__listening_sockets = {}
        self.__next_port = 1

    def time(self):
        return self._selector.clock.time()

    def call_soon_threadsafe(self, callback, *args, context=None):
        if self._thread_id == threading.get_ident():
            return self.call_soon(callback, *args, context=context)
        raise SolipsismError("call_soon_threadsafe is not supported")

    async def run_in_executor(self, executor, func, *args):
        # Mostly copies the base class code, but runs synchronously
        self._check_closed()
        if self._debug:
            self._check_callback(func, 'run_in_executor')
        if executor is None:
            executor = self._default_executor
            if executor is None:
                executor = concurrent.futures.ThreadPoolExecutor()
                self._default_executor = executor
        return executor.submit(func, *args).result()

    async def getaddrinfo(self, host, port, *,
                          family=0, type=0, proto=0, flags=0):
        raise SolipsismError("getaddrinfo is not supported")

    async def getnameinfo(self, sockaddr, flags=0):
        raise SolipsismError("getnameinfo is not supported")

    async def create_connection(
            self, protocol_factory, host=None, port=None,
            *, ssl=None, sock=None, **kwargs):
        if ssl:
            raise SolipsismError("create_connection with SSL is not supported")
        if sock is None:
            if host is None and port is None:
                raise ValueError('host and port was not specified and no sock specified')
            addr = (host, port, 0, 0)
            try:
                listener = self.__listening_sockets[addr]
            except KeyError:
                raise ConnectionRefusedError(f'No socket listening on {host}:{port}') from None
            port = self.__next_port
            self.__next_port += 1
            sock = await listener.make_connection(('::1', port, 0, 0))
        return await super().create_connection(
            protocol_factory, None, None,
            ssl=ssl, sock=sock, **kwargs
        )

    async def start_tls(self, transport, protocol, sslcontext, *,
                        server_side=False,
                        server_hostname=None,
                        ssl_handshake_timeout=None):
        raise SolipsismError("start_tls is not supported")

    async def create_datagram_endpoint(self, protocol_factory,
                                       local_addr=None, remote_addr=None, *,
                                       family=0, proto=0, flags=0,
                                       reuse_address=None, reuse_port=None,
                                       allow_broadcast=None, sock=None):
        raise SolipsismError("create_datagram_endpoint is not supported")

    async def create_server(
            self, protocol_factory, host=None, port=None,
            *,
            sock=None,
            ssl=None,
            reuse_address=None,
            reuse_port=None,
            **kwargs):
        if ssl is not None:
            raise SolipsismError("create_server with ssl is not supported")
        if sock is None:
            if host is None and port is None:
                raise ValueError('Neither host/port nor sock were specified')
            # TODO: what if host is actually a list?
            addr = (host, port, 0, 0)
            sock = _socket.ListenSocket(addr)
        else:
            addr = sock.getsockname()
        if addr in self.__listening_sockets:
            raise SolipsismError("Reuse of listening addresses is not supported")
        self.__listening_sockets[addr] = sock
        return await super().create_server(
            protocol_factory, None, None,
            sock=sock,
            ssl=ssl,
            reuse_address=False,
            reuse_port=False,
            **kwargs
        )

    async def connect_read_pipe(self, protocol_factory, pipe):
        raise SolipsismError("connect_read_pipe is not supported")

    async def connect_write_pipe(self, protocol_factory, pipe):
        raise SolipsismError("connect_write_pipe is not supported")

    async def subprocess_shell(self, protocol_factory, cmd, *,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=False,
                               shell=True, bufsize=0,
                               encoding=None, errors=None, text=None,
                               **kwargs):
        raise SolipsismError("subprocess_shell is not supported")

    async def subprocess_exec(self, protocol_factory, program, *args,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=False,
                              shell=False, bufsize=0,
                              encoding=None, errors=None, text=None,
                              **kwargs):
        raise SolipsismError("subprocess_exec is not supported")

    async def sock_connect(self, sock, address):
        raise SolipsismError("sock_connect is not supported")

    async def sock_accept(self, sock):
        raise SolipsismError("sock_accept is not supported")

    def add_signal_handler(self, sig, callback, *args):
        raise SolipsismError("add_signal_handler is not supported")

    def remove_signal_handler(self, sig):
        raise SolipsismError("remove_signal_handler is not supported")

    async def create_unix_connection(
            self, protocol_factory, path=None, *,
            ssl=None, sock=None,
            server_hostname=None,
            ssl_handshake_timeout=None):
        raise SolipsismError("create_unix_connection is not supported")

    async def create_unix_server(
            self, protocol_factory, path=None, *,
            sock=None, backlog=100, ssl=None,
            ssl_handshake_timeout=None,
            start_serving=True):
        raise SolipsismError("create_unix_server is not supported")

    # Methods in base class that we need to implement/override

    def _make_self_pipe(self):
        pass

    def _close_self_pipe(self):
        pass

    def _stop_serving(self, sock):
        addr = sock.getsockname()
        self.__listening_sockets.pop(addr)
        super()._stop_serving(sock)


async def stream_pairs(capacity=None):
    sock1, sock2 = _socket.socketpair(capacity=capacity)
    streams1 = await asyncio.open_connection(sock=sock1)
    streams2 = await asyncio.open_connection(sock=sock2)
    return streams1, streams2
