__all__ = ('ResolutionWarning', 'SolipsismError', 'SleepForeverError')


class ResolutionWarning(Warning):
    pass


class SolipsismError(RuntimeError):
    pass


class SleepForeverError(SolipsismError):
    pass
