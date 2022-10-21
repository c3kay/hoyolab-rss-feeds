import json
from os.path import exists
from pathlib import Path
from typing import List

import aiofiles
import atoma
import pytest

from hoyolabrssfeeds import models
from hoyolabrssfeeds import writers


def test_factory_feed_types():
    factory = writers.FeedFileWriterFactory()
    expected = {str(models.FeedType.JSON), str(models.FeedType.ATOM)}

    assert factory.feed_types == expected


def test_factory_create_writer(
        json_feed_file_writer_config: models.FeedFileWriterConfig,
        atom_feed_file_writer_config: models.FeedFileWriterConfig
):
    factory = writers.FeedFileWriterFactory()
    json_writer = factory.create_writer(json_feed_file_writer_config)
    atom_writer = factory.create_writer(atom_feed_file_writer_config)

    assert issubclass(type(json_writer), writers.AbstractFeedFileWriter)
    assert issubclass(type(atom_writer), writers.AbstractFeedFileWriter)

    assert isinstance(json_writer, writers.JSONFeedFileWriter)
    assert isinstance(atom_writer, writers.AtomFeedFileWriter)


def test_factory_register_writer(json_path: Path):
    factory = writers.FeedFileWriterFactory()
    factory.register_writer('custom', writers.JSONFeedFileWriter)

    assert 'custom' in factory.feed_types

    custom_config = models.FeedFileWriterConfig(feed_type='custom', path=json_path)
    writer = factory.create_writer(custom_config)

    assert isinstance(writer, writers.JSONFeedFileWriter)


def test_factory_register_duplicate_writer():
    factory = writers.FeedFileWriterFactory()

    with pytest.raises(ValueError):
        factory.register_writer(models.FeedType.JSON, writers.JSONFeedFileWriter)


def test_json_feed_writer_config(json_feed_file_writer_config: models.FeedFileWriterConfig):
    writer = writers.JSONFeedFileWriter(json_feed_file_writer_config)

    assert writer.config == json_feed_file_writer_config


async def test_json_feed_writer(
        json_feed_file_writer_config: models.FeedFileWriterConfig,
        feed_meta: models.FeedMeta,
        feed_item_list: List[models.FeedItem]
):
    writer = writers.JSONFeedFileWriter(json_feed_file_writer_config)

    await writer.write_feed(feed_meta, feed_item_list)

    assert exists(json_feed_file_writer_config.path)

    async with aiofiles.open(json_feed_file_writer_config.path, 'r') as fd:
        feed_str = await fd.read()

    # this should raise an error if feed is invalid -> indirect feed validation
    feed = atoma.parse_json_feed(json.loads(feed_str))

    # just some example asserts
    assert len(feed.items) == len(feed_item_list)
    assert feed.title == feed_meta.title


def test_atom_feed_writer_config(atom_feed_file_writer_config: models.FeedFileWriterConfig):
    writer = writers.JSONFeedFileWriter(atom_feed_file_writer_config)

    assert writer.config == atom_feed_file_writer_config


async def test_atom_feed_writer(
        atom_feed_file_writer_config: models.FeedFileWriterConfig,
        feed_meta: models.FeedMeta,
        feed_item_list: List[models.FeedItem]
):
    writer = writers.AtomFeedFileWriter(atom_feed_file_writer_config)

    await writer.write_feed(feed_meta, feed_item_list)

    assert exists(atom_feed_file_writer_config.path)

    async with aiofiles.open(atom_feed_file_writer_config.path, 'rb') as fd:
        feed_bytes = await fd.read()

    feed = atoma.parse_atom_bytes(feed_bytes)

    assert len(feed.entries) == len(feed_item_list)
    assert feed.title.value == feed_meta.title
