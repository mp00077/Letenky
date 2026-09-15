class ProviderError(Exception):
    """Provider cannot return a trustworthy result."""


class InvalidResponse(ProviderError):
    pass


class DuplicateWatch(ValueError):
    pass
