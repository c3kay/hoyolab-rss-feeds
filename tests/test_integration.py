import hoyolabrssfeeds as hrf
from aiohttp import ClientSession
from pathlib import Path


async def test_single_feed(
        client_session: ClientSession,
        shared_datadir: Path,
        tmp_path: Path
):
    config_path = shared_datadir / 'feed_config.toml'
    config_loader = hrf.configs.FeedConfigLoader(config_path)
    game_config = await config_loader.get_feed_config(hrf.models.Game.GENSHIN)

    # the following is a workaround to write the feeds in a tmpdir without modifying the config.
    # it is possible to modify the toml config, but it would require another third-party lib...
    # => prefixing the configured paths/files with a tmp path

    if game_config.loader_config is not None:
        game_config.loader_config.path = tmp_path / game_config.loader_config.path.name

    known_paths = []
    for w in game_config.writer_configs:
        w.path = tmp_path / w.path.name
        known_paths.append(w.path)

    game_feed = hrf.feeds.GameFeed.from_config(game_config)
    await game_feed.create_feed(client_session)

    for path in known_paths:
        assert path.exists()


async def test_feed_collection(
        client_session: ClientSession,
        shared_datadir: Path,
        tmp_path: Path
):
    config_path = shared_datadir / 'feed_config.toml'
    config_loader = hrf.configs.FeedConfigLoader(config_path)
    game_configs = await config_loader.get_all_feed_configs()

    known_paths = []
    for conf in game_configs:
        if conf.loader_config is not None:
            conf.loader_config.path = tmp_path / conf.loader_config.path.name

        for w in conf.writer_configs:
            w.path = tmp_path / w.path.name
            known_paths.append(w.path)

    feed_collection = hrf.feeds.GameFeedCollection.from_configs(game_configs)
    await feed_collection.create_feeds(client_session)

    for path in known_paths:
        assert path.exists()
