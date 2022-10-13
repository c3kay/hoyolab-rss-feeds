import json
from typing import Dict
from typing import List
from typing import Optional

import aiohttp
from pydantic import HttpUrl
from pydantic import parse_obj_as

from .errors import HoyolabApiError
from .models import FeedItem
from .models import FeedItemMeta
from .models import Game
from .models import Language
from .models import PostCategory

HOYOLAB_API_BASE_URL = 'https://bbs-api-os.hoyolab.com/community/post/wapi/'
DEFAULT_CATEGORY_SIZE = 5


class HoyolabNews:
    def __init__(
            self,
            game: Game,
            language: Language = Language.ENGLISH
    ):
        self._game = game
        self._lang = language.lower()

    async def _request(
            self,
            params: Dict,
            url: HttpUrl,
            session: Optional[aiohttp.ClientSession] = None
    ) -> Dict:
        """Send a GET request to the Hoyolab API endpoint."""

        local_session = session or aiohttp.ClientSession()

        headers = {
            'Origin': 'https://www.hoyolab.com',
            'X-Rpc-Language': self._lang
        }

        try:
            async with local_session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                response_json = await response.json(encoding='utf-8')

            if response_json['retcode'] != 0:
                # the message might be in chinese
                raise HoyolabApiError(response_json['message'])
        except aiohttp.ClientError as err:
            raise HoyolabApiError('Could not request Hoyolab endpoint!') from err
        except json.JSONDecodeError as err:
            raise HoyolabApiError('Could not decode JSON response!') from err
        except KeyError as err:
            raise HoyolabApiError('Unexpected response!') from err
        finally:
            if session is None:
                await local_session.close()

        return response_json

    async def get_news_list(
            self,
            category: PostCategory,
            category_size: int = DEFAULT_CATEGORY_SIZE,
            session: aiohttp.ClientSession = None
    ) -> List[Dict]:
        """Request an overview of the latest posts from Hoyolab."""

        params = {
            'gids': self._game,
            'page_size': category_size,
            'type': category
        }

        url = parse_obj_as(HttpUrl, HOYOLAB_API_BASE_URL + 'getNewsList')

        response = await self._request(params, url, session)

        return response['data']['list']

    async def get_post(
            self,
            post_id: int,
            session: Optional[aiohttp.ClientSession] = None
    ) -> Dict:
        """Request single post with full text from Hoyolab."""

        params = {
            'gids': self._game,
            'post_id': post_id
        }

        url = parse_obj_as(HttpUrl, HOYOLAB_API_BASE_URL + 'getPostFull')

        response = await self._request(params, url, session)

        return response['data']['post']

    async def get_latest_item_metas(
            self,
            category: PostCategory,
            category_size: int = DEFAULT_CATEGORY_SIZE,
            session: Optional[aiohttp.ClientSession] = None
    ) -> List[FeedItemMeta]:
        """Get the meta info of the latest posts in the specified category."""

        local_session = session or aiohttp.ClientSession()
        latest_posts = []

        category_posts = await self.get_news_list(category, category_size, local_session)

        for post in category_posts:
            published_ts = int(post['post']['created_at'])
            modified_ts = int(post['last_modify_time'])

            item_meta = {
                'id': post['post']['post_id'],
                'last_modified': max(published_ts, modified_ts)
            }

            # parsing for type conversions
            latest_posts.append(parse_obj_as(FeedItemMeta, item_meta))

        if session is None:
            await local_session.close()

        return latest_posts

    async def get_feed_item(
            self,
            post_id: int,
            session: Optional[aiohttp.ClientSession] = None
    ) -> FeedItem:
        """Get a single post as FeedItem."""

        post = await self.get_post(post_id, session)

        item = {
            'id': post['post']['post_id'],
            'title': post['post']['subject'],
            'author': post['user']['nickname'],
            'content': post['post']['content'],
            'category': post['post']['official_type'],
            'published': post['post']['created_at'],
        }

        if post['last_modify_time'] > 0:
            item['updated'] = post['last_modify_time']

        if len(post['image_list']) > 0:
            item['image'] = post['image_list'][0]['url']

        return parse_obj_as(FeedItem, item)
