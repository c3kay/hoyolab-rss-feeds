import json
import re
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

    def _transform_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Transform (i.e. apply fixes) post of Hoyolab API response."""

        # weird hoyolab bug/feature, where the content html is just a language code.
        # this needs to be first to also apply the other fixes.
        if re.fullmatch(r"^[a-z]{2}-[a-z]{2}$", post["post"]["content"]):
            post["post"]["content"] = self._parse_structured_content(
                post["post"]["structured_content"]
            )

        # native/local video post
        if (
            "view_type" in post["post"]
            and post["post"]["view_type"] == 5
            and post["video"] is not None
        ):
            post["post"]["content"] = (
                '<video src="{src}" poster="{poster}" controls playsinline>Watch the video here: {src}</video><p>'
                "{desc}</p>".format(
                    src=post["video"]["url"],
                    poster=post["video"]["cover"],
                    desc=post["post"]["desc"],
                )
            )

        # image gallery
        if "view_type" in post["post"] and post["post"]["view_type"] == 2:
            post["post"]["content"] = self._parse_gallery_post(post["post"]["content"])

        # remove empty leading paragraphs
        if post["post"]["content"].startswith(
            ("<p></p>", "<p>&nbsp;</p>", "<p><br></p>")
        ):
            post["post"]["content"] = post["post"]["content"].partition("</p>")[2]

        # fix private links
        post["post"]["content"] = post["post"]["content"].replace(
            "hoyolab-upload-private", "upload-os-bbs"
        )

        # youtube error 153
        if "<iframe" in post["post"]["content"]:
            post["post"]["content"] = re.sub(
                r'<iframe.+?src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9-_]+)\?.+?".*?><\/iframe>',
                r'<p><strong>YouTube: <a href="https://youtu.be/\1">https://youtu.be/\1</a></strong></p>',
                post["post"]["content"],
            )

        return post

    @staticmethod
    def _parse_structured_content(structured_content: str) -> str:
        """Parse the Hoyolab structured content and return the constructed HTML."""

        structured_content = re.sub(r"(\\)?\\n", "<br>", structured_content)
        html_content = []

        try:
            json_content: List[Dict[str, Any]] = json.loads(structured_content)
        except json.JSONDecodeError as err:
            raise HoyolabApiError(
                "Could not decode structured content to JSON!"
            ) from err

        for i, node in enumerate(json_content):
            next = json_content[i + 1] if i + 1 < len(json_content) else None

            if type(node["insert"]) is str:
                text = node["insert"]

                # skip spacer nodes
                if node["insert"] == "<br>":
                    continue

                # merge attributes of next spacer node into current
                if (
                    next is not None
                    and next["insert"] == "<br>"
                    and "attributes" in next
                ):
                    node["attributes"] = node.get("attributes", {})
                    node["attributes"].update(next["attributes"])

                if "attributes" in node:
                    if "link" in node["attributes"]:
                        text = '<a href="{}">{}</a>'.format(
                            node["attributes"]["link"], text
                        )
                    if "bold" in node["attributes"]:
                        text = "<strong>{}</strong>".format(text)
                    if "italic" in node["attributes"]:
                        text = "<em>{}</em>".format(text)
                    if "color" in node["attributes"]:
                        text = '<span color="{}">{}</span>'.format(
                            node["attributes"]["color"], text
                        )

                if "attributes" in node and "header" in node["attributes"]:
                    hn = node["attributes"]["header"]
                    text = f"<h{hn}>{text}</h{hn}>"
                else:
                    text = "<p>{}</p>".format(text)

                html_content.append(text)
            elif "image" in node["insert"]:
                attributes = node["insert"].get("attributes", {})
                attr_str = " ".join([f'{k}="{v}"' for k, v in attributes.items()])
                html_content.append(
                    '<div><img src="{}" {}></div>'.format(
                        node["insert"]["image"], attr_str
                    )
                )
            elif "video" in node["insert"]:
                pattern = re.compile(r".*youtube\.com\/embed\/([a-zA-Z0-9_-]+)\?.*")
                match = re.match(pattern, node["insert"]["video"])
                if match is not None:
                    yt_code = match.group(1)
                    html_content.append(
                        f'<p><strong>YouTube: <a href="https://youtu.be/{yt_code}">https://youtu.be/{yt_code}</a></strong></p>'
                    )
                else:
                    html_content.append(
                        f'<video src="{node["insert"]["video"]}">Watch the video here: {node["insert"]["video"]}</video>'
                    )
            elif "divider" in node["insert"]:
                img_url = "https://hyl-static-res-prod.hoyolab.com/divider_config/PC/{}.png".format(
                    node["insert"]["divider"]
                )
                html_content.append('<div><img src="{}"></div>'.format(img_url))

        return "".join(html_content)

    @staticmethod
    def _parse_gallery_post(content: str) -> str:
        """Parse the Hoyolab gallery post and return the constructed HTML."""

        content = re.sub(r"(\\)?\\n", "<br>", content)
        html_content = []

        try:
            json_content: Dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as err:
            raise HoyolabApiError("Could not decode gallery content to JSON!") from err

        if "describe" in json_content:
            html_content.append("<p>{}</p>".format(json_content["describe"]))

        if "imgs" in json_content and type(json_content["imgs"]) is list:
            for img in json_content["imgs"]:
                html_content.append('<p><img src="{}"></p>'.format(img))

        return "".join(html_content)

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

        return self._transform_post(post)

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

        item = {
            "id": post["post"]["post_id"],
            "title": post["post"]["subject"],
            "author": post["user"]["nickname"],
            "content": post["post"]["content"],
            "category": post["post"]["official_type"],
            "published": post["post"]["created_at"],
        }

        if "desc" in post["post"] and len(str(post["post"]["desc"]).strip()) > 0:
            item["summary"] = post["post"]["desc"]

        if post["last_modify_time"] > 0:
            item["updated"] = post["last_modify_time"]

        if len(post["cover_list"]) > 0:
            item["image"] = post["cover_list"][0]["url"]

        return pydantic.parse_obj_as(FeedItem, item)
