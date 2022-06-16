import asyncio
import json
from configparser import ConfigParser
from datetime import datetime
from os import getenv
from os.path import exists
from xml.dom import minidom

import aiohttp
import aiofiles


# -- CUSTOM ERROR CLASS -- #

class HoyolabError(Exception):
    pass


# -- MAPPINGS -- #

def get_category_name(category_id):
    categories = {
        1: 'Notices',
        2: 'Events',
        3: 'Info'
    }

    if category_id not in categories:
        raise HoyolabError('Unknown category ID ({})!'.format(category_id))

    return categories[category_id]


def get_game_id(game_name):
    # 3 = unused ; 5 = hoyolab internal news ; 7 = unused
    games = {
        'honkai': 1,
        'genshin': 2,
        'themis': 4,
        'starrail': 6,
        'zenless': 8
    }

    game_name = game_name.lower()

    if game_name not in games:
        raise HoyolabError('Unknown game "{}"!'.format(game_name))

    return games[game_name]


# -- REQUESTS -- #

async def request_news(session, game_id, category, num_entries, lang='en-us'):
    lang = lang.lower()

    headers = {
        'Origin': 'https://www.hoyolab.com',
        'X-Rpc-Language': lang
    }

    params = {
        'gids': game_id,
        'page_size': num_entries,
        'type': category
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'

    try:
        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            response_json = await response.json(encoding='utf-8')

        if response_json['retcode'] != 0:
            # the message might be in chinese
            raise HoyolabError(response_json['message'])

        return response_json['data']['list']
    except aiohttp.ClientError as err:
        raise HoyolabError('Could not request news!') from err
    except json.JSONDecodeError as err:
        raise HoyolabError('Could not decode JSON response!') from err
    except KeyError as err:
        raise HoyolabError('Unexpected response!') from err


async def request_post(session, game_id, post_id, lang='en-us'):
    lang = lang.lower()

    headers = {
        'Origin': 'https://www.hoyolab.com',
        'X-Rpc-Language': lang
    }

    params = {
        'gids': game_id,
        'post_id': post_id
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull'

    try:
        async with session.get(url, headers=headers, params=params) as response:
            response.raise_for_status()
            response_json = await response.json(encoding='utf-8')

        if response_json['retcode'] != 0:
            # the message might be in chinese
            raise HoyolabError(response_json['message'])

        return response_json['data']['post']
    except aiohttp.ClientError as err:
        raise HoyolabError('Could not request news!') from err
    except json.JSONDecodeError as err:
        raise HoyolabError('Could not decode JSON response!') from err
    except KeyError as err:
        raise HoyolabError('Unexpected response!') from err


# -- JSON FEED -- #

async def create_json_feed_file(game_id, path, url, icon, lang, title, author, items):
    feed = {
        'version': 'https://jsonfeed.org/version/1.1',
        'title': title,
        'home_page_url': 'https://www.hoyolab.com/official/{}'.format(game_id),
        'feed_url': url,
        'icon': icon,
        'language': lang,
        'authors': [{'name': author}],
        'items': items
    }

    try:
        async with aiofiles.open(path, 'w', encoding='utf-8') as fd:
            feed_json = json.dumps(feed)
            await fd.write(feed_json)
    except IOError as err:
        raise HoyolabError('Could not write JSON file to "{}"!'.format(path)) from err


async def load_json_feed_items(path):
    if not exists(path):
        # create empty feed dict
        return {category_id: [] for category_id in range(1, 4)}

    try:
        async with aiofiles.open(path, 'r', encoding='utf-8') as fd:
            feed_json = await fd.read()
            feed = json.loads(feed_json)

        feed_by_category = {}
        for category_id in range(1, 4):
            category_name = get_category_name(category_id)
            feed_by_category[category_id] = list(filter(lambda x: 'tags' in x and x['tags'][0] == category_name,
                                                        feed['items']))

        return feed_by_category
    except IOError as err:
        raise HoyolabError('Could not read JSON file from "{}"!'.format(path)) from err
    except json.JSONDecodeError as err:
        raise HoyolabError('Could not decode JSON file!') from err


def create_json_feed_item(post):
    published_str = datetime.fromtimestamp(post['post']['created_at']).astimezone().isoformat()
    content = post['post']['content']
    category_name = get_category_name(post['post']['official_type'])

    if content.startswith(('<p><br></p>', '<p></p>', '<p>&nbsp;</p>')):
        content = content.partition('</p>')[2]

    item = {
        'id': post['post']['post_id'],
        'url': 'https://www.hoyolab.com/article/{}'.format(post['post']['post_id']),
        'title': post['post']['subject'],
        'tags': [category_name],
        'content_html': content,
        'date_published': published_str
    }

    if post['last_modify_time'] > 0:
        modified_str = datetime.fromtimestamp(post['last_modify_time']).astimezone().isoformat()
        item['date_modified'] = modified_str

    if len(post['image_list']) > 0:
        item['image'] = post['image_list'][0]['url']

    return item


# -- ATOM FEED -- #

async def create_atom_feed_file(game_id, path, url, icon, lang, title, author, json_feed_items):
    doc = minidom.getDOMImplementation().createDocument(None, 'feed', None)
    root = doc.documentElement

    # workaround...
    root.setAttribute('xmlns', 'http://www.w3.org/2005/Atom')
    root.setAttribute('xml:lang', lang)

    append_text_node(doc, root, 'id', 'tag:hoyolab.com,2021:/official/{}'.format(game_id))
    append_text_node(doc, root, 'title', title)
    append_text_node(doc, root, 'updated', datetime.now().astimezone().isoformat())
    append_attr_node(doc, root, 'link', {'href': 'https://www.hoyolab.com/official/{}'.format(game_id),
                                         'rel': 'alternate', 'type': 'text/html'})
    append_attr_node(doc, root, 'link', {'href': url, 'rel': 'self', 'type': 'application/atom+xml'})
    append_text_node(doc, root, 'icon', icon)

    author_el = doc.createElement('author')
    append_text_node(doc, author_el, 'name', author)
    root.appendChild(author_el)

    for item in json_feed_items:
        entry = create_atom_entry_from_json_item(doc, item)
        root.appendChild(entry)

    try:
        async with aiofiles.open(path, 'w', encoding='utf-8') as fd:
            await fd.write(doc.toxml())
    except IOError as err:
        raise HoyolabError('Could not write Atom file to "{}"!'.format(path)) from err


def create_atom_entry_from_json_item(doc, json_item):
    entry = doc.createElement('entry')

    published_day = json_item['date_published'].partition('T')[0]
    append_text_node(doc, entry, 'id', 'tag:hoyolab.com,{}:{}'.format(published_day, json_item['id']))

    append_text_node(doc, entry, 'title', json_item['title'])
    append_attr_node(doc, entry, 'link', {'href': json_item['url'], 'rel': 'alternate', 'type': 'text/html'})
    append_attr_node(doc, entry, 'category', {'term': json_item['tags'][0]})
    append_text_node(doc, entry, 'published', json_item['date_published'])

    updated = json_item['date_modified'] if 'date_modified' in json_item else json_item['date_published']
    append_text_node(doc, entry, 'updated', updated)

    append_text_node(doc, entry, 'content', json_item['content_html'], attr={'type': 'html'})

    return entry


def append_text_node(doc, parent, name, text, attr=None):
    node = doc.createElement(name)
    node.appendChild(doc.createTextNode(text))
    if attr is not None:
        for key, val in attr.items():
            node.setAttribute(key, val)
    parent.appendChild(node)


def append_attr_node(doc, parent, name, attr):
    node = doc.createElement(name)
    for key, val in attr.items():
        node.setAttribute(key, val)
    parent.appendChild(node)


# -- FEED LOGIC -- #

def get_known_post_ids(feed_items):
    known_ids = {}

    # create dict of known ids with their latest modification timestamp
    for item in feed_items:
        published_ts = datetime.fromisoformat(item['date_published']).timestamp()
        modified_ts = datetime.fromisoformat(item['date_modified']).timestamp() if 'date_modified' in item else 0
        known_ids[item['id']] = int(max(published_ts, modified_ts))

    return known_ids


def get_latest_post_ids(posts):
    fetched_ids = {}

    # create dict of fetched ids with their latest modification timestamp
    for post in posts:
        post_id = post['post']['post_id']
        published_ts = post['post']['created_at']
        modified_ts = post['last_modify_time']
        fetched_ids[post_id] = int(max(published_ts, modified_ts))

    return fetched_ids


def get_post_id_diff(fetched_ids, known_ids):
    new_ids = []

    for fetched_id, fetched_modified_ts in fetched_ids.items():
        if fetched_id not in known_ids or (fetched_id in known_ids and fetched_modified_ts > known_ids[fetched_id]):
            new_ids.append(fetched_id)

    return new_ids


async def create_game_feeds(session, game_id, json_path, atom_path, json_url, atom_url, icon, title, author,
                            num_entries=5, lang='en-us'):
    # json feed as reference for known items since it is easier to parse...
    feed_items_by_category = await load_json_feed_items(json_path)

    feed_items_combined = []
    was_updated = False

    # concurrently fetch news from all categories
    category_news = await asyncio.gather(
        *[request_news(session, game_id, category_id, num_entries, lang)
          for category_id in feed_items_by_category.keys()]
    )

    for fetched_posts, category_items in zip(category_news, feed_items_by_category.values()):
        known_ids = get_known_post_ids(category_items)
        fetched_ids = get_latest_post_ids(fetched_posts)
        id_diff = get_post_id_diff(fetched_ids, known_ids)

        # remove modified items if any from category feed
        if len(id_diff) > 0 and len(category_items) > 0:
            category_items = list(filter(lambda x: x['id'] not in id_diff, category_items))

        # concurrently fetch full text of all new or edited posts
        fetched_full_posts = await asyncio.gather(
            *[request_post(session, game_id, post_id, lang) for post_id in id_diff]
        )

        # convert posts to items and add to category feed
        category_items.extend([create_json_feed_item(post) for post in fetched_full_posts])

        # cut off older entries if new have been added
        if len(id_diff) > 0:
            category_items.sort(key=lambda x: int(x['id']), reverse=True)
            category_items = category_items[:num_entries]
            was_updated = True

        # add category items to feed
        feed_items_combined.extend(category_items)

    if was_updated or not exists(atom_path):
        feed_items_combined.sort(key=lambda x: int(x['id']), reverse=True)

        # concurrently create feed files
        await asyncio.gather(
            create_atom_feed_file(game_id, atom_path, atom_url, icon, lang, title, author, feed_items_combined),
            create_json_feed_file(game_id, json_path, json_url, icon, lang, title, author, feed_items_combined)
        )


async def create_game_feeds_from_config(config=None, event_loop=None):
    # read config from file
    if config is None:
        path = getenv('HOYOLAB_CONFIG_PATH', 'feeds.conf')
        try:
            async with aiofiles.open(path, 'r') as fd:
                conf_str = await fd.read()
        except IOError as err:
            raise HoyolabError('Could not open config file at "{}"'.format(path)) from err

        conf_parser = ConfigParser()
        conf_parser.read_string(conf_str)
    # use param config parser
    else:
        conf_parser = config

    games = conf_parser.sections()
    if len(games) == 0:
        raise HoyolabError('No feeds configured!')

    game_configs = [(get_game_id(game), conf_parser[game]) for game in games]

    async with aiohttp.ClientSession(loop=event_loop) as session:
        # concurrently create game feeds
        await asyncio.gather(
            *[
                create_game_feeds(
                    session,
                    game_id,
                    conf.get('json_path', 'feed.json'),
                    conf.get('atom_path', 'feed.xml'),
                    conf.get('json_url', 'feed.json'),
                    conf.get('atom_url', 'feed.xml'),
                    conf.get('icon', 'https://img-os-static.hoyolab.com/favicon.ico'),
                    conf.get('title', 'Untitled'),
                    conf.get('author', 'Unknown'),
                    int(conf.get('entries', '5')),
                    conf.get('language', 'en-us')
                )
                for game_id, conf in game_configs
            ]
        )


if __name__ == '__main__':
    asyncio.run(create_game_feeds_from_config())
