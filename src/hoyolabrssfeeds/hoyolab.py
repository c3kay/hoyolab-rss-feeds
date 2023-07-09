from typing import Any
from typing import Dict
from typing import List

import aiohttp
import pydantic

from .errors import HoyolabApiError
from .models import FeedItem
from .models import FeedItemCategory
from .models import FeedItemMeta
from .models import Game
from .models import Language

HOYOLAB_API_BASE_URL = "https://bbs-api-os.hoyolab.com/community/post/wapi/"
DEFAULT_CATEGORY_SIZE = 5


class HoyolabNews:
    """Wrapper for Hoyolab REST API endpoints."""

    def __init__(self, game: Game, language: Language = Language.ENGLISH) -> None:
        self._game = game
        self._lang = language.lower()

    async def _request(
        self,
        session: aiohttp.ClientSession,
        params: Dict[str, Any],
        url: pydantic.HttpUrl,
    ) -> Dict[str, Any]:
        """Send a GET request to the Hoyolab API endpoint."""

        headers = {"Origin": "https://www.hoyolab.com", "X-Rpc-Language": self._lang}

        try:
            async with session.get(
                str(url), headers=headers, params=params
            ) as response:
                response.raise_for_status()
                response_json: Dict[str, Any] = await response.json()

            if response_json["retcode"] != 0:
                # the message might be in chinese
                raise HoyolabApiError(response_json["message"])
        except aiohttp.ContentTypeError as err:
            raise HoyolabApiError("Could not decode response to JSON!") from err
        except aiohttp.ClientResponseError as err:
            raise HoyolabApiError("Could not request Hoyolab endpoint!") from err
        except KeyError as err:
            raise HoyolabApiError("Unexpected response!") from err

        return response_json

    async def get_news_list(
        self,
        session: aiohttp.ClientSession,
        category: FeedItemCategory,
        category_size: int = DEFAULT_CATEGORY_SIZE,
    ) -> List[Dict[str, Any]]:
        """Request an overview of the latest posts."""

        params = {"gids": self._game, "page_size": category_size, "type": category}

        url = pydantic.parse_obj_as(
            pydantic.HttpUrl, HOYOLAB_API_BASE_URL + "getNewsList"
        )

        response = await self._request(session, params, url)
        news_list: List[Dict[str, Any]] = response["data"]["list"]

        return news_list

    async def get_post(
        self, session: aiohttp.ClientSession, post_id: int
    ) -> Dict[str, Any]:
        """Request single post with fulltext."""

        params = {"gids": self._game, "post_id": post_id}

        url = pydantic.parse_obj_as(
            pydantic.HttpUrl, HOYOLAB_API_BASE_URL + "getPostFull"
        )

        response = await self._request(session, params, url)
        post: Dict[str, Any] = response["data"]["post"]

        return post

    async def get_latest_item_metas(
        self,
        session: aiohttp.ClientSession,
        category: FeedItemCategory,
        category_size: int = DEFAULT_CATEGORY_SIZE,
    ) -> List[FeedItemMeta]:
        """Get the meta info of the latest posts in a specified category."""

        latest_posts = []

        category_posts = await self.get_news_list(session, category, category_size)

        for post in category_posts:
            published_ts = int(post["post"]["created_at"])
            modified_ts = int(post["last_modify_time"])

            item_meta = {
                "id": post["post"]["post_id"],
                "last_modified": max(published_ts, modified_ts),
            }

            # parsing for type conversions
            latest_posts.append(pydantic.parse_obj_as(FeedItemMeta, item_meta))

        return latest_posts

    async def get_feed_item(
        self, session: aiohttp.ClientSession, post_id: int
    ) -> FeedItem:
        """Get a single post as feed item."""

        post = await self.get_post(session, post_id)

        content = post["post"]["content"]

        # remove empty leading paragraphs
        if content.startswith(("<p></p>", "<p>&nbsp;</p>", "<p><br></p>")):
            content = content.partition("</p>")[2]

        item = {
            "id": post["post"]["post_id"],
            "title": post["post"]["subject"],
            "author": post["user"]["nickname"],
            "content": content,
            "category": post["post"]["official_type"],
            "published": post["post"]["created_at"],
        }

        if post["last_modify_time"] > 0:
            item["updated"] = post["last_modify_time"]

        if len(post["image_list"]) > 0:
            item["image"] = post["image_list"][0]["url"]

        return pydantic.parse_obj_as(FeedItem, item)
