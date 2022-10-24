from os import getenv
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import aiofiles
import tomli
import pydantic

from .errors import ConfigIOError
from .errors import ConfigFormatError
from .models import FeedConfig
from .models import FeedFileWriterConfig
from .models import FeedMeta
from .models import Game


class FeedConfigLoader:
    """TOML file config loader."""

    def __init__(self, config_path: Optional[Path] = None):
        fallback_path = Path('~/.hoyolab-rss-feeds.toml').expanduser()
        self._path = config_path or Path(getenv('HRF_CONFIG_PATH', fallback_path))

    async def _load_from_file(self) -> Dict:
        """Load and parse config from TOML file"""

        try:
            async with aiofiles.open(self._path, 'r') as fd:
                conf_str = await fd.read()

            config = tomli.loads(conf_str)
        except IOError as err:
            raise ConfigIOError('Could not open config file at "{}"!'.format(self._path)) from err
        except tomli.TOMLDecodeError as err:
            raise ConfigFormatError('Could not parse TOML config file!') from err

        if not any([game.name.lower() in config for game in Game]):
            raise ConfigFormatError('Could not find any game configs!')

        return config

    @staticmethod
    def _create_feed_config(game: Game, config_dict: Dict) -> FeedConfig:
        """Create a feed config from a TOML dict for a specified game."""

        games = {g.name.lower() for g in Game}

        try:
            game_config_dict = config_dict[game.name.lower()]

            # merge root keys into game config dict
            for key, val in config_dict.items():
                if key not in games and key != 'file':
                    # only set key if not already exists
                    game_config_dict.setdefault(key, val)

            file_config_dict = game_config_dict.pop('file')

            writer_configs = [
                FeedFileWriterConfig(feed_type=feed_type, **feed_config)
                for feed_type, feed_config in file_config_dict.items()
            ]

            feed_meta = FeedMeta(game=game, **game_config_dict)
            feed_config = FeedConfig(feed_meta=feed_meta, writer_configs=writer_configs)
        except KeyError as err:
            raise ConfigFormatError('Could not find required key in config!') from err
        except pydantic.ValidationError as err:
            raise ConfigFormatError('Invalid config value!') from err

        return feed_config

    async def get_feed_config(self, game: Game) -> FeedConfig:
        """Load and create a feed config for a given game."""

        config = await self._load_from_file()

        return self._create_feed_config(game, config)

    async def get_all_feed_configs(self) -> List[FeedConfig]:
        """Load and create feed configs for all games found in file."""

        config = await self._load_from_file()

        return [
            self._create_feed_config(Game.from_str(key), config)
            for key in config.keys()
            if key in {g.name.lower() for g in Game}
        ]
