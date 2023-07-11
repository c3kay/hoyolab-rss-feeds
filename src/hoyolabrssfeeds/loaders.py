import json
from abc import ABCMeta
from abc import abstractmethod
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Set
from xml.etree import ElementTree

import aiofiles
import pydantic

from .errors import FeedFormatError
from .errors import FeedIOError
from .models import FeedFileConfig
from .models import FeedItem
from .models import FeedItemCategory
from .models import FeedType
from .writers import AbstractFeedFileWriter
from .writers import JSONFeedFileWriter


class AbstractFeedFileLoader(metaclass=ABCMeta):
    """ABC for feed file loading functionality."""

    def __init__(self, config: FeedFileConfig) -> None:
        self._config = config

    @property
    def config(self) -> FeedFileConfig:
        """Returns the config of the feed loader."""
        return self._config

    @abstractmethod
    async def get_feed_items(self) -> List[FeedItem]:
        """Get the items of the feed or an empty list if they do not exist."""
        pass


class FeedFileLoaderFactory:
    """Factory for creating specific feed loaders."""

    def __init__(self) -> None:
        self._loaders = {
            FeedType.JSON: JSONFeedFileLoader,
            FeedType.ATOM: AtomFeedFileLoader,
        }

    @property
    def feed_types(self) -> Set[FeedType]:
        """Set of feed types for which writers are registered."""
        return set(self._loaders.keys())

    def create_loader(self, config: FeedFileConfig) -> AbstractFeedFileLoader:
        """Create feed loader for the specified feed type."""
        return self._loaders[config.feed_type](config)

    def create_any_loader(
        self, writers: List[AbstractFeedFileWriter]
    ) -> AbstractFeedFileLoader:
        """Create a suitable loader from given writers."""

        # prefer json loader if available
        for writer in writers:
            if isinstance(writer, JSONFeedFileWriter):
                json_config = pydantic.parse_obj_as(FeedFileConfig, writer.config)
                return self.create_loader(json_config)

        for writer in writers:
            if writer.config.feed_type in self._loaders:
                loader_config = pydantic.parse_obj_as(FeedFileConfig, writer.config)
                return self.create_loader(loader_config)

        raise ValueError("Could not create loader from given writers!")


class JSONFeedFileLoader(AbstractFeedFileLoader):
    """Load feed from JSON-Feed format (https://www.jsonfeed.org/version/1.1/)."""

    async def get_feed_items(self) -> List[FeedItem]:
        """Returns feed items of JSON-Feed if feed exists."""

        if self.config.path.exists():
            feed_items = []
            feed = await self._load_from_file()

            try:
                for item in feed["items"]:
                    category = FeedItemCategory.from_str(item["tags"][0])

                    item_dict = {
                        "id": item["id"],
                        "title": item["title"],
                        "author": item["authors"][0]["name"],
                        "content": item["content_html"],
                        "category": category,
                        "published": item["date_published"],
                    }

                    if "date_modified" in item:
                        item_dict["updated"] = item["date_modified"]

                    if "image" in item:
                        item_dict["image"] = item["image"]

                    feed_items.append(item_dict)
            except KeyError as err:
                raise FeedFormatError(
                    "Could not find required key in JSON feed!"
                ) from err
            except ValueError as err:
                raise FeedFormatError("Could not load JSON feed items!") from err

            return pydantic.parse_obj_as(List[FeedItem], feed_items)
        else:
            return []

    async def _load_from_file(self) -> Dict[str, Any]:
        """Load JSON-Feed from file."""

        try:
            async with aiofiles.open(self.config.path, "r") as fd:
                feed_json = await fd.read()

            feed: Dict[str, Any] = json.loads(feed_json)
        except IOError as err:
            raise FeedIOError(
                'Could not read JSON file from "{}"!'.format(self.config.path)
            ) from err
        except json.JSONDecodeError as err:
            raise FeedFormatError("Could not decode JSON file!") from err

        return feed


class AtomFeedFileLoader(AbstractFeedFileLoader):
    """Load feed from Atom format (https://validator.w3.org/feed/docs/atom.html)."""

    async def get_feed_items(self) -> List[FeedItem]:
        """Returns feed items of Atom feed if feed exists."""

        if self.config.path.exists():
            feed_items = []
            root = await self._load_from_file()

            for entry in root.findall("entry"):
                id_str = entry.findtext("id")
                item_id = id_str.rpartition(":")[2] if id_str is not None else None

                category_node = entry.find("category")
                try:
                    category = (
                        FeedItemCategory.from_str(category_node.get("term", default=""))
                        if category_node is not None
                        else None
                    )
                except ValueError as err:
                    raise FeedFormatError("Could not load Atom feed entries!") from err

                published_str = entry.findtext("published")
                published = (
                    datetime.fromisoformat(published_str)
                    if published_str is not None
                    else None
                )

                updated_str = entry.findtext("updated")
                updated = (
                    datetime.fromisoformat(updated_str)
                    if updated_str is not None
                    else None
                )

                item_dict = {
                    "id": item_id,
                    "title": entry.findtext("title"),
                    "author": entry.findtext("author/name"),
                    "content": entry.findtext("content"),
                    "category": category,
                    "published": published,
                    "updated": updated,
                }

                feed_items.append(item_dict)

            try:
                return pydantic.parse_obj_as(List[FeedItem], feed_items)
            except pydantic.ValidationError as err:
                raise FeedFormatError("Could not load Atom feed entries!") from err
        else:
            return []

    async def _load_from_file(self) -> ElementTree.Element:
        """Load Atom feed from file."""

        try:
            async with aiofiles.open(self.config.path, "r") as fd:
                feed_str = await fd.read()

            # removing default namespace declaration from xml because it makes
            # parsing MUCH easier
            feed_str = feed_str.replace(' xmlns="http://www.w3.org/2005/Atom"', "", 1)

            root = ElementTree.fromstring(feed_str)
        except IOError as err:
            raise FeedIOError(
                'Could not read Atom file from "{}"!'.format(self.config.path)
            ) from err
        except ElementTree.ParseError as err:
            raise FeedFormatError("Could not parse Atom file!") from err

        return root
