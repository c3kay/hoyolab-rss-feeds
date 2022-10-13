import json
from abc import ABCMeta
from abc import abstractmethod
from os.path import exists
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import TypeVar

import aiofiles
from pydantic import parse_obj_as

from .errors import FeedIOError
from .models import FeedFileConfig
from .models import FeedItem
from .models import FeedMeta
from .models import FeedType
from .writers import W


class AbstractFeedFileLoader(metaclass=ABCMeta):
    """ABC for feed file loading functionality."""

    def __init__(self, config):
        self._config = config

    @property
    def config(self) -> FeedFileConfig:
        """Path where the feed should be loaded from."""
        return self._config

    @abstractmethod
    async def get_feed_items(self) -> List[FeedItem]:
        """Returns the items of the feed or empty list if not available."""
        pass

    @abstractmethod
    async def get_feed_meta(self) -> Optional[FeedMeta]:
        """Returns meta information about the feed or None if not available."""
        pass


L = TypeVar('L', bound=AbstractFeedFileLoader)


class FeedFileLoaderFactory:
    """Factory for creating specific FeedFileWriters."""

    def __init__(self):
        self._loaders = {
            FeedType.JSON: JSONFeedFileLoader
        }

    @property
    def feed_types(self) -> Set[FeedType]:
        """Set of feed types for which writers are registered."""
        return set(self._loaders.keys())

    def create_loader(self, config: FeedFileConfig) -> L:
        """Create feed loader for the specified feed type."""

        try:
            loader = self._loaders[config.feed_type](config)
        except KeyError as err:
            raise ValueError('No loader registered for "{}"'.format(config.feed_type)) from err

        return loader

    def create_any_loader(self, writers: List[W]) -> L:
        for writer in writers:
            if writer.config.feed_type in self._loaders:
                loader_config = parse_obj_as(FeedFileConfig, writer.config)
                return self.create_loader(loader_config)

        raise ValueError('Could not create loader from given writers!')


class JSONFeedFileLoader(AbstractFeedFileLoader):
    """Load feed from JSON-Feed file."""

    async def get_feed_items(self) -> List[FeedItem]:
        """Returns feed items of JSON-Feed if feed exists."""

        if exists(self._config.path):
            feed = await self._load_from_file()
            return parse_obj_as(List[FeedItem], feed['items'])
        else:
            return []

    async def get_feed_meta(self) -> Optional[FeedMeta]:
        """Return feed meta information of JSON-Feed if feed exists."""

        if exists(self._config.path):
            feed = await self._load_from_file()
            return parse_obj_as(FeedMeta, feed)

    async def _load_from_file(self) -> Dict:
        """Load JSON-Feed from file."""

        try:
            async with aiofiles.open(self._config.path, 'r', encoding='utf-8') as fd:
                feed_json = await fd.read()

            feed = json.loads(feed_json)
        except IOError as err:
            raise FeedIOError('Could not read JSON file from "{}"!'.format(self._config.path)) from err
        except json.JSONDecodeError as err:
            raise FeedIOError('Could not decode JSON file!') from err

        return feed
