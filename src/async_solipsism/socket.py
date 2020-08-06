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
import socket
from collections import deque

from .exceptions import SolipsismError


DEFAULT_CAPACITY = 65536


__all__ = ('Socket', 'ListenSocket', 'Queue', 'socketpair')


class Queue:
    def __init__(self, capacity=None):
        self.capacity = capacity or DEFAULT_CAPACITY
        self._buffer = bytearray()
        self._eof = False

    def write_eof(self):
        self._eof = True

    def __len__(self):
        return len(self._buffer)

    def __bool__(self):
        return bool(self._buffer)

    def write(self, data):
        if self._eof:
            raise RuntimeError('Cannot write after connection closed')
        if len(self) >= self.capacity:
            return None
        n = len(data)
        if len(self) + n > self.capacity:
            n = self.capacity - len(self)
            data = memoryview(data)[:n]
        self._buffer += data
        return n

    def read(self, size=-1):
        if not self._buffer:
            if self._eof:
                return b''
            else:
                raise BlockingIOError
        elif size < 0:
            ret = self._buffer
            self._buffer = bytearray()
        else:
            n = min(size, len(self._buffer))
            ret = bytes(memoryview(self._buffer))[:n]
            self._buffer = self._buffer[n:]
        return ret

    def read_ready(self):
        return self._eof or self._buffer

    def write_ready(self):
        return len(self) < self.capacity


class SocketFd:
    def __init__(self, socket):
        self.socket = socket

    def fileno(self):
        return self

    def __int__(self):
        return id(self.socket)

    def __hash__(self):
        return hash(self.socket)

    def __eq__(self, other):
        if type(other) == SocketFd:
            return self.socket is other.socket
        return NotImplemented


class _SocketBase:
    family = 0
    type = socket.SOCK_STREAM
    proto = 0

    def fileno(self):
        return SocketFd(self)

    def gettimeout(self):
        return 0.0

    def setblocking(self, flag):
        if flag:
            raise SolipsismError('Socket only support non-blocking operation')


class Socket(_SocketBase):
    """Emulate a connected TCP socket."""

    def __init__(self, read_queue, write_queue, sockname=None, peername=None):
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._sockname = sockname
        self._peername = peername

    def getsockname(self):
        return self._sockname

    def getpeername(self):
        return self._peername

    def recv(self, bufsize, flags=0):
        return self._read_queue.read(bufsize)

    def recv_into(self, buffer, nbytes=0, flags=0):
        # TODO: implement more efficiently?
        if not nbytes:
            nbytes = len(buffer)
        data = self.recv(nbytes)
        buffer[:len(data)] = data
        return len(data)

    def send(self, bytes, flags=0):
        return self._write_queue.write(bytes)

    def read_ready(self):
        return self._read_queue is None or self._read_queue.read_ready()

    def write_ready(self):
        return self._write_queue is None or self._write_queue.write_ready()

    def shutdown(self, flag):
        if flag in {socket.SHUT_RD, socket.SHUT_RDWR} and self._read_queue is not None:
            self._read_queue = None
            # TODO: do we need to tell the other end that we're closed?
        if flag in {socket.SHUT_WR, socket.SHUT_RDWR} and self._write_queue is not None:
            self._write_queue.write_eof()
            self._write_queue = None

    def close(self):
        self.shutdown(socket.SHUT_RDWR)


class ListenSocket(_SocketBase):
    """Emulate a TCP socket that is listening for incoming connections."""

    def __init__(self, sockname):
        self._sockname = sockname
        self._queue = deque()

    def getsockname(self):
        return self._sockname

    def listen(self, backlog=None):
        pass

    def read_ready(self):
        if self._queue is None:
            return True
        while self._queue and self._queue[0].done():
            self._queue.popleft()
        return bool(self._queue)

    def close(self):
        for waiter in self._queue:
            if not waiter.done():
                waiter.set_exception(ConnectionResetError("Remote socket was closed"))
        self._queue = None

    def accept(self):
        if self._queue is None:
            raise RuntimeError('Socket is already closed')
        while self._queue and self._queue[0].done():
            self._queue.popleft()
        if not self._queue:
            raise BlockingIOError
        socks = socketpair()
        remote = self._queue.popleft()
        remote.set_result(socks[0])
        return socks[1], ()

    async def make_connection(self):
        """Connect to the server represented by this listening socket."""
        waiter = asyncio.get_event_loop().create_future()
        self._queue.append(waiter)
        return await waiter


def socketpair(capacity=None, sock1_name=None, sock2_name=None):
    queue1 = Queue(capacity=capacity)
    queue2 = Queue(capacity=capacity)
    sock1 = Socket(queue1, queue2, sockname=sock1_name, peername=sock2_name)
    sock2 = Socket(queue2, queue1, sockname=sock2_name, peername=sock1_name)
    return sock1, sock2
