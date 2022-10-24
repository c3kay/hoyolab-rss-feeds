import json
from pathlib import Path
from platform import system
from stat import S_IWRITE

import aiofiles
import pytest
import pytest_mock

from hoyolabrssfeeds import errors
from hoyolabrssfeeds import loaders
from hoyolabrssfeeds import models
from hoyolabrssfeeds import writers


def test_factory_feed_types():
    factory = loaders.FeedFileLoaderFactory()
    expected = {str(models.FeedType.JSON)}

    assert factory.feed_types == expected


def test_factory_create_loader(json_feed_file_config: models.FeedFileConfig):
    factory = loaders.FeedFileLoaderFactory()
    json_loader = factory.create_loader(json_feed_file_config)

    assert issubclass(type(json_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(json_loader, loaders.JSONFeedFileLoader)


def test_factory_create_invalid_loader(json_path: Path):
    factory = loaders.FeedFileLoaderFactory()
    invalid_config = models.FeedFileConfig(feed_type="invalid", path=json_path)

    with pytest.raises(ValueError):
        factory.create_loader(invalid_config)


def test_factory_create_any_loader(json_feed_file_config: models.FeedFileConfig):
    json_writer = writers.JSONFeedFileWriter(json_feed_file_config)
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
    factory.register_loader("custom", loaders.JSONFeedFileLoader)

    assert "custom" in factory.feed_types

    custom_config = models.FeedFileConfig(feed_type="custom", path=json_path)
    loader = factory.create_loader(custom_config)

    assert isinstance(loader, loaders.JSONFeedFileLoader)


def test_factory_register_duplicate_loader():
    factory = loaders.FeedFileLoaderFactory()

    with pytest.raises(ValueError):
        factory.register_loader(str(models.FeedType.JSON), loaders.JSONFeedFileLoader)


def test_json_feed_loader_config(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    assert loader.config == json_feed_file_config


async def test_json_feed_loader(
    mocker: pytest_mock.MockFixture,
    feed_item: models.FeedItem,
    json_feed_file_config: models.FeedFileConfig,
):
    json_items = {
        "items": [
            {
                "id": feed_item.id,
                "url": "https://example.org",
                "title": feed_item.title,
                "authors": [{"name": feed_item.author}],
                "tags": [feed_item.category.name.title()],
                "content_html": feed_item.content,
                "date_published": feed_item.published.astimezone().isoformat(),
                "date_modified": feed_item.updated.astimezone().isoformat(),
                "image": feed_item.image,
            }
        ]
    }

    mocked_load = mocker.patch(
        "hoyolabrssfeeds.loaders.JSONFeedFileLoader._load_from_file",
        spec=True,
        return_value=json_items,
    )

    # needed for get_feed_items() to work
    json_feed_file_config.path.touch()

    loader = loaders.JSONFeedFileLoader(json_feed_file_config)
    loaded_items = await loader.get_feed_items()

    mocked_load.assert_awaited()
    mocked_load.assert_called()

    assert loaded_items == [feed_item]


async def test_invalid_json_feed_values(
    mocker: pytest_mock.MockFixture, json_feed_file_config: models.FeedFileConfig
):
    invalid_json_items = {
        "items": [
            {
                "id": 1,
                "url": "https://example.org",
                "title": "Invalid",
                "authors": [{"name": "Invalid"}],
                "tags": ["Invalid"],  # this should raise
                "content": "Invalid",
                "date_published": "1970-01-01",
            }
        ]
    }

    mocker.patch(
        "hoyolabrssfeeds.loaders.JSONFeedFileLoader._load_from_file",
        spec=True,
        return_value=invalid_json_items,
    )

    json_feed_file_config.path.touch()
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    with pytest.raises(errors.FeedFormatError, match="Found unexpected value"):
        await loader.get_feed_items()


async def test_invalid_json_feed(
    mocker: pytest_mock.MockFixture, json_feed_file_config: models.FeedFileConfig
):
    mocker.patch(
        "hoyolabrssfeeds.loaders.JSONFeedFileLoader._load_from_file",
        spec=True,
        return_value={},
    )

    json_feed_file_config.path.touch()
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    with pytest.raises(errors.FeedFormatError, match="Could not find"):
        await loader.get_feed_items()


async def test_no_json_file(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    assert await loader.get_feed_items() == []


async def test_load_json_file(json_feed_file_config):
    data = {"version": "https://jsonfeed.org/version/1.1"}

    async with aiofiles.open(json_feed_file_config.path, "w") as fd:
        await fd.write(json.dumps(data))

    loader = loaders.JSONFeedFileLoader(json_feed_file_config)
    loaded_data = await loader._load_from_file()

    assert loaded_data == data


async def test_load_invalid_json_file(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    # write invalid json file
    async with aiofiles.open(json_feed_file_config.path, "w") as fd:
        await fd.write("Not JS0N!")

    with pytest.raises(errors.FeedFormatError, match="Could not decode"):
        await loader._load_from_file()


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_load_json_file_io_error(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    # create write only file
    json_feed_file_config.path.touch(S_IWRITE)

    with pytest.raises(errors.FeedIOError, match="Could not read"):
        await loader._load_from_file()
