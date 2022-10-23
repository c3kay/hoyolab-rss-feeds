import asyncio
from datetime import datetime
from datetime import timezone
from pathlib import Path
from platform import system
from re import fullmatch
from typing import Dict
from typing import List

import pytest
from aiohttp import ClientSession
from pydantic import HttpUrl
from pydantic import parse_obj_as

from hoyolabrssfeeds import models


# ---- SESSION FIXTURES ----

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


# ---- TEST FIXTURES ----

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
        category=models.FeedItemCategory.INFO,
        published=datetime(2022, 10, 3, 16, tzinfo=timezone.utc),
        updated=datetime(2022, 10, 3, 18, tzinfo=timezone.utc),
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


# ---- ASSERTION HELPERS ----
# https://docs.pytest.org/en/6.2.x/assert.html#assertion-introspection-details

def validate_hoyolab_post(post: Dict, is_full_post: bool):
    assert type(post['post']['post_id']) is str
    assert fullmatch(r'\d+', post['post']['post_id']) is not None

    assert type(post['post']['created_at']) is int
    assert post['post']['created_at'] > 0

    assert type(post['last_modify_time']) is int
    assert post['last_modify_time'] >= 0

    if is_full_post:
        assert type(post['post']['official_type']) is int
        assert post['post']['official_type'] in [c.value for c in models.FeedItemCategory]

        assert type(post['user']['nickname']) is str
        assert len(post['user']['nickname']) > 0

        assert type(post['post']['content']) is str
        assert len(post['post']['content']) > 0

        assert type(post['post']['subject']) is str
        assert len(post['post']['subject']) > 0

        assert type(post['image_list']) is list
        assert len(post['image_list']) >= 0
