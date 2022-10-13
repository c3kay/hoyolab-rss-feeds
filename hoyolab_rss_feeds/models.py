from enum import IntEnum, unique
from enum import Enum
from pydantic import BaseModel
from pydantic import HttpUrl
from datetime import datetime
from typing import Optional
from typing import List
from pathlib import Path


# --- ENUMS ---

@unique
class PostCategory(IntEnum):
    NOTICES = 1
    EVENTS = 2
    INFO = 3


@unique
class Game(IntEnum):
    # 3 = unused, 5 = hoyolab, 7 = unused
    HONKAI = 1
    GENSHIN = 2
    THEMIS = 4
    STARRAIL = 6
    ZENLESS = 8


class Language(str, Enum):
    CHINESE_CN = "zh-cn"
    CHINESE_TW = "zh-tw"
    GERMAN = "de-de"
    ENGLISH = "en-us"
    SPANISH = "es-es"
    FRENCH = "fr-fr"
    INDONESIAN = "id-id"
    JAPANESE = "ja-jp"
    KOREAN = "ko-kr"
    PORTUGUESE = "pt-pt"
    RUSSIAN = "ru-ru"
    THAI = "th-th"
    VIETNAMESE = "vi-vn"


@unique
class FeedType(str, Enum):
    JSON = 'json'
    ATOM = 'atom'


# --- PYDANTIC MODELS ---

class FeedMeta(BaseModel):
    game: Game
    category_size: int
    language: Language = Language.ENGLISH
    title: Optional[str] = None
    icon: Optional[HttpUrl] = None


class FeedItem(BaseModel):
    id: int
    title: str
    author: str
    content: str
    category: PostCategory
    published: datetime
    updated: Optional[datetime] = None
    image: Optional[HttpUrl] = None


class FeedItemMeta(BaseModel):
    id: int
    last_modified: datetime


class FeedFileConfig(BaseModel):
    feed_type: FeedType
    path: Path


class FeedFileWriterConfig(FeedFileConfig):
    url: Optional[HttpUrl] = None


class FeedConfig(BaseModel):
    feed_meta: FeedMeta
    writer_configs: List[FeedFileWriterConfig]
    loader_config: Optional[FeedFileConfig] = None
