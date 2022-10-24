class HoyolabRssFeedsBaseError(Exception):
    """Base Error for this package."""


class ConfigIOError(HoyolabRssFeedsBaseError):
    """Raised if an IO operation on a config file failed."""


class FeedIOError(HoyolabRssFeedsBaseError):
    """Raised if an IO operation on a feed file failed."""


class HoyolabApiError(HoyolabRssFeedsBaseError):
    """Raised if interaction with the Hoyolab API failed."""


class ConfigFormatError(HoyolabRssFeedsBaseError):
    """Raised if an invalid config syntax or value is found."""


class FeedFormatError(HoyolabRssFeedsBaseError):
    """Raised if an invalid feed syntax or value is found."""
