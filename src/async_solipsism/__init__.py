# Copyright 2020-2022, 2024-2025 Bruce Merry
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
import sys
import warnings
from typing import TYPE_CHECKING

from .exceptions import *  # noqa
from .loop import *  # noqa
from .loop import EventLoop  # redundant, but keeps static analysis happy
from .socket import *  # noqa

__all__ = exceptions.__all__ + socket.__all__ + loop.__all__  # noqa
__version__ = "0.10"

if sys.version_info < (3, 16, 0):
    # asyncio.DefaultEventLoopPolicy is deprecated, so we have to jump through
    # some hoops to avoid using it at import time.
    __all__ += ("EventLoopPolicy",)

    if TYPE_CHECKING:

        class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
            def new_event_loop(self) -> EventLoop: ...
    else:

        def __getattr__(name):
            global EventLoopPolicy

            match name:
                case "EventLoopPolicy":

                    class EventLoopPolicy(asyncio.DefaultEventLoopPolicy):
                        def new_event_loop(self):
                            return EventLoop()

                    warnings.warn(
                        "async_solipsism.EventLoopPolicy is deprecated",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    return EventLoopPolicy
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
