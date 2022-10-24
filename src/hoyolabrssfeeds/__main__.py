import asyncio
from platform import system

from .configs import FeedConfigLoader
from .feeds import GameFeedCollection


async def create_feeds():
    config_loader = FeedConfigLoader()
    feed_configs = await config_loader.get_all_feed_configs()
    game_feed = GameFeedCollection.from_configs(feed_configs)
    await game_feed.create_feeds()


def main():
    if system() == "Windows":
        # default policy not working on windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(create_feeds())


if __name__ == "__main__":
    main()
