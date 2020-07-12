import socket


DEFAULT_CAPACITY = 65536


__all__ = ('Socket', 'Queue', 'socketpair')


class Queue:
    def __init__(self, capacity=DEFAULT_CAPACITY):
        self.capacity = capacity
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


class Socket:
    family = 0
    type = 0
    proto = 0

    def __init__(self, read_queue, write_queue):
        self._read_queue = read_queue
        self._write_queue = write_queue

    def fileno(self):
        return SocketFd(self)

    def getsockname(self):
        raise socket.error('getsockname is not supported')

    def getpeername(self):
        raise socket.error('getpeername is not supported')

    def gettimeout(self):
        return 0.0

    def recv(self, bufsize, flags=0):
        return self._read_queue.read(bufsize)

    def recv_into(self, buffer, nbytes=0, flags=0):
        # TODO: implement in re
        if not nbytes:
            nbytes = len(buffer)
        data = self.recv(nbytes)
        buffer[:len(data)] = data
        return len(data)

    def send(self, bytes, flags=0):
        return self._write_queue.write(bytes)

    def read_ready(self):
        return self._read_queue.read_ready()

    def write_ready(self):
        return self._write_queue.write_ready()

    def close(self):
        self._write_queue.write_eof()
        self._write_queue = None
        self._read_queue = None


def socketpair():
    queue1 = Queue()
    queue2 = Queue()
    return Socket(queue1, queue2), Socket(queue2, queue1)
