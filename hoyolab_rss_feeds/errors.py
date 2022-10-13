class HoyolabRssFeedsBaseError(Exception):
    """Base Error for this package."""
    pass


class MappingError(HoyolabRssFeedsBaseError):
    """Error for invalid mapping value."""
    pass


class ConfigError(HoyolabRssFeedsBaseError):
    """Error for invalid configuration."""
    pass


class HoyolabApiError(HoyolabRssFeedsBaseError):
    """Error while interacting with Hoyolab API."""
    pass


class FeedIOError(HoyolabRssFeedsBaseError):
    """Feed IO errors."""
