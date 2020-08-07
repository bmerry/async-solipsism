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

import pytest

import async_solipsism


@pytest.fixture
def sock():
    return async_solipsism.socketpair()[0]


def test_setblocking(sock):
    sock.setblocking(False)
    with pytest.raises(async_solipsism.SolipsismError):
        sock.setblocking(True)


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
