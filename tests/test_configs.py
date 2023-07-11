from pathlib import Path
from platform import system
from stat import S_IWRITE
from stat import S_IREAD
from typing import Dict

import aiofiles
import pytest
import pytest_mock

try:
    import tomllib as toml
except ImportError:
    import tomli as toml  # type: ignore

from hoyolabrssfeeds import configs
from hoyolabrssfeeds import errors
from hoyolabrssfeeds import models


def test_config_paths(config_path: Path):
    param_config = configs.FeedConfigLoader(config_path)
    assert param_config.path == config_path

    fallback_config = configs.FeedConfigLoader()
    assert fallback_config.path == Path("hoyolab-rss-feeds.toml")


async def test_load_toml_file(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    toml_str = """
    [genshin]
    key = 'value'
    """

    async with aiofiles.open(config_path, "w") as fd:
        await fd.write(toml_str)

    config_dict = await loader._load_from_file()
    expected = {"genshin": {"key": "value"}}

    assert config_dict == expected


async def test_invalid_toml_file(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    async with aiofiles.open(config_path, "w") as fd:
        await fd.write("{Invalid}")

    with pytest.raises(errors.ConfigFormatError, match="Could not parse"):
        await loader._load_from_file()


async def test_empty_toml_file(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    config_path.touch()

    with pytest.raises(errors.ConfigFormatError, match="Could not find"):
        await loader._load_from_file()


async def test_default_toml_file(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    await loader.create_default_config_file()

    assert config_path.exists()

    async with aiofiles.open(config_path, "r") as fd:
        toml_str = await fd.read()

    default_config = toml.loads(toml_str)

    expected = {
        "genshin": {"feed": {"json": {"path": "genshin.json"}}},
    }

    assert default_config == expected


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_default_toml_file_io_error(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    # create read-only file
    config_path.touch(S_IREAD)

    with pytest.raises(errors.ConfigIOError, match="Could not create"):
        await loader.create_default_config_file()


@pytest.mark.skipif(system() == "Windows", reason="Currently not working on Windows")
async def test_load_toml_file_io_error(config_path: Path):
    loader = configs.FeedConfigLoader(config_path)

    # create write-only file
    config_path.touch(S_IWRITE)

    with pytest.raises(errors.ConfigIOError, match="Could not open"):
        await loader._load_from_file()


async def test_create_feed_config(
    mocker: pytest_mock.MockFixture,
    feed_config_no_loader: models.FeedConfig,
    toml_config_dict: Dict,
):
    loader = configs.FeedConfigLoader()

    mocked_load = mocker.patch(
        "hoyolabrssfeeds.configs.FeedConfigLoader._load_from_file",
        spec=True,
        return_value=toml_config_dict,
    )

    loaded_config = await loader.get_feed_config(feed_config_no_loader.feed_meta.game)

    mocked_load.assert_awaited()
    mocked_load.assert_called_once()

    assert loaded_config == feed_config_no_loader


async def test_create_all_feed_configs(
    mocker: pytest_mock.MockFixture, toml_config_dict: Dict
):
    loader = configs.FeedConfigLoader()

    mocked_load = mocker.patch(
        "hoyolabrssfeeds.configs.FeedConfigLoader._load_from_file",
        spec=True,
        return_value=toml_config_dict,
    )

    loaded_configs = await loader.get_all_feed_configs()

    mocked_load.assert_awaited()
    mocked_load.assert_called_once()

    for conf in loaded_configs:
        # only testing if a feed config exists for all specified games
        assert conf.feed_meta.game.name.lower() in toml_config_dict


def test_create_invalid_feed_config():
    loader = configs.FeedConfigLoader()

    with pytest.raises(errors.ConfigFormatError, match="Could not find"):
        loader._create_feed_config(models.Game.GENSHIN, {"honkai": {}})

    with pytest.raises(errors.ConfigFormatError, match="Invalid config"):
        loader._create_feed_config(
            models.Game.GENSHIN, {"genshin": {"feed": {"Invalid": {}}}}
        )
