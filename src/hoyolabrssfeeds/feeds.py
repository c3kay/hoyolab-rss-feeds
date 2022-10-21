import asyncio
from typing import List
from typing import Optional
from warnings import warn

import aiohttp

from .errors import ConfigError
from .hoyolab import HoyolabNews
from .loaders import FeedFileLoaderFactory
from .loaders import L
from .models import FeedConfig
from .models import FeedItem
from .models import FeedMeta
from .models import PostCategory
from .writers import FeedFileWriterFactory
from .writers import W


class GameFeed:
    def __init__(
            self,
            feed_meta: FeedMeta,
            feed_writers: List[W],
            feed_loader: L
    ):
        # warn if identical paths for writers are found
        writer_paths = [str(writer.config.path) for writer in feed_writers]
        if len(writer_paths) != len(set(writer_paths)):
            warn('Writers for {} game feed contain identical paths'.format(feed_meta.game.name.title()))

        self._feed_meta = feed_meta
        self._feed_writers = feed_writers
        self._feed_loader = feed_loader
        self._hoyolab = HoyolabNews(feed_meta.game, feed_meta.language)
        self._was_updated = False

    @property
    def was_updated(self):
        return self._was_updated

    @classmethod
    def from_config(cls, feed_config: FeedConfig):
        try:
            writer_factory = FeedFileWriterFactory()
            writers = [
                writer_factory.create_writer(writer_config)
                for writer_config in feed_config.writer_configs
            ]

            loader_factory = FeedFileLoaderFactory()
            if feed_config.loader_config:
                loader = loader_factory.create_loader(feed_config.loader_config)
            else:
                loader = loader_factory.create_any_loader(writers)
        except ValueError as err:
            raise ConfigError('Could not create game feed from config!') from err

        return cls(feed_config.feed_meta, writers, loader)

    async def create_feed(self, session: Optional[aiohttp.ClientSession] = None):
        local_session = session or aiohttp.ClientSession()
        self._was_updated = False

        # load known feed items
        feed_items = await self._feed_loader.get_feed_items()

        category_feeds = await asyncio.gather(*[
            self._update_category_feed(
                category,
                [item for item in feed_items if item.category == category],
                local_session
            )
            for category in PostCategory
        ])

        if self._was_updated:
            # merge category feeds together
            combined_feed = []
            for feed in category_feeds:
                combined_feed.extend(feed)

            # sort feed items descending by id -> latest at the top
            combined_feed.sort(key=lambda item: item.id, reverse=True)

            # concurrently write to files
            await asyncio.gather(*[
                writer.write_feed(self._feed_meta, combined_feed)
                for writer in self._feed_writers
            ])

        if session is None:
            await local_session.close()

    async def _update_category_feed(
            self,
            category: PostCategory,
            category_items: List[FeedItem],
            session: aiohttp.ClientSession
    ) -> List[FeedItem]:
        known_ids = {
            item.id: max(item.published, (item.updated or 0))
            for item in category_items
            if item.category == category
        }

        latest_item_metas = await self._hoyolab.get_latest_item_metas(
            category,
            self._feed_meta.category_size
        )

        new_or_outdated_ids = {
            item_meta.id
            for item_meta in latest_item_metas
            if item_meta.id not in known_ids or item_meta.last_modified > known_ids[item_meta.id]
        }

        if len(new_or_outdated_ids) > 0:
            # remove outdated items from feed because they will be re-fetched
            category_items = list(filter(
                lambda item: item.id not in new_or_outdated_ids, category_items
            ))

            # concurrently fetch new and outdated items
            fetched_items = await asyncio.gather(*[
                self._hoyolab.get_feed_item(item_id, session)
                for item_id in new_or_outdated_ids
            ])

            # add fetched items to category feed
            category_items.extend(fetched_items)

            # cut off older items that exceed category_size
            category_items.sort(key=lambda item: item.id, reverse=True)
            category_items = category_items[:self._feed_meta.category_size]

            self._was_updated = True

        return category_items


class GameFeedCollection:
    def __init__(
            self,
            feed_metas: List[FeedMeta],
            feed_writers: List[List[W]],
            feed_loaders: List[L]
    ):
        if not (len(feed_metas) == len(feed_writers) == len(feed_loaders)):
            raise ValueError('Parameter lists do not have the same length!')

        self._game_feeds = [
            GameFeed(meta, writer, loader)
            for meta, writer, loader in zip(
                feed_metas,
                feed_writers,
                feed_loaders
            )
        ]

    @classmethod
    def from_configs(cls, feed_configs: List[FeedConfig]):
        metas = []
        writers = []
        loaders = []

        try:
            for feed_config in feed_configs:
                metas.append(feed_config.feed_meta)

                writer_factory = FeedFileWriterFactory()
                writers_configs = [
                    writer_factory.create_writer(conf)
                    for conf in feed_config.writer_configs
                ]
                writers.append(writers_configs)

                loader_factory = FeedFileLoaderFactory()
                if feed_config.loader_config:
                    loaders.append(loader_factory.create_loader(feed_config.loader_config))
                else:
                    loaders.append(loader_factory.create_any_loader(writers_configs))
        except ValueError as err:
            raise ConfigError('Could not create game feed collection from configs!') from err

        return cls(metas, writers, loaders)

    async def create_feeds(self, session: Optional[aiohttp.ClientSession] = None):
        local_session = session or aiohttp.ClientSession()

        await asyncio.gather(*[
            feed.create_feed(local_session)
            for feed in self._game_feeds
        ])

        if session is None:
            await local_session.close()
