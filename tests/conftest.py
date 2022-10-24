import asyncio
import re
from datetime import datetime
from pathlib import Path
from platform import system
from typing import Dict
from typing import List
from unittest.mock import MagicMock

import aiohttp
import pydantic
import pytest
import pytest_mock

from hoyolabrssfeeds import models
from hoyolabrssfeeds.loaders import AbstractFeedFileLoader
from hoyolabrssfeeds.writers import AbstractFeedFileWriter


# ---- SESSION FIXTURES ----

@pytest.fixture(scope='session')
def event_loop():
    if system() == 'Windows':
        # default policy not working on windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    return asyncio.get_event_loop()


@pytest.fixture(scope='session')
async def client_session(event_loop):
    async with aiohttp.ClientSession(loop=event_loop, raise_for_status=True) as cs:
        yield cs


# ---- PATH FIXTURES ----

@pytest.fixture
def json_path(tmp_path) -> Path:
    return tmp_path / Path('json_feed.json')


@pytest.fixture
def atom_path(tmp_path) -> Path:
    return tmp_path / Path('atom_feed.xml')


@pytest.fixture
def config_path(tmp_path) -> Path:
    return tmp_path / Path('feeds.toml')


# ---- MODEL FIXTURES ----

@pytest.fixture(params=[g for g in models.Game])
def game(request) -> models.Game:
    return request.param


@pytest.fixture(params=[c for c in models.FeedItemCategory])
def category(request) -> models.FeedItemCategory:
    return request.param


@pytest.fixture(params=[la for la in models.Language])
def language(request) -> models.Language:
    return request.param


# ---- CONFIG FIXTURES ----

@pytest.fixture
def json_feed_file_writer_config(json_path) -> models.FeedFileWriterConfig:
    return models.FeedFileWriterConfig(
        feed_type=models.FeedType.JSON,
        path=json_path,
        url=pydantic.parse_obj_as(pydantic.HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def atom_feed_file_writer_config(atom_path) -> models.FeedFileWriterConfig:
    return models.FeedFileWriterConfig(
        feed_type=models.FeedType.ATOM,
        path=atom_path,
        url=pydantic.parse_obj_as(pydantic.HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def json_feed_file_config(json_path) -> models.FeedFileConfig:
    return models.FeedFileConfig(
        feed_type=models.FeedType.JSON,
        path=json_path
    )


@pytest.fixture
def feed_config(
        feed_meta,
        json_feed_file_writer_config,
        json_feed_file_config
) -> models.FeedConfig:
    return models.FeedConfig(
        feed_meta=feed_meta,
        writer_configs=[json_feed_file_writer_config],
        loader_config=json_feed_file_config
    )


@pytest.fixture
def feed_config_no_loader(
        feed_meta,
        json_feed_file_writer_config
) -> models.FeedConfig:
    return models.FeedConfig(
        feed_meta=feed_meta,
        writer_configs=[json_feed_file_writer_config],
    )


@pytest.fixture
def toml_config_dict(
        feed_meta: models.FeedMeta,
        json_feed_file_writer_config,
        atom_feed_file_writer_config
) -> Dict:
    return {
        'category_size': feed_meta.category_size,
        'language': str(feed_meta.language),
        feed_meta.game.name.lower(): {
            'file': {
                str(models.FeedType.JSON): {
                    'path': str(json_feed_file_writer_config.path),
                    'url': str(json_feed_file_writer_config.url)
                }
            },
            'title': feed_meta.title,
            'icon': str(feed_meta.icon)
        },
        models.Game.ZENLESS.name.lower(): {
            'file': {
                str(models.FeedType.ATOM): {
                    'path': str(atom_feed_file_writer_config.path)
                }
            }
        }
    }


# ---- FEED FIXTURES ----

@pytest.fixture
def feed_item() -> models.FeedItem:
    return models.FeedItem(
        id=42,
        title='Test Article',
        author='John Doe',
        content='<p>Hello World!</p>',
        category=models.FeedItemCategory.INFO,
        published=datetime(2022, 10, 3, 16).astimezone(),
        updated=datetime(2022, 10, 3, 18).astimezone(),
        image=pydantic.parse_obj_as(pydantic.HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def feed_item_list(feed_item) -> List[models.FeedItem]:
    other_item = feed_item.copy()
    other_item.id -= 1
    return [feed_item, other_item]


@pytest.fixture
def feed_meta() -> models.FeedMeta:
    return models.FeedMeta(
        game=models.Game.GENSHIN,
        category_size=1,
        language=models.Language.GERMAN,
        title='Example Feed',
        icon=pydantic.parse_obj_as(pydantic.HttpUrl, 'https://example.org/')
    )


@pytest.fixture
def category_feeds(feed_item: models.FeedItem) -> List[List[models.FeedItem]]:
    cat_feeds = []
    for i, cat in enumerate(models.FeedItemCategory):
        item = feed_item.copy()
        item.id += i
        item.category = cat
        cat_feeds.append([item])

    return cat_feeds


@pytest.fixture
def combined_feed(category_feeds: List[List[models.FeedItem]]) -> List[models.FeedItem]:
    comb_feed = []
    for item_list in category_feeds:
        comb_feed.extend(item_list)
    comb_feed.sort(key=lambda x: x.id, reverse=True)

    return comb_feed


# ---- MOCK FIXTURES ----

@pytest.fixture
def mocked_loader(mocker: pytest_mock.MockFixture) -> MagicMock:
    loader = mocker.create_autospec(
        AbstractFeedFileLoader,
        instance=True
    )
    loader.get_feed_items = mocker.AsyncMock(return_value=[])

    return loader


@pytest.fixture
def mocked_writers(mocker: pytest_mock.MockFixture) -> List[MagicMock]:
    writer = mocker.create_autospec(
        AbstractFeedFileWriter,
        instance=True
    )

    return [writer]


# ---- ASSERTION HELPERS ----

# https://docs.pytest.org/en/6.2.x/assert.html#assertion-introspection-details

def validate_hoyolab_post(post: Dict, is_full_post: bool):
    assert type(post['post']['post_id']) is str
    assert re.fullmatch(r'\d+', post['post']['post_id']) is not None

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
