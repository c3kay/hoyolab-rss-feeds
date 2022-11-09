import json
from platform import system
from stat import S_IWRITE
from typing import Dict
from typing import List
from xml.etree import ElementTree

import aiofiles
import pytest
import pytest_mock

from hoyolabrssfeeds import errors
from hoyolabrssfeeds import loaders
from hoyolabrssfeeds import models
from hoyolabrssfeeds import writers


# ---- FACTORY TESTS ----


def test_factory_feed_types():
    factory = loaders.FeedFileLoaderFactory()
    expected = {models.FeedType.ATOM, models.FeedType.JSON}

    assert factory.feed_types == expected


def test_factory_create_loader(
    json_feed_file_config: models.FeedFileConfig,
    atom_feed_file_config: models.FeedFileConfig,
):
    factory = loaders.FeedFileLoaderFactory()
    json_loader = factory.create_loader(json_feed_file_config)

    assert issubclass(type(json_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(json_loader, loaders.JSONFeedFileLoader)

    atom_loader = factory.create_loader(atom_feed_file_config)

    assert issubclass(type(atom_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(atom_loader, loaders.AtomFeedFileLoader)


def test_factory_create_any_loader(
    atom_feed_file_config: models.FeedFileConfig,
    json_feed_file_config: models.FeedFileConfig,
):
    json_writer = writers.JSONFeedFileWriter(json_feed_file_config)
    atom_writer = writers.AtomFeedFileWriter(atom_feed_file_config)

    factory = loaders.FeedFileLoaderFactory()
    json_loader = factory.create_any_loader([atom_writer, json_writer])

    assert issubclass(type(json_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(json_loader, loaders.JSONFeedFileLoader)

    atom_loader = factory.create_any_loader([atom_writer])

    assert issubclass(type(atom_loader), loaders.AbstractFeedFileLoader)
    assert isinstance(atom_loader, loaders.AtomFeedFileLoader)


def test_factory_create_invalid_any_loader():
    factory = loaders.FeedFileLoaderFactory()

    with pytest.raises(ValueError, match="Could not create"):
        factory.create_any_loader([])


# ---- JSON LOADER TESTS ----


def test_json_feed_loader_config(json_feed_file_config: models.FeedFileConfig):
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    assert loader.config == json_feed_file_config


async def test_json_feed_loader(
    mocker: pytest_mock.MockFixture,
    json_feed_items: Dict,
    feed_item_list: List[models.FeedItem],
    json_feed_file_config: models.FeedFileConfig,
):
    mocked_load = mocker.patch(
        "hoyolabrssfeeds.loaders.JSONFeedFileLoader._load_from_file",
        spec=True,
        return_value=json_feed_items,
    )

    # needed for get_feed_items() to work for this test
    json_feed_file_config.path.touch()

    loader = loaders.JSONFeedFileLoader(json_feed_file_config)
    loaded_items = await loader.get_feed_items()

    mocked_load.assert_awaited()
    mocked_load.assert_called()

    assert loaded_items == feed_item_list


async def test_invalid_json_feed_values(
    mocker: pytest_mock.MockFixture,
    json_feed_items: Dict,
    json_feed_file_config: models.FeedFileConfig,
):
    # set invalid value
    json_feed_items["items"][0]["tags"] = ["invalid"]

    mocker.patch(
        "hoyolabrssfeeds.loaders.JSONFeedFileLoader._load_from_file",
        spec=True,
        return_value=json_feed_items,
    )

    json_feed_file_config.path.touch()
    loader = loaders.JSONFeedFileLoader(json_feed_file_config)

    with pytest.raises(errors.FeedFormatError, match="Could not load"):
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


# ---- ATOM LOADER TESTS ----


def test_atom_feed_loader_config(atom_feed_file_config: models.FeedFileConfig):
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    assert loader.config == atom_feed_file_config


async def test_atom_feed_loader(
    mocker: pytest_mock.MockFixture,
    feed_item_list: List[models.FeedItem],
    atom_feed_entries: ElementTree.Element,
    atom_feed_file_config: models.FeedFileConfig,
):
    mocked_load = mocker.patch(
        "hoyolabrssfeeds.loaders.AtomFeedFileLoader._load_from_file",
        spec=True,
        return_value=atom_feed_entries,
    )

    # images cannot be stored in atom feeds
    for feed_item in feed_item_list:
        feed_item.image = None

    # needed for get_feed_items() to work for this test
    atom_feed_file_config.path.touch()
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    loaded_items = await loader.get_feed_items()

    mocked_load.assert_awaited()
    mocked_load.assert_called()

    assert loaded_items == feed_item_list


async def test_invalid_atom_feed_values(
    mocker: pytest_mock.MockFixture,
    atom_feed_entries: ElementTree.Element,
    atom_feed_file_config: models.FeedFileConfig,
):
    # set invalid value in first entry
    atom_feed_entries.find("entry/category").set("term", "invalid")

    mocker.patch(
        "hoyolabrssfeeds.loaders.AtomFeedFileLoader._load_from_file",
        spec=True,
        return_value=atom_feed_entries,
    )

    atom_feed_file_config.path.touch()
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    with pytest.raises(errors.FeedFormatError, match="Could not load"):
        await loader.get_feed_items()


async def test_invalid_atom_feed(
    mocker: pytest_mock.MockFixture, atom_feed_file_config: models.FeedFileConfig
):
    invalid_feed = ElementTree.Element("feed")
    ElementTree.SubElement(invalid_feed, "entry")

    mocker.patch(
        "hoyolabrssfeeds.loaders.AtomFeedFileLoader._load_from_file",
        spec=True,
        return_value=invalid_feed,
    )

    atom_feed_file_config.path.touch()
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    with pytest.raises(errors.FeedFormatError, match="Could not load"):
        await loader.get_feed_items()


async def test_no_atom_file(atom_feed_file_config):
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    assert await loader.get_feed_items() == []


async def test_load_atom_file(atom_feed_file_config):
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    # faking namespace declaration because it is supposed to be removed in fn
    root = ElementTree.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})

    title_text = "Test Atom Feed"
    ElementTree.SubElement(root, "title").text = title_text

    xml_bytes = ElementTree.tostring(root, encoding="utf-8")

    async with aiofiles.open(atom_feed_file_config.path, "wb") as fd:
        await fd.write(xml_bytes)

    loaded_feed = await loader._load_from_file()

    assert loaded_feed.findtext("title") == title_text


async def test_load_invalid_atom_file(atom_feed_file_config):
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    async with aiofiles.open(atom_feed_file_config.path, "w") as fd:
        await fd.write("Not At0m!")

    with pytest.raises(errors.FeedFormatError, match="Could not parse"):
        await loader._load_from_file()


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_load_atom_file_io_error(atom_feed_file_config):
    loader = loaders.AtomFeedFileLoader(atom_feed_file_config)

    # create write only file
    atom_feed_file_config.path.touch(S_IWRITE)

    with pytest.raises(errors.FeedIOError, match="Could not read"):
        await loader._load_from_file()
