import asyncio
import json
import re
from configparser import ConfigParser
from datetime import datetime
from os import environ
from os.path import exists
from os.path import join

import aiofiles
import atoma
import langdetect
import pytest
from aiohttp import ClientSession

import hoyolab


# -- FIXTURES -- #

@pytest.fixture(scope='session')
def event_loop():
    el = asyncio.get_event_loop()
    yield el
    el.close()


@pytest.fixture(scope='session')
async def session(event_loop):
    cs = ClientSession(loop=event_loop, raise_for_status=True)
    yield cs
    await cs.close()


@pytest.fixture(params=[1, 2, 4, 6, 8], ids=['honkai', 'genshin', 'themis', 'starrail', 'zenless'])
def game_id(request):
    return request.param


@pytest.fixture(params=[1, 2, 3], ids=['notices', 'events', 'info'])
def category_id(request):
    return request.param


@pytest.fixture
def json_path(tmpdir):
    return join(tmpdir, 'json_feed.json')


@pytest.fixture
def atom_path(tmpdir):
    return join(tmpdir, 'atom_feed.xml')


@pytest.fixture
def feed_config(tmpdir):
    conf_file = join(tmpdir, 'my-feeds.conf')

    conf_parser = ConfigParser()
    conf_parser.add_section('genshin')
    conf_parser.add_section('honkai')
    conf_parser.set('genshin', 'json_path', join(tmpdir, 'genshin.json'))
    conf_parser.set('genshin', 'atom_path', join(tmpdir, 'genshin.xml'))
    conf_parser.set('genshin', 'entries', '1')
    conf_parser.set('honkai', 'json_path', join(tmpdir, 'honkai.json'))
    conf_parser.set('honkai', 'atom_path', join(tmpdir, 'honkai.xml'))
    conf_parser.set('honkai', 'entries', '1')

    with open(conf_file, 'w') as f:
        conf_parser.write(f)

    environ['HOYOLAB_CONFIG_PATH'] = conf_file

    return conf_parser


# -- FEED LOGIC TESTS -- #

def test_game_id_mapping():
    assert hoyolab.get_game_id('honkai') == 1
    assert hoyolab.get_game_id('genshin') == 2
    assert hoyolab.get_game_id('Themis') == 4
    assert hoyolab.get_game_id('starRail') == 6
    assert hoyolab.get_game_id('zEnlEss') == 8

    with pytest.raises(hoyolab.HoyolabError):
        hoyolab.get_game_id('minecraft')


def test_news_category_mapping():
    assert hoyolab.get_category_name(1) == 'Notices'
    assert hoyolab.get_category_name(2) == 'Events'
    assert hoyolab.get_category_name(3) == 'Info'

    with pytest.raises(hoyolab.HoyolabError):
        hoyolab.get_category_name(42)


def test_id_diff():
    known = {
        '1': 1645564942,
        '3': 1645564943
    }

    fetched = {
        '1': 1645564945,
        '3': 1645564943,
        '5': 1645564944
    }

    assert hoyolab.get_post_id_diff(fetched, known) == ['1', '5']


def test_known_post_ids():
    feed_items = [
        {
            'id': '12345',
            'date_published': '2022-02-22T22:22:22+00:00'
        },
        {
            'id': '23456',
            'date_published': '2022-03-23T03:03:03+01:00',
            'date_modified': '2022-03-23T03:33:03+01:00',
        }
    ]

    expected = {
        '12345': 1645568542,
        '23456': 1648002783
    }

    assert hoyolab.get_known_post_ids(feed_items) == expected


def test_latest_post_ids():
    posts = [
        {
            'post': {
                'post_id': '12345',
                'created_at': 1645564942
            },
            'last_modify_time': 1645564943
        },
        {
            'post': {
                'post_id': '23456',
                'created_at': 1645564944
            },
            'last_modify_time': 0
        }
    ]

    expected = {
        '12345': 1645564943,
        '23456': 1645564944
    }

    assert hoyolab.get_latest_post_ids(posts) == expected


# -- API & IO TESTS -- #

async def test_request_news(session, game_id, category_id):
    req = await hoyolab.request_news(session, game_id, category_id, 3)

    assert type(req) is list
    assert len(req) > 0

    for post in req:
        validate_api_response(post)


async def test_request_post(session, game_id):
    post_ids = {
        1: 4361615,
        2: 4326670,
        4: 4283335,
        6: 3746616,
        8: 4729212
    }

    req = await hoyolab.request_post(session, game_id, post_ids[game_id])

    validate_api_response(req)


async def test_language(session):
    # NOTE: not checking subject/title because it is often too short to be detected correctly

    # apparently needed to get constant results
    langdetect.DetectorFactory.seed = 42

    req_news = await hoyolab.request_news(session, 2, 1, 1, 'de-de')

    for post in req_news:
        validate_api_response(post)
        assert langdetect.detect(post['post']['content']) == 'de'

    req_post = await hoyolab.request_post(session, 2, 4326670, 'es-ES')

    validate_api_response(req_post)
    assert langdetect.detect(req_post['post']['content']) == 'es'


async def test_file_io(json_path, atom_path):
    await hoyolab.create_json_feed_file(1, json_path, '-', '-', '-', '-', '-', [])
    await hoyolab.create_atom_feed_file(1, atom_path, '-', '-', '-', '-', '-', [])

    assert exists(json_path)
    assert exists(atom_path)

    assert await hoyolab.load_json_feed_items(json_path) == {1: [], 2: [], 3: []}
    assert await hoyolab.load_json_feed_items('/i-dont-exist.json') == {1: [], 2: [], 3: []}

    with pytest.raises(hoyolab.HoyolabError):
        await hoyolab.create_json_feed_file(1, '/i-dont-exist.json', '', '', '', '', '', [])

    with pytest.raises(hoyolab.HoyolabError):
        await hoyolab.create_atom_feed_file(1, '/i-dont-exist.xml', '', '', '', '', '', [])


# -- FEED TESTS -- #

async def test_feed(session, json_path, atom_path, game_id):
    num_entries = 3
    feed_title = 'Hoyolab Game News'
    feed_author = 'Unknown'
    feed_icon = 'https://example.org/favicon.ico'
    atom_url = 'https://example.org/atom_feed.xml'
    json_url = 'https://example.org/json_feed.json'

    await hoyolab.create_game_feeds(
        session,
        game_id,
        json_path,
        atom_path,
        json_url,
        atom_url,
        feed_icon,
        feed_title,
        feed_author,
        num_entries
    )

    assert exists(json_path)

    async with aiofiles.open(json_path, 'r') as fd:
        feed_str = await fd.read()

    json_feed = atoma.parse_json_feed(json.loads(feed_str))
    validate_json_feed(json_feed, game_id, feed_title, feed_icon, json_url, num_entries*3)

    assert exists(atom_path)

    async with aiofiles.open(atom_path, 'rb') as fd:
        feed_bytes = await fd.read()

    atom_feed = atoma.parse_atom_bytes(feed_bytes)
    validate_atom_feed(atom_feed, game_id, feed_title, feed_author, feed_icon, atom_url, num_entries*3)


async def test_config(event_loop, feed_config):
    await hoyolab.create_game_feeds_from_config(event_loop=event_loop)

    for game in feed_config.sections():
        conf_game = feed_config[game]
        assert exists(conf_game.get('json_path'))
        assert exists(conf_game.get('atom_path'))

    environ['HOYOLAB_CONFIG_PATH'] = '/i-dont-exist.conf'
    with pytest.raises(hoyolab.HoyolabError):
        await hoyolab.create_game_feeds_from_config(event_loop=event_loop)

    empty_config = ConfigParser()
    with pytest.raises(hoyolab.HoyolabError):
        await hoyolab.create_game_feeds_from_config(config=empty_config, event_loop=event_loop)


# -- HELPER / VALIDATE FUNCTIONS -- #

def validate_json_feed(json_feed, gid, title, icon, url, max_entries):
    # authors (v1.1) not yet supported by atoma -> waiting for 0.0.18
    assert json_feed.title == title
    assert json_feed.icon == icon
    assert json_feed.feed_url == url
    assert json_feed.home_page_url == 'https://www.hoyolab.com/official/{}'.format(gid)
    assert json_feed.version == 'https://jsonfeed.org/version/1.1'
    assert len(json_feed.items) > 0
    assert len(json_feed.items) <= max_entries

    prev_published_ts = datetime.now().timestamp()

    for item in json_feed.items:
        assert re.fullmatch(r'\d+', item.id_) is not None
        assert item.url == 'https://www.hoyolab.com/article/{}'.format(item.id_)
        assert re.fullmatch(r'(Notices|Info|Events)', item.tags[0]) is not None
        assert len(item.title) > 0
        assert len(item.content_html) > 0

        published_ts = item.date_published.timestamp()
        assert published_ts > 0
        assert published_ts <= prev_published_ts
        prev_published_ts = published_ts

        if item.date_modified is not None:
            modified_ts = item.date_modified.timestamp()
            assert modified_ts > 0
            assert modified_ts >= published_ts

        if item.image is not None:
            assert re.fullmatch(r'https://.+\.(jp(e)?g|png)', item.image, flags=re.IGNORECASE) is not None


def validate_atom_feed(atom_feed, gid, title, author, icon, url, max_entries):
    assert atom_feed.id_ == 'tag:hoyolab.com,2021:/official/{}'.format(gid)
    assert atom_feed.title.value == title
    assert atom_feed.authors[0].name == author
    assert atom_feed.icon == icon

    for link in atom_feed.links:
        if link.rel == 'self':
            assert link.href == url
        elif link.rel == 'alternate':
            assert link.href == 'https://www.hoyolab.com/official/{}'.format(gid)
        else:
            raise ValueError('Unknown link relation {}'.format(link.rel))

    assert len(atom_feed.entries) > 0
    assert len(atom_feed.entries) <= max_entries

    prev_published_ts = datetime.now().timestamp()

    for entry in atom_feed.entries:
        assert re.fullmatch(r'tag:hoyolab\.com,\d{4}(-\d{2}){2}:\d+', entry.id_) is not None
        assert entry.links[0].rel == 'alternate'
        assert re.fullmatch(r'https://www.hoyolab.com/article/\d+', entry.links[0].href) is not None
        assert re.fullmatch(r'(Notices|Info|Events)', entry.categories[0].term) is not None
        assert len(entry.title.value) > 0
        assert len(entry.content.value) > 0

        published_ts = entry.published.timestamp()
        assert published_ts > 0
        assert published_ts <= prev_published_ts
        prev_published_ts = published_ts

        modified_ts = entry.updated.timestamp()
        assert modified_ts > 0
        assert modified_ts >= published_ts


def validate_api_response(post):
    assert type(post) is dict
    assert type(post['post']['post_id']) is str
    assert re.fullmatch(r'\d+', post['post']['post_id']) is not None
    assert type(post['post']['created_at']) is int
    assert post['post']['created_at'] > 0
    assert type(post['last_modify_time']) is int
    assert post['last_modify_time'] >= 0
    assert type(post['post']['official_type']) is int
    assert type(post['post']['content']) is str
    assert len(post['post']['content']) > 0
    assert type(post['post']['subject']) is str
    assert len(post['post']['subject']) > 0
