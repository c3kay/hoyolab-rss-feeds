import argparse
import asyncio
import logging
from pathlib import Path
from platform import system
from typing import Optional

from .configs import FeedConfigLoader
from .feeds import GameFeedCollection

logger = logging.getLogger(__package__)


async def create_feeds(config_path: Optional[Path] = None) -> None:
    # fallback path defined in config loader if no path given
    config_loader = FeedConfigLoader(config_path)

    if not config_loader.path.exists():
        await config_loader.create_default_config_file()
        logger.info("Default config file created at %s.", config_loader.path.resolve())
        return

    feed_configs = await config_loader.get_all_feed_configs()
    game_feed = GameFeedCollection.from_configs(feed_configs)
    await game_feed.create_feeds()


def cli() -> None:
    if system() == "Windows":
        # default policy not working on windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore

    arg_parser = argparse.ArgumentParser(
        prog="hoyolab-rss-feeds", description="Generate Hoyolab RSS feeds."
    )

    arg_parser.add_argument(
        "-c", "--config-path", help="Path to the TOML config file", type=Path
    )

    arg_parser.add_argument(
        "-l",
        "--log-path",
        required=False,
        default=None,
        help="Path to the written log file",
        type=Path,
    )

    args = arg_parser.parse_args()

    logging.basicConfig(
        filename=args.log_path,
        filemode="a",
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        level=logging.INFO,
    )

    asyncio.run(create_feeds(args.config_path))


if __name__ == "__main__":
    cli()
