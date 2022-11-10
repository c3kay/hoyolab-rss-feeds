import asyncio
from pathlib import Path

import aiofiles
from aiohttp import ClientSession

import hoyolabrssfeeds as hrf


async def test_single_feed(client_session: ClientSession, tmp_path: Path):
    config_path = await _write_config(tmp_path)
    config_loader = hrf.configs.FeedConfigLoader(config_path)
    game_config = await config_loader.get_feed_config(hrf.models.Game.GENSHIN)
    known_paths = [w.path for w in game_config.writer_configs]

    game_feed = hrf.feeds.GameFeed.from_config(game_config)

    # initial creation
    await game_feed.create_feed(client_session)

    for path in known_paths:
        assert path.exists()

    # save modification timestamps
    m_times = [p.stat().st_mtime for p in known_paths]

    await asyncio.sleep(1)

    # feed update
    await game_feed.create_feed(client_session)

    # feeds should not have changed after update
    assert m_times == [p.stat().st_mtime for p in known_paths]


async def test_feed_collection(client_session: ClientSession, tmp_path: Path):
    config_path = await _write_config(tmp_path)
    config_loader = hrf.configs.FeedConfigLoader(config_path)
    game_configs = await config_loader.get_all_feed_configs()

    feed_collection = hrf.feeds.GameFeedCollection.from_configs(game_configs)
    await feed_collection.create_feeds(client_session)

    for conf in game_configs:
        for w in conf.writer_configs:
            assert w.path.exists()


# ---- HELPER FUNCTIONS ----


async def _write_config(base_tmp_path: Path):
    # NOTE: paths are single quoted to get literal paths
    # this should avoid wrongfully escaping of windows paths
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
