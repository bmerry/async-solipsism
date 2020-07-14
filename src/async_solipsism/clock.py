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
