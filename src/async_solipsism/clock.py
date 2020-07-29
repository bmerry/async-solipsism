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

import warnings

from . import exceptions


__all__ = ('Clock',)


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
                          exceptions.ResolutionWarning)
        self._ticks += ticks
