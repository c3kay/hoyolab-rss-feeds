import asyncio
from datetime import datetime
from pathlib import Path
from platform import system
from typing import List

import pytest
from aiohttp import ClientSession
from pydantic import HttpUrl
from pydantic import parse_obj_as

from hoyolabrssfeeds import models


@pytest.fixture(scope='session')
def event_loop():
    if system() == 'Windows':
        # default policy not working on windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    return asyncio.get_event_loop()


@pytest.fixture(scope='session')
async def client_session(event_loop):
    async with ClientSession(loop=event_loop, raise_for_status=True) as cs:
        yield cs


@pytest.fixture
def json_path(tmpdir) -> Path:
    return Path('{}/json_feed.json'.format(tmpdir))


@pytest.fixture
def atom_path(tmpdir) -> Path:
    return Path('{}/atom_feed.xml'.format(tmpdir))


@pytest.fixture
def json_feed_file_writer_config(json_path) -> models.FeedFileWriterConfig:
    return models.FeedFileWriterConfig(
        feed_type=models.FeedType.JSON,
        path=json_path,
        url=parse_obj_as(HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def atom_feed_file_writer_config(atom_path) -> models.FeedFileWriterConfig:
    return models.FeedFileWriterConfig(
        feed_type=models.FeedType.ATOM,
        path=atom_path,
        url=parse_obj_as(HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def empty_json_feed_file_config(json_path) -> models.FeedFileConfig:
    return models.FeedFileConfig(
        feed_type=models.FeedType.JSON,
        path=json_path
    )


@pytest.fixture
def json_feed_file_config(shared_datadir) -> models.FeedFileConfig:
    return models.FeedFileConfig(
        feed_type=models.FeedType.JSON,
        path=(shared_datadir / 'json_feed.json')
    )


@pytest.fixture
def feed_item() -> models.FeedItem:
    return models.FeedItem(
        id=42,
        title='Test Article',
        author='John Doe',
        content='<p>Hello World!</p>',
        category=models.PostCategory.INFO,
        published=datetime(2022, 10, 3, 16),
        updated=datetime(2022, 10, 3, 18),
        image=parse_obj_as(HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def feed_item_list(feed_item) -> List[models.FeedItem]:
    return [feed_item]


@pytest.fixture
def feed_meta() -> models.FeedMeta:
    return models.FeedMeta(
        game=models.Game.GENSHIN,
        category_size=1,
        title='Example Feed',
        icon=parse_obj_as(HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def feed_config(
        feed_meta,
        json_feed_file_writer_config,
        empty_json_feed_file_config
) -> models.FeedConfig:
    return models.FeedConfig(
        feed_meta=feed_meta,
        writer_configs=[json_feed_file_writer_config],
        loader_config=empty_json_feed_file_config
    )


@pytest.fixture
def feed_config_no_loader(
        feed_meta,
        json_feed_file_writer_config,
        json_feed_file_config
) -> models.FeedConfig:
    return models.FeedConfig(
        feed_meta=feed_meta,
        writer_configs=[json_feed_file_writer_config]
    )
