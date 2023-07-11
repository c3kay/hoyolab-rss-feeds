from datetime import datetime
from typing import List
from unittest.mock import MagicMock

import aiohttp
import pytest
import pytest_mock

from hoyolabrssfeeds import feeds
from hoyolabrssfeeds import models
from hoyolabrssfeeds.loaders import AbstractFeedFileLoader
from hoyolabrssfeeds.writers import AbstractFeedFileWriter
from hoyolabrssfeeds.writers import JSONFeedFileWriter


def test_game_feed_was_updated(
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
):
    feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)

    assert not feed.was_updated


def test_same_path_warning(
    feed_meta: models.FeedMeta,
    mocked_loader: MagicMock,
    json_feed_file_writer_config: models.FeedFileWriterConfig,
):
    writer = JSONFeedFileWriter(json_feed_file_writer_config)
    duplicate_writers = [writer, writer]

    with pytest.warns(UserWarning, match="identical paths"):
        feeds.GameFeed(feed_meta, duplicate_writers, mocked_loader)


def test_from_config(feed_config: models.FeedConfig):
    game_feed = feeds.GameFeed.from_config(feed_config)

    assert game_feed._feed_meta == feed_config.feed_meta

    for writer in game_feed._feed_writers:
        assert issubclass(type(writer), AbstractFeedFileWriter)

    writer_configs = [writer.config for writer in game_feed._feed_writers]
    assert writer_configs == feed_config.writer_configs

    assert issubclass(type(game_feed._feed_loader), AbstractFeedFileLoader)
    assert game_feed._feed_loader.config == feed_config.loader_config


def test_from_config_no_loader(feed_config_no_loader: models.FeedConfig):
    game_feed = feeds.GameFeed.from_config(feed_config_no_loader)

    assert game_feed._feed_loader is not None
    assert issubclass(type(game_feed._feed_loader), AbstractFeedFileLoader)


def test_init_no_loader(
    feed_meta: models.FeedMeta,
    json_feed_file_writer_config: models.FeedFileWriterConfig,
):
    writers = [JSONFeedFileWriter(json_feed_file_writer_config)]
    game_feed = feeds.GameFeed(feed_meta, writers)

    assert game_feed._feed_loader.config.feed_type == models.FeedType.JSON


async def test_category_feed_new_item(
    mocker: pytest_mock.MockFixture,
    client_session: aiohttp.ClientSession,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
    feed_item: models.FeedItem,
):
    feed_meta.category_size = 2

    new_item = feed_item.copy()
    new_item.id += 1
    new_item.published = datetime.now()
    new_item.updated = datetime.now()

    mocked_metas = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_latest_item_metas",
        spec=True,
        return_value=[
            models.FeedItemMeta(id=new_item.id, last_modified=new_item.updated),
            models.FeedItemMeta(id=feed_item.id, last_modified=feed_item.updated),
        ],
    )

    mocked_item = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_feed_item",
        spec=True,
        return_value=new_item,
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)
    updated_feed = await game_feed._update_category_feed(
        client_session, models.FeedItemCategory.INFO, [feed_item]
    )

    mocked_metas.assert_awaited()
    mocked_metas.assert_called_once()

    # only the new item should be fetched
    mocked_item.assert_awaited()
    mocked_item.assert_called_once()

    assert game_feed.was_updated

    # since the new item should be the latest, it needs to be the first in list
    # -> indirect check of sorting
    assert updated_feed == [new_item, feed_item]


async def test_category_feed_updated_item(
    mocker: pytest_mock.MockFixture,
    client_session: aiohttp.ClientSession,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
    feed_item: models.FeedItem,
):
    feed_meta.category_size = 2

    updated_item = feed_item.copy()
    updated_item.updated = datetime.now().astimezone()

    other_item = feed_item.copy()
    other_item.id += 1

    mocked_metas = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_latest_item_metas",
        spec=True,
        return_value=[
            models.FeedItemMeta(id=other_item.id, last_modified=other_item.updated),
            models.FeedItemMeta(id=updated_item.id, last_modified=updated_item.updated),
        ],
    )

    mocked_item = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_feed_item",
        spec=True,
        return_value=updated_item,
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)
    updated_feed = await game_feed._update_category_feed(
        client_session, models.FeedItemCategory.INFO, [other_item, feed_item]
    )

    mocked_metas.assert_awaited()
    mocked_metas.assert_called_once()

    # only the updated item should be fetched
    mocked_item.assert_awaited()
    mocked_item.assert_called_once()

    assert game_feed.was_updated

    # feed is sorted by ids even if an item was updated
    assert updated_feed == [other_item, updated_item]


async def test_category_feed_unchanged(
    mocker: pytest_mock.MockFixture,
    client_session: aiohttp.ClientSession,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
    feed_item: models.FeedItem,
):
    mocked_metas = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_latest_item_metas",
        spec=True,
        return_value=[
            models.FeedItemMeta(id=feed_item.id, last_modified=feed_item.updated)
        ],
    )

    mocked_item = mocker.patch(
        "hoyolabrssfeeds.feeds.HoyolabNews.get_feed_item", spec=True
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)
    updated_feed = await game_feed._update_category_feed(
        client_session, models.FeedItemCategory.INFO, [feed_item]
    )

    mocked_metas.assert_awaited()
    mocked_metas.assert_called_once()

    mocked_item.assert_not_called()

    assert not game_feed.was_updated

    assert updated_feed == [feed_item]


async def test_create_feed(
    mocker: pytest_mock.MockFixture,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
    category_feeds: List[List[models.FeedItem]],
    combined_feed: List[models.FeedItem],
):
    mocked_update_feed = mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed._update_category_feed",
        spec=True,
        side_effect=category_feeds,
    )

    mocked_was_updated = mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed._was_updated",
        new_callable=mocker.PropertyMock,
        create=True,
        return_value=True,
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)

    # no client session given to test local session in method
    await game_feed.create_feed()

    mocked_loader.get_feed_items.assert_awaited()
    mocked_loader.get_feed_items.assert_called_once()

    mocked_update_feed.assert_awaited()
    mocked_update_feed.assert_called()

    mocked_was_updated.assert_called()

    for writer in mocked_writers:
        writer.write_feed.assert_called_with(feed_meta, combined_feed)


async def test_create_feed_unchanged(
    mocker: pytest_mock.MockFixture,
    client_session: aiohttp.ClientSession,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
    category_feeds: List[List[models.FeedItem]],
    combined_feed: List[models.FeedItem],
):
    # set known feed items from file
    mocked_loader.get_feed_items.return_value = combined_feed

    mocked_update_feed = mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed._update_category_feed",
        spec=True,
        side_effect=category_feeds,
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)

    await game_feed.create_feed(client_session)

    mocked_loader.get_feed_items.assert_awaited()
    mocked_loader.get_feed_items.assert_called_once()

    mocked_update_feed.assert_awaited()
    mocked_update_feed.assert_called()

    for writer in mocked_writers:
        writer.write_feed.assert_not_called()


async def test_create_feed_one_category(
    mocker: pytest_mock.MockFixture,
    client_session: aiohttp.ClientSession,
    feed_meta: models.FeedMeta,
    feed_item: models.FeedItem,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
):
    feed_meta.categories = [feed_item.category]

    mocked_update_feed = mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed._update_category_feed",
        spec=True,
        return_value=[feed_item],
    )

    # needed for writers to trigger
    mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed._was_updated",
        new_callable=mocker.PropertyMock,
        create=True,
        return_value=True,
    )

    game_feed = feeds.GameFeed(feed_meta, mocked_writers, mocked_loader)

    await game_feed.create_feed(client_session)

    mocked_update_feed.assert_awaited()
    mocked_update_feed.assert_called_once()

    for writer in mocked_writers:
        writer.write_feed.assert_called_with(feed_meta, [feed_item])


def test_collection_from_config(
    feed_config: models.FeedConfig, feed_config_no_loader: models.FeedConfig
):
    # NOTE: there is currently no check for identical paths of multiple game feeds
    configs = [feed_config, feed_config_no_loader]

    collection = feeds.GameFeedCollection.from_configs(configs)

    assert len(collection._game_feeds) == len(configs)

    for feed, config in zip(collection._game_feeds, configs):
        assert feed._feed_meta == config.feed_meta

        writer_configs = [w.config for w in feed._feed_writers]
        assert writer_configs == config.writer_configs

        if config.loader_config is not None:
            assert feed._feed_loader.config == config.loader_config


async def test_create_feed_collections(
    mocker: pytest_mock.MockFixture,
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
):
    mocked_create = mocker.patch(
        "hoyolabrssfeeds.feeds.GameFeed.create_feed", spec=True
    )

    collection = feeds.GameFeedCollection(
        [feed_meta, feed_meta],
        [mocked_writers, mocked_writers],
        [mocked_loader, mocked_loader],
    )

    await collection.create_feeds()

    mocked_create.assert_awaited()
    mocked_create.assert_called()


async def test_invalid_feed_collection(
    feed_meta: models.FeedMeta,
    mocked_writers: List[MagicMock],
    mocked_loader: MagicMock,
):
    with pytest.raises(ValueError):
        feeds.GameFeedCollection(
            [feed_meta, feed_meta],
            [mocked_writers],
            [mocked_loader, mocked_loader, mocked_loader],
        )
