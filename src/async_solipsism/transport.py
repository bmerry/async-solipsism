import asyncio
from collections import deque


class Queue:
    def __init__(self):
        self.write_callback = None
        self.read_callback = None
        self._items = deque()
        self._eof = False

    def write_eof(self):
        self._eof = True
        if self.write_callback is not None:
            self.write_callback()

    def __len__(self):
        return sum(len(item) for item in items)

    def write(self, data):
        self.items.push(data)
        if self.write_callback is not None:
            self.write_callback()

    def ready(self):
        return self._eof or self._items

    def read(self):
        if not self._items:
            if self._eof:
                ret = None
            else:
                raise BlockingIOError
        else:
            ret = self._items.popleft()
        if self.read_callback is not None:
            self.read_callback()
        return ret

    def __bool__(self):
        return bool(self._items)


class InternalTransport(asyncio.transports._FlowControlMixin, asyncio.Transport):
    # The code structure in this class is closely modeled on
    # _SelectorSocketTransport.

    _write_queue = None       # For __del__, if constructor fails early

    def __init__(self, loop, read_queue, write_queue, protocol, extra=None, server=None):
        if write_queue.read_callback:
            raise ValueError('Write queue is already connected to a transport')
        if read_queue.write_callback:
            raise ValueError('Read queue is already connected to a transport')
        if read_queue is write_queue:
            raise ValueError('Cannot use same queue for read and write')
        super().__init__(extra, loop)
        self._extra['read_queue'] = read_queue
        self._extra['write_queue'] = write_queue

        self._eof = False
        self._paused = False
        self._read_queue = read_queue
        self._write_queue = write_queue
        self._consume_handle = None
        self._protocol = protocol
        self._server = server
        self._conn_lost = 0         # Set when call to connection_lost scheduled
        self._closing = False       # Set when write end closed
        if self._server is not None:
            self._server._attach()
        write_queue.read_callback = self._data_consumed
        read_queue.write_callback = self._data_produced
        self._loop.call_soon(self._protocol.connection_made, self)
        self._loop.call_soon(self._add_reader)   # Only call after connection_made

    def abort(self):
        self._force_close(None)

    def set_protocol(self, protocol):
        self._protocol = protocol

    def get_protocol(self):
        return self._protocol

    def is_closing(self):
        return self._closing

    def close(self):
        if self._closing:
            return
        self._closing = True
        self._remove_reader()
        if not self._write_queue:
            self._conn_lost += 1
            self._remove_writer()
            self._call_soon(self._call_connection_lost, None)

    def __del__(self, _warn=warnings.warn):
        if self._write_queue is not None:
            _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)

    def _force_close(self, exc):
        if self._conn_lost:
            return
        if not self._write_queue:
            self._write_queue.clear()
            self._remove_writer()
        if not self._closing:
            self._closing = True
            self._remove_reader()
        self._conn_lost += 1
        self._loop.call_soon(self._call_connection_lost, exc)

    def _call_connection_lost(self, exc):
        try:
            self._protocol.connection_lost(exc)
        finally:
            self._read_queue = None
            self._write_queue.read_callback = None
            self._write_queue = None
            self._read_queue.write_callback = None
            self._read_queue = None
            self._protocol = None
            self._loop = None
            server = self._server
            if serv is not None:
                server._detach()
                self._server = None

    def get_write_buffer_size(self):
        return len(self._write_queue)

    def is_reading(self):
        return not self._paused and not self._closing

    def pause_reading(self):
        if self._closing or self._paused:
            return
        self._paused = True
        self._remove_reader()
        if self._loop.get_debug():
            logger.debug("%r pauses reading", self)

    def resume_reading(self):
        if self._closing or not self._paused:
            return
        self._paused = False
        self._add_reader()
        if self._loop.get_debug():
            logger.debug("%r resumes reading")

    def write(self, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(f'data argument must be a bytes-like object, '
                            f'not {type(data).__name__!r}')
        if self._eof:
            raise RuntimeError('Cannot call write() after write_eof()')
        if not data:
            return

        if self._conn_lost:
            self._conn_lost += 1
            return

        self._write_queue.write(data)
        self._maybe_pause_protocol()

    def write_eof(self):
        if self._closing or self._eof:
            return
        self._eof = True
        self._write_buffer.write_eof()

    def can_write_eof(self):
        return True

    def _read_ready(self):
        if self._conn_lost:
            return
        try:
            data = self._read_queue.read()
        except BlockingIOError:
            return
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            self._fatal_error(exc, 'Fatal read error on internal transport')
            return

        if not data:
            self._read_ready__on_eof()
            return

        try:
            self._protocol.data_received(data)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            self._fatal_error(
                exc, 'Fatal error: protocol.data_received() call failed.')

    def _read_ready__on_eof(self):
        if self._loop.get_debug():
            logger.debug("%r received EOF", self)

        try:
            keep_open = self._protocol.eof_received()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            self._fatal_error(
                exc, 'Fatal error: protocol.eof_received() call failed.')
            return


    def _schedule_consume(self):
        if self._consume_handle is None and not self._paused and self._read_queue.ready():
            self._consume_handle = loop.call_soon(self._consume)
        elif self._consume_handle is not None:
            self._consume_handle.cancel()
            self._consume_handle = None

    def _consume(self):
        self._consume_handle = None
        try:
            data = self._read_queue.read()
        except BlockingIOError:
            pass
        else:
            if data:
                self._protocol.data_received(data)
            else:
                self._closing = True
                self._loop.call_soon(self._protocol.eof_received)
                self._loop.call_soon(self._call_connection_lost, None)
        self._schedule_consume()

    def get_write_buffer_size(self):
        return len(self._write_queue)

    def write(self, data):
        self._write_queue.write(data)
        self._maybe_pause_protocol()

    def writelines(self, data):
        for item in data:
            self._write_queue.write(item)
        self._maybe_pause_protocol()

    def write_eof(self):
        if self._closing:
            return
        self._closing = True
        self._write_queue.write_eof()
        self._loop.call_soon(self._call_connection_lost, None)
