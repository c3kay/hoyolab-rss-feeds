import json
from platform import system
from stat import S_IREAD
from typing import List

import aiofiles
import atoma
import pytest

from hoyolabrssfeeds import errors
from hoyolabrssfeeds import models
from hoyolabrssfeeds import writers


# ---- FACTORY TESTS ----


def test_factory_feed_types():
    factory = writers.FeedFileWriterFactory()
    expected = {models.FeedType.JSON, models.FeedType.ATOM}

    assert factory.feed_types == expected


def test_factory_create_writer(
    json_feed_file_writer_config: models.FeedFileWriterConfig,
    atom_feed_file_writer_config: models.FeedFileWriterConfig,
):
    factory = writers.FeedFileWriterFactory()
    json_writer = factory.create_writer(json_feed_file_writer_config)

    assert issubclass(type(json_writer), writers.AbstractFeedFileWriter)
    assert isinstance(json_writer, writers.JSONFeedFileWriter)

    atom_writer = factory.create_writer(atom_feed_file_writer_config)

    assert issubclass(type(atom_writer), writers.AbstractFeedFileWriter)
    assert isinstance(atom_writer, writers.AtomFeedFileWriter)


# ---- JSON WRITER TESTS ----


def test_json_feed_writer_config(
    json_feed_file_writer_config: models.FeedFileWriterConfig,
):
    writer = writers.JSONFeedFileWriter(json_feed_file_writer_config)

    assert writer.config == json_feed_file_writer_config


async def test_json_feed_writer(
    json_feed_file_writer_config: models.FeedFileWriterConfig,
    feed_meta: models.FeedMeta,
    feed_item_list: List[models.FeedItem],
):
    writer = writers.JSONFeedFileWriter(json_feed_file_writer_config)

    await writer.write_feed(feed_meta, feed_item_list)

    assert json_feed_file_writer_config.path.exists()

    async with aiofiles.open(json_feed_file_writer_config.path, "r") as fd:
        feed_str = await fd.read()

    # this should raise an error if feed is invalid -> indirect feed validation
    feed = atoma.parse_json_feed(json.loads(feed_str))

    # just some example asserts
    assert len(feed.items) == len(feed_item_list)
    assert feed.title == feed_meta.title


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_write_json_feed_io_error(
    json_feed_file_writer_config: models.FeedFileWriterConfig,
    feed_meta: models.FeedMeta,
):
    writer = writers.JSONFeedFileWriter(json_feed_file_writer_config)

    # read-only file
    writer.config.path.touch(S_IREAD)

    with pytest.raises(errors.FeedIOError):
        await writer.write_feed(feed_meta, [])


# ---- ATOM WRITER TESTS ----


def test_atom_feed_writer_config(
    atom_feed_file_writer_config: models.FeedFileWriterConfig,
):
    writer = writers.JSONFeedFileWriter(atom_feed_file_writer_config)

    assert writer.config == atom_feed_file_writer_config


async def test_atom_feed_writer(
    atom_feed_file_writer_config: models.FeedFileWriterConfig,
    feed_meta: models.FeedMeta,
    feed_item_list: List[models.FeedItem],
):
    writer = writers.AtomFeedFileWriter(atom_feed_file_writer_config)

    await writer.write_feed(feed_meta, feed_item_list)

    assert atom_feed_file_writer_config.path.exists()

    async with aiofiles.open(atom_feed_file_writer_config.path, "rb") as fd:
        feed_bytes = await fd.read()

    # this should raise an error if feed is invalid -> indirect feed validation
    feed = atoma.parse_atom_bytes(feed_bytes)

    assert len(feed.entries) == len(feed_item_list)
    assert feed.title.value == feed_meta.title


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_write_atom_feed_io_error(
    atom_feed_file_writer_config: models.FeedFileWriterConfig,
    feed_meta: models.FeedMeta,
):
    writer = writers.AtomFeedFileWriter(atom_feed_file_writer_config)

    # read-only file
    writer.config.path.touch(S_IREAD)

    with pytest.raises(errors.FeedIOError):
        await writer.write_feed(feed_meta, [])
