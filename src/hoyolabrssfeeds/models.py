from datetime import datetime
from enum import Enum
from enum import IntEnum, unique
from pathlib import Path
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar

from pydantic import BaseModel
from pydantic import HttpUrl

_IC = TypeVar("_IC", bound="FeedItemCategory")
_G = TypeVar("_G", bound="Game")


# --- ENUMS ---


@unique
class FeedItemCategory(IntEnum):
    NOTICES = 1
    EVENTS = 2
    INFO = 3

    @classmethod
    def from_str(cls: Type[_IC], category_str: str) -> _IC:
        try:
            return cls[category_str.upper()]
        except KeyError as err:
            raise ValueError('Unknown category "{}"!'.format(category_str)) from err


@unique
class Game(IntEnum):
    # 3 = unused, 5 = hoyolab, 7 = unused
    HONKAI = 1
    GENSHIN = 2
    THEMIS = 4
    STARRAIL = 6
    ZENLESS = 8

    @classmethod
    def from_str(cls: Type[_G], game_str: str) -> _G:
        try:
            return cls[game_str.upper()]
        except KeyError as err:
            raise ValueError('Unknown game "{}"!'.format(game_str)) from err


@unique
class FeedType(str, Enum):
    JSON = "json"
    ATOM = "atom"

    def __str__(self) -> str:  # pragma: no cover
        return self.value


@unique
class Language(str, Enum):
    GERMAN = "de-de"
    ENGLISH = "en-us"
    SPANISH = "es-es"
    FRENCH = "fr-fr"
    INDONESIAN = "id-id"
    ITALIAN = "it-it"
    JAPANESE = "ja-jp"
    KOREAN = "ko-kr"
    PORTUGUESE = "pt-pt"
    RUSSIAN = "ru-ru"
    THAI = "th-th"
    TURKISH = "tr-tr"
    VIETNAMESE = "vi-vn"
    CHINESE_CN = "zh-cn"
    CHINESE_TW = "zh-tw"

    def __str__(self) -> str:  # pragma: no cover
        return self.value


# --- PYDANTIC MODELS ---


class MyBaseModel(BaseModel):
    # https://docs.pydantic.dev/usage/model_config/#options
    class Config:
        extra = "forbid"
        anystr_strip_whitespace = True
        min_anystr_length = 1


class FeedMeta(MyBaseModel):
    game: Game
    category_size: int = 5
    categories: List[FeedItemCategory] = [c for c in FeedItemCategory]
    language: Language = Language.ENGLISH
    title: Optional[str] = None
    icon: Optional[HttpUrl] = None


class FeedItem(MyBaseModel):
    id: int
    title: str
    author: str
    content: str
    category: FeedItemCategory
    published: datetime
    updated: Optional[datetime] = None
    image: Optional[HttpUrl] = None


class FeedItemMeta(MyBaseModel):
    id: int
    last_modified: datetime


class FeedFileConfig(MyBaseModel):
    feed_type: FeedType
    path: Path


class FeedFileWriterConfig(FeedFileConfig):
    url: Optional[HttpUrl] = None


class FeedConfig(MyBaseModel):
    feed_meta: FeedMeta
    writer_configs: List[FeedFileWriterConfig]
    loader_config: Optional[FeedFileConfig] = None
