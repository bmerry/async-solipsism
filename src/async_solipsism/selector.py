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

import asyncio.base_events
import selectors

from . import socket
from .exceptions import SolipsismError, SleepForeverError
from .clock import Clock


__all__ = ('Selector',)


class Selector(selectors._BaseSelectorImpl):
    def __init__(self, clock=None):
        super().__init__()
        self.clock = Clock() if clock is None else clock
        self._closed = False

    def _fileobj_lookup(self, fileobj):
        self._check_closed()
        if isinstance(fileobj, socket.Socket):
            return fileobj.fileno()
        elif isinstance(fileobj, socket.SocketFd):
            return fileobj
        else:
            raise SolipsismError('Only instances of Socket or SocketFd can be registered')

    def select(self, timeout=None):
        self._check_closed()
        ready = []
        for key in self.get_map().values():
            events = 0
            if (key.events & selectors.EVENT_READ) and key.fd.socket.read_ready():
                events |= selectors.EVENT_READ
            if (key.events & selectors.EVENT_WRITE) and key.fd.socket.write_ready():
                events |= selectors.EVENT_WRITE
            if events:
                ready.append((key, events))
        if ready:
            return ready
        elif timeout is None or timeout >= asyncio.base_events.MAXIMUM_SELECT_TIMEOUT:
            raise SleepForeverError('select with no timeout and no ready events')
        elif timeout > 0:
            self.clock.advance(timeout)
        return []

    def close(self):
        super().close()
        self._closed = True

    def _check_closed(self):
        if self._closed:
            raise RuntimeError('Selector is closed')
