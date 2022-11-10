"""RSS feed generator for official game news from Hoyolab."""

from . import configs
from . import errors
from . import feeds
from . import hoyolab
from . import loaders
from . import models
from . import writers

# quick access
from .configs import FeedConfigLoader
from .feeds import GameFeed
from .feeds import GameFeedCollection
from .models import Game

__all__ = [
    "configs",
    "errors",
    "feeds",
    "hoyolab",
    "loaders",
    "models",
    "writers",
    "FeedConfigLoader",
    "GameFeed",
    "GameFeedCollection",
    "Game",
]
