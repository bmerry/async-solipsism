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

import socket

import pytest

import async_solipsism


@pytest.fixture
def sock():
    return async_solipsism.socketpair()[0]


def test_setblocking(sock):
    sock.setblocking(False)
    with pytest.raises(async_solipsism.SolipsismError):
        sock.setblocking(True)


def test_setsockopt_known(sock, caplog):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


def test_setsockopt_unknown(sock, caplog):
    try:
        opt = socket.IP_MULTICAST_LOOP
    except AttributeError:
        pytest.skip('IP_MULTICAST_LOOP not defined')
    with pytest.warns(async_solipsism.SolipsismWarning, match='Ignoring socket option'):
        sock.setsockopt(socket.IPPROTO_IP, opt, 1)


@pytest.mark.parametrize(
    'given, expected',
    [
        (None, ('::', 0, 0, 0)),
        (('fe80::', 1234), ('fe80::', 1234, 0, 0)),
        (('fe80::', 1, 2, 3), ('fe80::', 1, 2, 3))
    ]
)
def test_sockaddr(given, expected):
    sock = async_solipsism.socketpair(sock1_name=given)[0]
    assert sock.getsockname() == expected


@pytest.mark.parametrize('end', ['read', 'write'])
def test_use_after_shutdown(end):
    sock0, sock1 = async_solipsism.socketpair()
    if end == 'read':
        sock0.shutdown(socket.SHUT_RD)
    else:
        sock1.shutdown(socket.SHUT_WR)
    assert sock0.recv(1) == b''
    with pytest.raises(BrokenPipeError):
        sock1.send(b'hello')
