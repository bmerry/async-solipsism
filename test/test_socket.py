import pytest

import async_solipsism


@pytest.fixture
def sock():
    return async_solipsism.socketpair()[0]


def test_setblocking(sock):
    sock.setblocking(False)
    with pytest.raises(async_solipsism.SolipsismError):
        sock.setblocking(True)
