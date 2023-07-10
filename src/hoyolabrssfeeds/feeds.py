import asyncio
import warnings
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

import aiohttp

from .hoyolab import HoyolabNews
from .loaders import AbstractFeedFileLoader
from .loaders import FeedFileLoaderFactory
from .models import FeedConfig
from .models import FeedItem
from .models import FeedItemCategory
from .models import FeedMeta
from .writers import AbstractFeedFileWriter
from .writers import FeedFileWriterFactory

# used for class-methods
_GF = TypeVar("_GF", bound="GameFeed")
_GFC = TypeVar("_GFC", bound="GameFeedCollection")


class GameFeed:
    """Feed generator for a single game."""

    def __init__(
        self,
        feed_meta: FeedMeta,
        feed_writers: List[AbstractFeedFileWriter],
        feed_loader: Optional[AbstractFeedFileLoader] = None,
    ) -> None:
        # warn if identical paths for writers are found
        writer_paths = [str(writer.config.path) for writer in feed_writers]
        if len(writer_paths) != len(set(writer_paths)):
            warnings.warn(
                "Writers for {} game feed contain identical paths".format(
                    feed_meta.game.name.title()
                )
            )

        if feed_loader is None:
            loader_factory = FeedFileLoaderFactory()
            feed_loader = loader_factory.create_any_loader(feed_writers)

        self._feed_meta = feed_meta
        self._feed_writers = feed_writers
        self._feed_loader = feed_loader
        self._hoyolab = HoyolabNews(feed_meta.game, feed_meta.language)
        self._was_updated = False

    @property
    def was_updated(self) -> bool:
        """Flag if the feed has been updated after a create_feed() call."""
        return self._was_updated

    @classmethod
    def from_config(cls: Type[_GF], feed_config: FeedConfig) -> _GF:
        """Create an instance via a feed config."""

        writer_factory = FeedFileWriterFactory()
        writers = [
            writer_factory.create_writer(writer_config)
            for writer_config in feed_config.writer_configs
        ]

        loader_factory = FeedFileLoaderFactory()
        loader: AbstractFeedFileLoader
        if feed_config.loader_config:
            loader = loader_factory.create_loader(feed_config.loader_config)
        else:
            loader = loader_factory.create_any_loader(writers)

        return cls(feed_config.feed_meta, writers, loader)

    async def create_feed(
        self, session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        """Create or update a feed and write it to files."""

        local_session = session or aiohttp.ClientSession()
        feed_categories = self._feed_meta.categories or [c for c in FeedItemCategory]
        self._was_updated = False

        feed_items = await self._feed_loader.get_feed_items()

        try:
            category_feeds = await asyncio.gather(
                *[
                    self._update_category_feed(
                        local_session,
                        category,
                        [item for item in feed_items if item.category == category],
                    )
                    for category in feed_categories
                ]
            )
        finally:
            if session is None:
                await local_session.close()

        if self._was_updated:
            combined_feed: List[FeedItem] = []
            for feed in category_feeds:
                combined_feed.extend(feed)

            # sort feed items descending by id -> latest at the top
            combined_feed.sort(key=lambda item: item.id, reverse=True)

            await asyncio.gather(
                *[
                    writer.write_feed(self._feed_meta, combined_feed)
                    for writer in self._feed_writers
                ]
            )

    async def _update_category_feed(
        self,
        session: aiohttp.ClientSession,
        category: FeedItemCategory,
        category_items: List[FeedItem],
    ) -> List[FeedItem]:
        """Create or update a specific category feed."""

        known_ids = {
            item.id: item.published
            if item.updated is None
            else max(item.published, item.updated)
            for item in category_items
            if item.category == category
        }

        latest_item_metas = await self._hoyolab.get_latest_item_metas(
            session, category, self._feed_meta.category_size
        )

        new_or_outdated_ids = {
            item_meta.id
            for item_meta in latest_item_metas
            if item_meta.id not in known_ids
            or item_meta.last_modified > known_ids[item_meta.id]
        }

        if len(new_or_outdated_ids) > 0:
            # remove outdated items from feed because they will be re-fetched
            category_items = list(
                filter(lambda item: item.id not in new_or_outdated_ids, category_items)
            )

            fetched_items = await asyncio.gather(
                *[
                    self._hoyolab.get_feed_item(session, item_id)
                    for item_id in new_or_outdated_ids
                ]
            )

            category_items.extend(fetched_items)

            # cut off older items that exceed category_size
            category_items.sort(key=lambda item: item.id, reverse=True)
            category_items = category_items[: self._feed_meta.category_size]

            self._was_updated = True

        return category_items


class GameFeedCollection:
    """Collection of feed generators for multiple games."""

    def __init__(
        self,
        feed_metas: List[FeedMeta],
        feed_writers: List[List[AbstractFeedFileWriter]],
        feed_loaders: List[Optional[AbstractFeedFileLoader]],
    ) -> None:
        if not (len(feed_metas) == len(feed_writers) == len(feed_loaders)):
            raise ValueError("Parameter lists do not have the same length!")

        self._game_feeds = [
            GameFeed(meta, writer, loader)
            for meta, writer, loader in zip(feed_metas, feed_writers, feed_loaders)
        ]

    @classmethod
    def from_configs(cls: Type[_GFC], feed_configs: List[FeedConfig]) -> _GFC:
        """Create an instance via feed configs."""

        metas: List[FeedMeta] = []
        writers: List[List[AbstractFeedFileWriter]] = []
        loaders: List[Optional[AbstractFeedFileLoader]] = []

        for feed_config in feed_configs:
            metas.append(feed_config.feed_meta)

            writer_factory = FeedFileWriterFactory()
            writers_configs = [
                writer_factory.create_writer(conf)
                for conf in feed_config.writer_configs
            ]
            writers.append(writers_configs)

            loader_factory = FeedFileLoaderFactory()
            loader = (
                loader_factory.create_loader(feed_config.loader_config)
                if feed_config.loader_config
                else None
            )
            loaders.append(loader)

        return cls(metas, writers, loaders)

    async def create_feeds(
        self, session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        """Create or update a feed and write it to files."""

        local_session = session or aiohttp.ClientSession()

        try:
            await asyncio.gather(
                *[feed.create_feed(local_session) for feed in self._game_feeds]
            )
        finally:
            if session is None:
                await local_session.close()
