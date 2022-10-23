class HoyolabRssFeedsBaseError(Exception):
    """Base Error for this package."""
    pass


class ConfigError(HoyolabRssFeedsBaseError):
    """Error for invalid configuration."""
    pass


class HoyolabApiError(HoyolabRssFeedsBaseError):
    """Error while interacting with Hoyolab API."""
    pass


class FeedIOError(HoyolabRssFeedsBaseError):
    """Feed IO errors."""
