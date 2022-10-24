import aiofiles

import hoyolabrssfeeds as hrf
from aiohttp import ClientSession
from pathlib import Path


async def test_single_feed(client_session: ClientSession, tmp_path: Path):
    config_path = await _write_config(tmp_path)
    config_loader = hrf.configs.FeedConfigLoader(config_path)
    game_config = await config_loader.get_feed_config(hrf.models.Game.GENSHIN)

    known_paths = []
    for w in game_config.writer_configs:
        w.path = tmp_path / w.path.name
        known_paths.append(w.path)

    game_feed = hrf.feeds.GameFeed.from_config(game_config)
    await game_feed.create_feed(client_session)

    for path in known_paths:
        assert path.exists()


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
    toml_templ = """
        category_size = 3

        [genshin]
        file.json.path = "{base}/genshin.json"
        file.json.url = "https://example.org"
        file.atom.path = "{base}/genshin.xml"
        title = "Genshin"

        [honkai]
        file.json.path = "{base}/honkai.json"
    """

    toml_config = toml_templ.format(base=base_tmp_path)

    config_path = base_tmp_path / Path('feeds.toml')
    async with aiofiles.open(config_path, 'w') as fd:
        await fd.write(toml_config)

    return config_path
