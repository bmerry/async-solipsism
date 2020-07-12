import asyncio
import selectors
import socket
import subprocess
import warnings


__all__ = ('ResolutionWarning', 'SolipsismError', 'Clock', 'Selector', 'EventLoop')


class ResolutionWarning(Warning):
    pass


class SolipsismError(RuntimeError):
    pass


class Clock:
    def __init__(self, start_time=0.0, resolution=1e-6):
        if resolution <= 0.0:
            raise ValueError('Resolution must be positive')
        self._ticks = round(start_time / resolution)
        self._resolution = resolution

    @property
    def resolution(self):
        return self._resolution

    def time(self):
        return self._ticks * self._resolution

    def advance(self, delta):
        ticks = round(delta / self._resolution)
        if ticks == 0 and delta != 0.0:
            warnings.warn('delta is less than resolution, so clock will not advance',
                          ResolutionWarning)
        self._ticks += ticks


class Selector(selectors.BaseSelector):
    def __init__(self, clock=None):
        super().__init__()
        self.clock = Clock() if clock is None else clock
        self._closed = False

    def register(self, fileobj, events, data=None):
        self._check_closed()
        raise SolipsismError('register is not supported')

    def unregister(self, fileobj):
        self._check_closed()
        raise SolipsismError('unregister is not supported')

    def modify(self, fileobj, events, data=None):
        self._check_closed()
        raise SolipsismError('modify is not supported')

    def select(self, timeout=None):
        self._check_closed()
        if timeout >= asyncio.base_events.MAXIMUM_SELECT_TIMEOUT:
            raise SolipsismError('select with no timeout is not supported')
        elif timeout > 0:
            self.clock.advance(timeout)
        return []

    def close(self):
        self._closed = True

    def get_map(self):
        # get_key in the base class treats None as closed
        return None if self._closed else {}

    def _check_closed(self):
        if self._closed:
            raise RuntimeError('Selector is closed')


class EventLoop(asyncio.BaseEventLoop):
    def __init__(self):
        super().__init__()
        self._selector = Selector()
        self._clock_resolution = self._selector.clock.resolution

    def time(self):
        return self._selector.clock.time()

    def call_soon_threadsafe(self, callback, *args, context=None):
        raise SolipsismError("call_soon_threadsafe is not supported")

    def run_in_executor(self, executor, func, *args):
        raise SolipsismError("run_in_executor is not supported")

    async def getaddrinfo(self, host, port, *,
                          family=0, type=0, proto=0, flags=0):
        raise SolipsismError("getaddrinfo is not supported")

    async def getnameinfo(self, sockaddr, flags=0):
        raise SolipsismError("getnameinfo is not supported")

    async def sock_sendfile(self, sock, file, offset=0, count=None,
                            *, fallback=True):
        raise SolipsismError("sock_sendfile is not supported")

    async def create_connection(
            self, protocol_factory, host=None, port=None,
            *, ssl=None, family=0,
            proto=0, flags=0, sock=None,
            local_addr=None, server_hostname=None,
            ssl_handshake_timeout=None,
            happy_eyeballs_delay=None, interleave=None):
        raise SolipsismError("create_connection is not supported")

    async def sendfile(self, transport, file, offset=0, count=None,
                       *, fallback=True):
        raise SolipsismError("sendfile is not supported")

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
            family=socket.AF_UNSPEC,
            flags=socket.AI_PASSIVE,
            sock=None,
            backlog=100,
            ssl=None,
            reuse_address=None,
            reuse_port=None,
            ssl_handshake_timeout=None,
            start_serving=True):
        raise SolipsismError("create_server is not supported")

    async def connect_accepted_socket(
            self, protocol_factory, sock,
            *, ssl=None,
            ssl_handshake_timeout=None):
        raise SolipsismError("connect_accepted_socket is not supported")

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

    def add_reader(self, fd, callback, *args):
        raise SolipsismError("add_reader is not supported")

    def remove_reader(self, fd):
        raise SolipsismError("remove_reader is not supported")

    def add_writer(self, fd, callback, *args):
        raise SolipsismError("add_writer is not supported")

    def remove_writer(self, fd):
        raise SolipsismError("remove_writer is not supported")

    async def sock_recv(self, sock, n):
        raise SolipsismError("sock_recv is not supported")

    async def sock_recv_into(self, sock, buf):
        raise SolipsismError("sock_recv_into is not supported")

    async def sock_sendall(self, sock, data):
        raise SolipsismError("sock_sendall is not supported")

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

    # Methods in BaseEventLoop that we need to implement
    def _process_events(self, event_list):
        if event_list:
            raise SolipsismError("Unexpected events from selector")
