import asyncio
from pathlib import Path

import aiofiles
import aiohttp

from hoyolabrssfeeds import FeedConfigLoader
from hoyolabrssfeeds import Game
from hoyolabrssfeeds import GameFeed
from hoyolabrssfeeds import GameFeedCollection


async def test_single_feed(client_session: aiohttp.ClientSession, tmp_path: Path):
    config_path = await _write_config(tmp_path)
    config_loader = FeedConfigLoader(config_path)
    game_config = await config_loader.get_feed_config(Game.GENSHIN)
    game_feed = GameFeed.from_config(game_config)

    # initial creation
    await game_feed.create_feed(client_session)

    for feed_path in [w.path for w in game_config.writer_configs]:
        assert feed_path.exists()

    await asyncio.sleep(2)

    # feed update
    await game_feed.create_feed(client_session)

    assert not game_feed.was_updated


async def test_feed_collection(client_session: aiohttp.ClientSession, tmp_path: Path):
    config_path = await _write_config(tmp_path)
    config_loader = FeedConfigLoader(config_path)
    game_configs = await config_loader.get_all_feed_configs()

    feed_collection = GameFeedCollection.from_configs(game_configs)
    await feed_collection.create_feeds(client_session)

    for conf in game_configs:
        for w in conf.writer_configs:
            assert w.path.exists()


# ---- HELPER FUNCTIONS ----


async def _write_config(base_tmp_path: Path):
    # NOTE: paths are single quoted to get literal strings
    # this should avoid wrongfully escaping of windows paths by tomli
    toml_templ = """
        icon = "https://example.org"

        [genshin]
        feed.json.path = '{}'
        feed.json.url = "https://example.org"
        feed.atom.path = '{}'
        title = "Genshin"

        [honkai]
        feed.atom.path = '{}'
        category_size = 3
    """

    toml_config = toml_templ.format(
        base_tmp_path / Path("genshin.json"),
        base_tmp_path / Path("genshin.xml"),
        base_tmp_path / Path("honkai.xml"),
    )

    config_path = base_tmp_path / Path("feeds.toml")
    async with aiofiles.open(config_path, "w") as fd:
        await fd.write(toml_config)

    return config_path
