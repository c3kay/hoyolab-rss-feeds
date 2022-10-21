import json
from abc import ABCMeta
from abc import abstractmethod
from os.path import exists
from typing import Dict
from typing import List
from typing import Set
from typing import TypeVar
from typing import Type

import aiofiles
from pydantic import parse_obj_as

from .errors import FeedIOError
from .models import FeedFileConfig
from .models import FeedItem
from .models import FeedType
from .models import PostCategory
from .writers import W


class AbstractFeedFileLoader(metaclass=ABCMeta):
    """ABC for feed file loading functionality."""

    def __init__(self, config):
        self._config = config

    @property
    def config(self) -> FeedFileConfig:
        """Returns the config of the feed loader."""
        return self._config

    @abstractmethod
    async def get_feed_items(self) -> List[FeedItem]:
        """Get the items of the feed or an empty list if they do not exist."""
        pass


L = TypeVar('L', bound=AbstractFeedFileLoader)


class FeedFileLoaderFactory:
    """Factory for creating specific FeedFileLoaders."""

    def __init__(self):
        self._loaders = {
            str(FeedType.JSON): JSONFeedFileLoader
            # TODO: add atom loader
        }

    @property
    def feed_types(self) -> Set[str]:
        """Set of feed types for which writers are registered."""
        return set(self._loaders.keys())

    def register_loader(self, feed_type: str, loader: Type[L]):
        """Register feed loader for a new feed type."""

        if feed_type in self._loaders:
            raise ValueError('Feed loader already exists for feed type "{}"!'.format(feed_type))

        self._loaders[feed_type] = loader

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
            feed_items = []

            try:
                for item in feed['items']:
                    category = PostCategory.from_str(item['tags'][0])

                    item_dict = {
                        'id': item['id'],
                        'title': item['title'],
                        'author': item['authors'][0]['name'],
                        'content': item['content_html'],
                        'category': category,
                        'published': item['date_published']
                    }

                    if 'date_modified' in item:
                        item_dict['updated'] = item['date_modified']

                    if 'image' in item:
                        item_dict['image'] = item['image']

                    feed_items.append(item_dict)

                    return parse_obj_as(List[FeedItem], feed_items)
            except KeyError as err:
                raise FeedIOError('Could not find required key in JSON feed!') from err
            except ValueError as err:
                raise FeedIOError('Found unexpected value in JSON feed!') from err
        else:
            return []

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
