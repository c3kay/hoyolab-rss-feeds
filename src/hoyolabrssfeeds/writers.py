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

from .errors import FeedIOError
from .models import FeedFileWriterConfig
from .models import FeedItem
from .models import FeedMeta
from .models import FeedType


class AbstractFeedFileWriter(metaclass=ABCMeta):
    """ABC for feed file writing functionality."""

    def __init__(self, config: FeedFileWriterConfig) -> None:
        self._config = config

    @property
    def config(self) -> FeedFileWriterConfig:
        """Returns the config of feed writer."""
        return self._config

    @abstractmethod
    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]) -> None:
        """Write feed to file."""
        pass


class FeedFileWriterFactory:
    """Factory for creating specific feed writers."""

    def __init__(self) -> None:
        self._writers = {
            FeedType.JSON: JSONFeedFileWriter,
            FeedType.ATOM: AtomFeedFileWriter,
        }

    @property
    def feed_types(self) -> Set[FeedType]:
        """Set of feed types for which writers are registered."""
        return set(self._writers.keys())

    def create_writer(self, config: FeedFileWriterConfig) -> AbstractFeedFileWriter:
        """Create a feed writer for the specified feed type."""
        return self._writers[config.feed_type](config)


class JSONFeedFileWriter(AbstractFeedFileWriter):
    """Export feed as JSON-Feed format (https://www.jsonfeed.org/version/1.1/)."""

    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]) -> None:
        """Write feed to JSON file."""

        feed: Dict[str, Any] = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": feed_meta.title or "{} News".format(feed_meta.game.name.title()),
            "language": str(feed_meta.language),
            "home_page_url": "https://www.hoyolab.com/circles/{}".format(
                feed_meta.game
            ),
        }

        if self.config.url is not None:
            feed["feed_url"] = str(self.config.url)

        if feed_meta.icon is not None:
            feed["icon"] = str(feed_meta.icon)

        feed["items"] = [self.create_json_feed_item(item) for item in feed_items]

        try:
            async with aiofiles.open(self.config.path, "w", encoding="utf-8") as fd:
                await fd.write(json.dumps(feed))
        except IOError as err:
            raise FeedIOError(
                'Could not write JSON file to "{}"!'.format(self.config.path)
            ) from err

    @staticmethod
    def create_json_feed_item(item: FeedItem) -> Dict[str, Any]:
        """Convert FeedItem to JSON-Feed item."""

        json_item = {
            "id": str(item.id),
            "url": "https://www.hoyolab.com/article/{}".format(item.id),
            "title": item.title,
            "authors": [{"name": item.author}],
            "tags": [item.category.name.title()],
            "content_html": item.content,
            "date_published": item.published.astimezone().isoformat(),
        }

        if item.updated is not None:
            json_item["date_modified"] = item.updated.astimezone().isoformat()

        if item.image is not None:
            json_item["image"] = str(item.image)

        return json_item


class AtomFeedFileWriter(AbstractFeedFileWriter):
    """Export feed as Atom format (https://validator.w3.org/feed/docs/atom.html)."""

    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]) -> None:
        """Write feed to Atom file."""

        # this is a workaround to avoid dealing with namespaces...
        meta_params = {
            "xmlns": "http://www.w3.org/2005/Atom",
            "xml:lang": str(feed_meta.language),
        }

        root = ElementTree.Element("feed", meta_params)

        id_str = "tag:hoyolab.com,2021:/official/{}".format(feed_meta.game)
        ElementTree.SubElement(root, "id").text = id_str

        title_str = feed_meta.title or "{} News".format(feed_meta.game.name.title())
        ElementTree.SubElement(root, "title").text = title_str

        updated_str = datetime.now().astimezone().isoformat()
        ElementTree.SubElement(root, "updated").text = updated_str

        ElementTree.SubElement(
            root,
            "link",
            {
                "href": "https://www.hoyolab.com/circles/{}".format(feed_meta.game),
                "rel": "alternate",
                "type": "text/html",
            },
        )

        if self.config.url:
            ElementTree.SubElement(
                root,
                "link",
                {
                    "href": self.config.url,
                    "rel": "self",
                    "type": "application/atom+xml",
                },
            )

        if feed_meta.icon:
            ElementTree.SubElement(root, "icon").text = feed_meta.icon

        entries = self.create_atom_feed_entries(feed_items)
        root.extend(entries)

        xml_bytes = ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)

        try:
            async with aiofiles.open(self.config.path, "wb") as fd:
                await fd.write(xml_bytes)
        except IOError as err:
            raise FeedIOError(
                'Could not write Atom file to "{}"!'.format(self.config.path)
            ) from err

    @staticmethod
    def create_atom_feed_entries(
        feed_items: List[FeedItem],
    ) -> List[ElementTree.Element]:
        """Create Atom feed entries from given feed items."""

        entries = []

        for item in feed_items:
            entry = ElementTree.Element("entry")

            published_day = item.published.astimezone().date().isoformat()
            id_str = "tag:hoyolab.com,{}:{}".format(published_day, item.id)
            ElementTree.SubElement(entry, "id").text = id_str

            ElementTree.SubElement(entry, "title").text = item.title

            ElementTree.SubElement(
                entry,
                "link",
                {
                    "href": "https://www.hoyolab.com/article/{}".format(item.id),
                    "rel": "alternate",
                    "type": "text/html",
                },
            )

            ElementTree.SubElement(
                entry, "category", {"term": item.category.name.title()}
            )

            published_str = item.published.astimezone().isoformat()
            ElementTree.SubElement(entry, "published").text = published_str

            updated_str = (item.updated or item.published).astimezone().isoformat()
            ElementTree.SubElement(entry, "updated").text = updated_str

            author = ElementTree.SubElement(entry, "author")
            ElementTree.SubElement(author, "name").text = item.author

            ElementTree.SubElement(
                entry, "content", {"type": "html"}
            ).text = item.content

            entries.append(entry)

        return entries
