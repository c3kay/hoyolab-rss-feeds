from datetime import datetime
from datetime import timezone

import aiohttp
import langdetect  # type: ignore
import pydantic
import pytest
import pytest_mock

from hoyolabrssfeeds import errors
from hoyolabrssfeeds import hoyolab
from hoyolabrssfeeds import models
from .conftest import validate_hoyolab_post

# force consistent results
langdetect.DetectorFactory.seed = 0


@pytest.mark.hoyolabapi
async def test_api_post_endpoint(
    client_session: aiohttp.ClientSession, game: models.Game
) -> None:
    post_id = get_post_id(game)
    api = hoyolab.HoyolabNews(game)
    post = await api.get_post(client_session, post_id)

    validate_hoyolab_post(post, is_full_post=True)


@pytest.mark.hoyolabapi
async def test_api_list_endpoint(
    client_session: aiohttp.ClientSession,
    game: models.Game,
    category: models.FeedItemCategory,
) -> None:
    api = hoyolab.HoyolabNews(game)
    news_list = await api.get_news_list(client_session, category, 2)

    assert type(news_list) is list
    assert len(news_list) > 0

    for post in news_list:
        validate_hoyolab_post(post, is_full_post=False)


@pytest.mark.hoyolabapi
@pytest.mark.xfail(reason="not accurate for all languages")
async def test_language(
    client_session: aiohttp.ClientSession, language: models.Language
) -> None:
    # NOTE: The list endpoint is not checked due to insufficient text.
    # The text of the list endpoint is also not used for the feeds.

    api = hoyolab.HoyolabNews(models.Game.GENSHIN, language)

    post_id = 14189622
    post = await api.get_post(client_session, post_id)
    content = post["post"]["content"]

    # only use first letters of code if not chinese
    # https://github.com/Mimino666/langdetect
    expected = language.lower()
    if not expected.startswith("zh"):
        expected = expected.partition("-")[0]

    assert langdetect.detect(content) == expected


@pytest.mark.hoyolabapi
async def test_request_errors(client_session: aiohttp.ClientSession) -> None:
    api = hoyolab.HoyolabNews(models.Game.GENSHIN)

    # request error
    error_url = pydantic.parse_obj_as(
        pydantic.HttpUrl, "https://httpbin.org/status/500"
    )
    with pytest.raises(errors.HoyolabApiError, match="Could not request"):
        await api._request(client_session, {}, error_url)

    # decode error
    error_url = pydantic.parse_obj_as(pydantic.HttpUrl, "https://httpbin.org/html")
    with pytest.raises(errors.HoyolabApiError, match="Could not decode"):
        await api._request(client_session, {}, error_url)

    # unexpected response
    error_url = pydantic.parse_obj_as(pydantic.HttpUrl, "https://httpbin.org/json")
    with pytest.raises(errors.HoyolabApiError, match="Unexpected response"):
        await api._request(client_session, {}, error_url)

    # hoyolab error code
    error_url = pydantic.parse_obj_as(
        pydantic.HttpUrl,
        "https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList",
    )
    with pytest.raises(errors.HoyolabApiError):
        # missing params raise exception here
        await api._request(client_session, {}, error_url)


async def test_get_latest_item_metas(
    mocker: pytest_mock.MockFixture, client_session: aiohttp.ClientSession
) -> None:
    posts = [
        {"post": {"post_id": "42", "created_at": 1645564944}, "last_modify_time": 0},
        {
            "post": {"post_id": "41", "created_at": 1645564942},
            "last_modify_time": 1645564943,
        },
    ]

    mocked_news_list = mocker.patch(
        "hoyolabrssfeeds.hoyolab.HoyolabNews.get_news_list",
        spec=True,
        return_value=posts,
    )

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    metas = await api.get_latest_item_metas(
        client_session, models.FeedItemCategory.INFO, 2
    )

    expected = [
        models.FeedItemMeta(
            id=42, last_modified=datetime.fromtimestamp(1645564944, tz=timezone.utc)
        ),
        models.FeedItemMeta(
            id=41, last_modified=datetime.fromtimestamp(1645564943, tz=timezone.utc)
        ),
    ]

    mocked_news_list.assert_awaited()
    mocked_news_list.assert_called()

    assert metas == expected


async def test_get_feed_item(
    mocker: pytest_mock.MockFixture,
    feed_item: models.FeedItem,
    client_session: aiohttp.ClientSession,
) -> None:
    post = {
        "post": {
            "post_id": str(feed_item.id),
            "subject": feed_item.title,
            "content": feed_item.content,
            "desc": feed_item.summary,
            "official_type": feed_item.category.value,
            "created_at": int(feed_item.published.timestamp()),
        },
        "user": {"nickname": feed_item.author},
        "last_modify_time": int(
            feed_item.updated.timestamp() if feed_item.updated else 0
        ),
        "cover_list": [{"url": str(feed_item.image)}],
    }

    mocked_get_post = mocker.patch(
        "hoyolabrssfeeds.hoyolab.HoyolabNews.get_post", spec=True, return_value=post
    )

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    fetched_item = await api.get_feed_item(client_session, feed_item.id)

    mocked_get_post.assert_awaited()
    mocked_get_post.assert_called()

    assert fetched_item == feed_item


def test_leading_line_breaks() -> None:
    post = {"post": {"content": "<p><br></p>Hello World"}}

    expected = {"post": {"content": "Hello World"}}

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    transformed_post = api._transform_post(post)

    assert transformed_post == expected


def test_private_link_bug() -> None:
    post = {
        "post": {
            "content": '<img src="https://hoyolab-upload-private.hoyolab.com/test.jpg">'
        }
    }

    expected = {
        "post": {"content": '<img src="https://upload-os-bbs.hoyolab.com/test.jpg">'}
    }

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    transformed_post = api._transform_post(post)

    assert transformed_post == expected


def test_content_html_bug() -> None:
    post = {"post": {"content": "en-us", "structured_content": "[]"}}

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    transformed_post = api._transform_post(post)

    # test that the content was replaced/fixed
    assert transformed_post["post"]["content"] != "en-us"


def test_structured_content_parser() -> None:
    raw_sc = """
        [{"insert":"Hello World!"},
        {"insert":"Hello bold World!","attributes":{"bold":true}},
        {"insert":"Hello italic World!","attributes":{"italic":true}},
        {"insert":"\\n","attributes":{"align":"center"}},
        {"insert":"Hello Link!","attributes":{"link":"https://example.com"}},
        {"insert":{"image":"https://example.com/image.jpg"}},
        {"insert":{"video":"https://example.com/video.mp4"}}]
    """

    expected_html = """
        <p>Hello World!</p>
        <p><strong>Hello bold World!</strong></p>
        <p><em>Hello italic World!</em></p>
        <p><br></p>
        <p><a href="https://example.com">Hello Link!</a></p>
        <img src="https://example.com/image.jpg">
        <iframe src="https://example.com/video.mp4"></iframe>
    """.replace(
        "    ", ""
    ).replace(
        "\n", ""
    )

    assert hoyolab.HoyolabNews._parse_structured_content(raw_sc) == expected_html

    with pytest.raises(errors.HoyolabApiError):
        hoyolab.HoyolabNews._parse_structured_content("###")


def test_video_post() -> None:
    post = {
        "post": {
            "content": '{"video": "https://example.com/video.mp4"}',
            "view_type": 5,
            "desc": "Hello world!",
        },
        "video": {
            "url": "https://example.com/video.mp4",
            "cover": "https://example.com/cover.jpg",
        },
    }

    api = hoyolab.HoyolabNews(models.Game.GENSHIN)
    transformed_post = api._transform_post(post)
    expected = (
        '<video src="https://example.com/video.mp4" poster="https://example.com/cover.jpg" controls playsinline>Watch '
        "the video here: https://example.com/video.mp4</video><p>Hello world!</p>"
    )

    assert transformed_post["post"]["content"] == expected


# ---- HELPER FUNCTIONS ----


def get_post_id(game: models.Game) -> int:
    post_ids = {
        models.Game.HONKAI: 4361615,
        models.Game.GENSHIN: 7156359,
        models.Game.THEMIS: 4283335,
        models.Game.STARRAIL: 3746616,
        models.Game.ZENLESS: 4729212,
        models.Game.NEXUS: 40785878,
    }

    return post_ids[game]
