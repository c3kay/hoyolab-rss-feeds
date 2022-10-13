import json
from abc import ABCMeta
from abc import abstractmethod
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import TypeVar
from xml.dom import minidom

import aiofiles

from .errors import FeedIOError
from .models import FeedFileWriterConfig
from .models import FeedItem
from .models import FeedMeta
from .models import FeedType


class AbstractFeedFileWriter(metaclass=ABCMeta):
    """ABC for feed file writing functionality."""

    def __init__(self, config: FeedFileWriterConfig):
        self._config = config

    @property
    def config(self) -> FeedFileWriterConfig:
        return self._config

    @abstractmethod
    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]):
        """Write feed to file, device etc."""
        pass


# define type for subclasses of AbstractFeedFileWriter
W = TypeVar('W', bound=AbstractFeedFileWriter)


class FeedFileWriterFactory:
    """Factory for creating specific FeedFileWriters."""

    def __init__(self):
        self._writers = {
            FeedType.JSON: JSONFeedFileWriter,
            FeedType.ATOM: AtomFeedFileWriter
        }

    @property
    def feed_types(self) -> Set[str]:
        """Set of feed types for which writers are registered."""
        return set(self._writers.keys())

    def create_writer(self, config: FeedFileWriterConfig) -> W:
        """Create feed writer for the specified feed type."""

        try:
            writer = self._writers[config.feed_type](config)
        except KeyError as err:
            raise ValueError('No writer registered for "{}"'.format(config.feed_type)) from err

        return writer


class JSONFeedFileWriter(AbstractFeedFileWriter):
    """Export feed as JSON-Feed format (https://www.jsonfeed.org/version/1.1/)."""

    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]):
        """Write feed to JSON file."""

        feed = {
            'version': 'https://jsonfeed.org/version/1.1',
            'title': feed_meta.title or '{} News'.format(feed_meta.game.name.title()),
            'language': feed_meta.language,
            'home_page_url': 'https://www.hoyolab.com/official/{}'.format(feed_meta.game),
        }

        if self._config.url:
            feed['feed_url'] = self._config.url

        if feed_meta.icon:
            feed['icon'] = feed_meta.icon

        feed['items'] = [self.create_json_feed_item(item) for item in feed_items]

        try:
            feed_json = json.dumps(feed)

            async with aiofiles.open(self._config.path, 'w', encoding='utf-8') as fd:
                await fd.write(feed_json)
        except IOError as err:
            raise FeedIOError('Could not write JSON file to "{}"!'.format(self._config.path)) from err
        except TypeError as err:
            raise FeedIOError('Could not parse feed to JSON!') from err

    @staticmethod
    def create_json_feed_item(item: FeedItem) -> Dict:
        """Convert FeedItem to JSON-Feed item."""

        json_item = {
            'id': str(item.id),
            'url': 'https://www.hoyolab.com/article/{}'.format(item.id),
            'title': item.title,
            'authors': [{'name': item.author}],
            'tags': [item.category.name.title()],
            'content_html': item.content,
            'date_published': item.published.astimezone().isoformat()
        }

        if item.updated:
            json_item['date_updated'] = item.updated

        if item.image:
            json_item['image'] = item.image

        return json_item


class AtomFeedFileWriter(AbstractFeedFileWriter):
    """Export feed as Atom format (https://validator.w3.org/feed/docs/atom.html)."""

    def __init__(self, config: FeedFileWriterConfig):
        super().__init__(config)
        self._doc: minidom.Document = minidom.getDOMImplementation().createDocument(None, 'feed', None)

    async def write_feed(self, feed_meta: FeedMeta, feed_items: List[FeedItem]):
        """Write feed to Atom file."""

        root = self._doc.documentElement

        # workaround...
        root.setAttribute('xmlns', 'http://www.w3.org/2005/Atom')
        root.setAttribute('xml:lang', feed_meta.language)

        self._append_text_node(root, 'id', 'tag:hoyolab.com,2021:/official/{}'.format(feed_meta.game))
        self._append_text_node(root, 'title', feed_meta.title or '{} News'.format(feed_meta.game.name.title()))
        self._append_text_node(root, 'updated', datetime.now().astimezone().isoformat())
        self._append_attr_node(root, 'link', {'href': 'https://www.hoyolab.com/official/{}'.format(feed_meta.game),
                                              'rel': 'alternate', 'type': 'text/html'})

        if self._config.url:
            self._append_attr_node(root, 'link', {'href': self._config.url, 'rel': 'self',
                                                  'type': 'application/atom+xml'})

        if feed_meta.icon:
            self._append_text_node(root, 'icon', feed_meta.icon)

        for item in feed_items:
            entry = self.create_atom_feed_item(item)
            root.appendChild(entry)

        try:
            async with aiofiles.open(self._config.path, 'w', encoding='utf-8') as fd:
                await fd.write(self._doc.toxml())
        except IOError as err:
            raise FeedIOError('Could not write Atom file to "{}"!'.format(self._config.path)) from err

    def create_atom_feed_item(self, item: FeedItem) -> minidom.Element:
        """Convert FeedItem to Atom entry."""

        entry = self._doc.createElement('entry')

        published_day = item.published.astimezone().date().isoformat()
        updated = item.updated or item.published

        self._append_text_node(entry, 'id', 'tag:hoyolab.com,{}:{}'.format(published_day, item.id))
        self._append_text_node(entry, 'title', item.title)
        self._append_attr_node(entry, 'link', {'href': 'https://www.hoyolab.com/article/{}'.format(item.id),
                                               'rel': 'alternate', 'type': 'text/html'})
        self._append_attr_node(entry, 'category', {'term': item.category.name.title()})
        self._append_text_node(entry, 'published', item.published.astimezone().isoformat())
        self._append_text_node(entry, 'updated', updated.astimezone().isoformat())

        author_el = self._doc.createElement('author')
        self._append_text_node(author_el, 'name', item.author)
        entry.appendChild(author_el)

        self._append_text_node(entry, 'content', item.content, attr={'type': 'html'})

        return entry

    def _append_text_node(
            self,
            parent: minidom.Element,
            name: str,
            text: str,
            attr: Optional[Dict] = None
    ):
        """Create XML element with text and optional attributes. Append to given element."""

        node = self._doc.createElement(name)
        node.appendChild(self._doc.createTextNode(text))

        if attr:
            for key, val in attr.items():
                node.setAttribute(key, val)

        parent.appendChild(node)

    def _append_attr_node(
            self,
            parent: minidom.Element,
            name: str,
            attr: Dict
    ):
        """Create XML element with only attributes and append to given element."""

        node = self._doc.createElement(name)

        for key, val in attr.items():
            node.setAttribute(key, val)

        parent.appendChild(node)
