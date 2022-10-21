from os import getenv
from os.path import expanduser
from os.path import join
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import aiofiles
import tomli
from pydantic import ValidationError

from .errors import ConfigError
from .models import FeedConfig
from .models import FeedFileWriterConfig
from .models import FeedMeta
from .models import Game


class FeedConfigLoader:
    """TOML file config loader."""

    def __init__(self, config_path: Optional[Path] = None):
        fallback_path = join(expanduser('~'), '.hoyolab_feeds.toml')
        self._path = config_path or getenv('HRF_CONFIG_PATH', fallback_path)

    async def _load_from_file(self) -> Dict:
        """Load and parse config from TOML file"""

        try:
            async with aiofiles.open(self._path, 'r') as fd:
                conf_str = await fd.read()

            config = tomli.loads(conf_str)
        except IOError as err:
            raise ConfigError('Could not open config file at "{}"'.format(self._path)) from err
        except tomli.TOMLDecodeError as err:
            raise ConfigError('Could not parse config file!') from err

        if not any([game.name.lower() in config for game in Game]):
            raise ConfigError('Could not find any game configs!')

        return config

    @staticmethod
    def _create_feed_config(game: Game, game_config_dict: Dict) -> FeedConfig:
        """Create a FeedConfig from a game config section."""

        try:
            file_config_dict = game_config_dict.pop('file')

            writer_configs = [
                FeedFileWriterConfig(feed_type=feed_type, **feed_config)
                for feed_type, feed_config in file_config_dict.items()
            ]

            feed_meta = FeedMeta(game=game, **game_config_dict)
            feed_config = FeedConfig(feed_meta=feed_meta, writer_configs=writer_configs)
        except KeyError as err:
            raise ConfigError('Could not find required key in config!') from err
        except ValidationError as err:
            raise ConfigError('Invalid config file!') from err

        return feed_config

    @staticmethod
    def _merge_root(config: Dict, game_config_dict: Dict) -> Dict:
        """Put root entries (defaults) to specific section."""

        games = {g.name.lower() for g in Game}

        for key, val in config.items():
            if key not in games and key != 'file':
                # only set key if not already exists
                game_config_dict.setdefault(key, val)

        return game_config_dict

    async def get_feed_config(self, game: Game) -> FeedConfig:
        """Create a FeedConfig from config file for a given game."""

        config = await self._load_from_file()
        game_str = game.name.lower()

        try:
            game_config_dict = config[game_str]
        except KeyError as err:
            raise ConfigError('Could not find "{}" game section!'.format(game_str)) from err

        game_config_dict = self._merge_root(config, game_config_dict)

        return self._create_feed_config(game, game_config_dict)

    async def get_all_feed_configs(self) -> List[FeedConfig]:
        """Create FeedConfigs for all games in a config file."""

        config = await self._load_from_file()
        games = {g.name.lower() for g in Game}
        feed_configs = []

        for key, config_dict in config.items():
            if key in games:
                config_dict = self._merge_root(config, config_dict)
                feed_config = self._create_feed_config(Game.from_str(key), config_dict)
                feed_configs.append(feed_config)

        return feed_configs
