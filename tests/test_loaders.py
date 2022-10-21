from pathlib import Path
from platform import system
from stat import S_IWRITE

import aiofiles
import pytest

from hoyolabrssfeeds import errors
from hoyolabrssfeeds import loaders
from hoyolabrssfeeds import models
from hoyolabrssfeeds import writers


def test_factory_feed_types():
    factory = loaders.FeedFileLoaderFactory()
    expected = {str(models.FeedType.JSON)}

    assert factory.feed_types == expected


def test_factory_create_loader(empty_json_feed_file_config: models.FeedFileConfig):
    factory = loaders.FeedFileLoaderFactory()
    json_loader = factory.create_loader(empty_json_feed_file_config)

    assert issubclass(type(json_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(json_loader, loaders.JSONFeedFileLoader)


def test_factory_create_any_loader(empty_json_feed_file_config: models.FeedFileConfig):
    json_writer = writers.JSONFeedFileWriter(empty_json_feed_file_config)
    factory = loaders.FeedFileLoaderFactory()
    json_loader = factory.create_any_loader([json_writer])

    assert issubclass(type(json_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(json_loader, loaders.JSONFeedFileLoader)


def test_factory_create_invalid_any_loader():
    factory = loaders.FeedFileLoaderFactory()

    with pytest.raises(ValueError):
        factory.create_any_loader([])


def test_factory_register_loader(json_path: Path):
    factory = loaders.FeedFileLoaderFactory()
    factory.register_loader('custom', loaders.JSONFeedFileLoader)

    assert 'custom' in factory.feed_types

    custom_config = models.FeedFileConfig(feed_type='custom', path=json_path)
    loader = factory.create_loader(custom_config)

    assert isinstance(loader, loaders.JSONFeedFileLoader)


def test_factory_register_duplicate_loader():
    factory = loaders.FeedFileLoaderFactory()

    with pytest.raises(ValueError):
        factory.register_loader(str(models.FeedType.JSON), loaders.JSONFeedFileLoader)


def test_json_feed_loader_config(empty_json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(empty_json_feed_file_config)

    assert loader.config == empty_json_feed_file_config


async def test_json_feed_loader(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    items = await loader.get_feed_items()

    # see ./data/json_feed.json
    assert len(items) == 1

    item = items.pop()

    assert item.id == 42
    assert item.author == 'John Doe'
    assert item.category == models.PostCategory.INFO

    # TODO: complete asserts for feed?


async def test_empty_json_feed(empty_json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(empty_json_feed_file_config)

    assert await loader.get_feed_items() == []


@pytest.mark.skipif(system() == 'Windows', reason='Currently not working on Windows!')
async def test_json_feed_reading_error(empty_json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(empty_json_feed_file_config)

    # create write only file
    empty_json_feed_file_config.path.touch(S_IWRITE)

    with pytest.raises(errors.FeedIOError, match=r'Could not read JSON file.*'):
        await loader.get_feed_items()


async def test_invalid_json_feed(empty_json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(empty_json_feed_file_config)

    # write invalid json file
    async with aiofiles.open(empty_json_feed_file_config.path, 'w') as fd:
        await fd.write('Not JS0N!')

    with pytest.raises(errors.FeedIOError, match=r'Could not decode JSON file.*'):
        await loader.get_feed_items()
