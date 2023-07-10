from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import aiofiles
import pydantic

try:
    import tomllib as toml
except ImportError:
    import tomli as toml  # type: ignore

from .errors import ConfigIOError
from .errors import ConfigFormatError
from .models import FeedConfig
from .models import FeedFileWriterConfig
from .models import FeedItemCategory
from .models import FeedMeta
from .models import Game


class FeedConfigLoader:
    """TOML config file loader."""

    def __init__(self, config_path: Optional[Path] = None):
        self._path = config_path or Path("hoyolab-rss-feeds.toml")

    @property
    def path(self) -> Path:
        """TOML config file path."""
        return self._path

    async def _load_from_file(self) -> Dict[str, Any]:
        """Load and parse config from TOML file."""

        try:
            async with aiofiles.open(self._path, "r") as fd:
                conf_str = await fd.read()

            config: Dict[str, Any] = toml.loads(conf_str)
        except IOError as err:
            raise ConfigIOError(
                'Could not open config file at "{}"!'.format(self._path)
            ) from err
        except toml.TOMLDecodeError as err:
            raise ConfigFormatError("Could not parse TOML config file!") from err

        if not any([game.name.lower() in config for game in Game]):
            raise ConfigFormatError("Could not find any game configs!")

        return config

    @staticmethod
    def _create_feed_config(game: Game, config_dict: Dict[str, Any]) -> FeedConfig:
        """Create a feed config from a TOML dict for a specified game."""

        games = {g.name.lower() for g in Game}

        try:
            game_config_dict = config_dict[game.name.lower()]

            # merge root keys into game config dict
            for key, val in config_dict.items():
                if key not in games and key != "feed":
                    # only set key if not already exists
                    game_config_dict.setdefault(key, val)

            feed_config_dict = game_config_dict.pop("feed")

            writer_configs = [
                FeedFileWriterConfig(feed_type=feed_type, **feed_config)
                for feed_type, feed_config in feed_config_dict.items()
            ]

            if "categories" in game_config_dict:
                game_config_dict["categories"] = list(
                    map(
                        lambda cat: FeedItemCategory.from_str(cat),
                        game_config_dict["categories"],
                    )
                )

            feed_meta = FeedMeta(game=game, **game_config_dict)
            feed_config = FeedConfig(feed_meta=feed_meta, writer_configs=writer_configs)
        except KeyError as err:
            raise ConfigFormatError("Could not find required key in config!") from err
        except (pydantic.ValidationError, ValueError) as err:
            raise ConfigFormatError("Invalid config value!") from err

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

    async def create_default_config_file(self) -> None:
        """Create an initial example config file."""

        toml_str = '[genshin]\nfeed.json.path = "genshin.json"'

        try:
            async with aiofiles.open(self._path, "w") as fd:
                await fd.write(toml_str)
        except IOError as err:
            raise ConfigIOError(
                'Could not create default config file at "{}"!'.format(self._path)
            ) from err
