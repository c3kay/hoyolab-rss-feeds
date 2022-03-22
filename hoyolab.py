import requests
import json
from os.path import exists
from os import getenv
from configparser import ConfigParser
from time import sleep
from datetime import datetime
from xml.dom import minidom


# -- REQUESTS -- #

def request_news(game_id, category, num_entries, lang='en-US'):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.hoyolab.com',
        'X-Rpc-Language': lang
    }

    params = {
        'gids': game_id,
        'page_size': num_entries,
        'type': category
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'
    res = requests.get(url, headers=headers, params=params)

    try:
        res.raise_for_status()
        j = res.json()
        res.close()

        if j['retcode'] != 0:
            # the message might be in chinese
            raise RuntimeError('Hoyolab error occurred: "{}"'.format(j['message']))

        return j['data']['list']
    except requests.HTTPError as err:
        raise RuntimeError('Could not request news!') from err
    except json.JSONDecodeError as err:
        raise RuntimeError('Could not parse json response!') from err
    except KeyError as err:
        raise RuntimeError('Unexpected response!') from err


def request_post(game_id, post_id, lang='en-US'):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.hoyolab.com',
        'X-Rpc-Language': lang
    }

    params = {
        'gids': game_id,
        'post_id': post_id
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull'
    res = requests.get(url, headers=headers, params=params)

    try:
        res.raise_for_status()
        j = res.json()
        res.close()

        if j['retcode'] != 0:
            # the message might be in chinese
            raise RuntimeError('Hoyolab error occurred: "{}"'.format(j['message']))

        return j['data']['post']
    except requests.HTTPError as err:
        raise RuntimeError('Could not request post!') from err
    except json.JSONDecodeError as err:
        raise RuntimeError('Could not parse json response!') from err
    except KeyError as err:
        raise RuntimeError('Unexpected response!') from err


# -- JSON FEED -- #

def create_json_feed_file(game_id, path, url, icon, lang, title, author, items):
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
        with open(path, 'w', encoding='utf-8') as fd:
            json.dump(feed, fd)
    except IOError as err:
        raise RuntimeError('Could not write json file to {}!'.format(path)) from err


def load_json_feed_items(path):
    try:
        with open(path, 'r') as fd:
            feed = json.load(fd)
        return feed['items']
    except IOError:
        # file not found -> create new feed list
        return []


def create_json_feed_item(post):
    ct = datetime.fromtimestamp(post['post']['created_at']).astimezone().isoformat()
    post_id = post['post']['post_id']
    content = post['post']['content']

    if content.startswith(('<p><br></p>', '<p></p>', '<p>&nbsp;</p>')):
        content = content.partition('</p>')[2]

    item = {
        'id': post_id,
        'url': 'https://www.hoyolab.com/article/{}'.format(post_id),
        'title': post['post']['subject'],
        'content_html': content,
        'date_published': ct
    }

    if post['last_modify_time'] > 0:
        mt = datetime.fromtimestamp(post['last_modify_time']).astimezone().isoformat()
        item['date_modified'] = mt

    if len(post['image_list']) > 0:
        item['image'] = post['image_list'][0]['url']

    return item


# -- ATOM FEED -- #

def create_atom_feed_file(game_id, path, url, icon, lang, title, author, items):
    doc = minidom.getDOMImplementation().createDocument(None, 'feed', None)
    root = doc.documentElement

    # workaround...
    root.setAttribute('xmlns', 'http://www.w3.org/2005/Atom')
    root.setAttribute('xml:lang', lang)

    append_text_node(doc, root, 'id', 'tag:hoyolab.com,2021:/official/{}'.format(game_id))
    append_text_node(doc, root, 'title', title)
    append_text_node(doc, root, 'updated', datetime.now().astimezone().isoformat())
    append_attr_node(doc, root, 'link', {'href': 'https://www.hoyolab.com/official/{:d}'.format(game_id),
                                         'rel': 'alternate', 'type': 'text/html'})
    append_attr_node(doc, root, 'link', {'href': url, 'rel': 'self', 'type': 'application/atom+xml'})
    append_text_node(doc, root, 'icon', icon)

    author_el = doc.createElement('author')
    append_text_node(doc, author_el, 'name', author)
    root.appendChild(author_el)

    for item in items:
        entry = create_atom_feed_entry(doc, item)
        root.appendChild(entry)

    try:
        with open(path, 'w', encoding='utf-8') as fd:
            doc.writexml(fd, encoding='utf-8')
    except IOError as err:
        raise RuntimeError('Could not write atom file to {}!'.format(path)) from err


def create_atom_feed_entry(doc, feed_item):
    entry = doc.createElement('entry')

    p_date = datetime.fromisoformat(feed_item['date_published'])
    append_text_node(doc, entry, 'id', 'tag:hoyolab.com,{:%Y-%m-%d}:{}'.format(p_date, feed_item['id']))

    append_text_node(doc, entry, 'title', feed_item['title'])
    append_attr_node(doc, entry, 'link', {'href': feed_item['url'], 'rel': 'alternate', 'type': 'text/html'})
    append_text_node(doc, entry, 'published', feed_item['date_published'])

    updated = feed_item['date_modified'] if 'date_modified' in feed_item else feed_item['date_published']
    append_text_node(doc, entry, 'updated', updated)

    append_text_node(doc, entry, 'content', feed_item['content_html'], attr={'type': 'html'})

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

    for item in feed_items:
        ct = datetime.fromisoformat(item['date_published']).timestamp()
        mt = datetime.fromisoformat(item['date_modified']).timestamp() if 'date_modified' in item else 0
        known_ids[item['id']] = max(ct, mt)

    # dict of ids with latest modification timestamp
    return known_ids


def get_latest_post_ids(game_id, num_entries, lang):
    all_posts = []

    # collect posts from all 3 news categories
    for cat in range(1, 4):
        cat_news = request_news(game_id, cat, num_entries, lang)
        all_posts.extend(cat_news)

    # dict of ids with latest modification timestamp
    return {p['post']['post_id']: max(p['last_modify_time'], p['post']['created_at']) for p in all_posts}


def get_post_id_diff(fetched_ids, known_ids):
    new_ids = []

    for post_id, modified in fetched_ids.items():
        if post_id not in known_ids or (post_id in known_ids and modified > known_ids[post_id]):
            new_ids.append(post_id)

    return new_ids


def get_game_id(game_name):
    # 3 = unused ; 5 = hoyolab internal news
    games = {
        'honkai': 1,
        'genshin': 2,
        'tearsofthemis': 4,
        'starrail': 6
    }

    game_name = game_name.lower()

    if game_name not in games:
        raise RuntimeError('Unknown game "{}"'.format(game_name))

    return games[game_name]


def create_game_feeds(game_id, json_path, atom_path, json_url, atom_url, icon, title, author, num_entries=5,
                      lang='en-US'):
    # json feed as reference for known items since it is easier to parse...
    feed_items = load_json_feed_items(json_path)

    known_ids = get_known_post_ids(feed_items)
    fetched_ids = get_latest_post_ids(game_id, num_entries, lang)
    id_diff = get_post_id_diff(fetched_ids, known_ids)

    # remove modified items from feed item list (if exists)
    if len(id_diff) > 0 and len(feed_items) > 0:
        feed_items = list(filter(lambda x: x['id'] not in id_diff, feed_items))

    # add diff items to existing feed
    for post_id in id_diff:
        post = request_post(game_id, post_id, lang)
        feed_items.append(create_json_feed_item(post))

    # feed was updated or atom file is missing (possibly due to error)
    if len(id_diff) > 0 or not exists(atom_path):
        # sort feed items desc. so that latest is at the top
        feed_items.sort(key=lambda x: int(x['id']), reverse=True)

        # cut off older entries to limit file size
        limit = 3 * num_entries  # equals one full fetch
        feed_items = feed_items[:limit]

        create_atom_feed_file(game_id, atom_path, atom_url, icon, lang, title, author, feed_items)
        create_json_feed_file(game_id, json_path, json_url, icon, lang, title, author, feed_items)


def create_game_feeds_from_config(path=None, sleep_between=True):
    conf_parser = ConfigParser()
    conf_path = getenv('HOYOLAB_CONFIG_PATH', 'feeds.conf') if path is None else path
    conf_parser.read(conf_path)
    games = conf_parser.sections()

    if len(games) == 0:
        raise RuntimeError('No feeds configured!')

    for game in games:
        conf = conf_parser[game]

        create_game_feeds(
            get_game_id(game),
            conf.get('json_path', 'feed.json'),
            conf.get('atom_path', 'feed.xml'),
            conf.get('json_url', 'feed.json'),
            conf.get('atom_url', 'feed.xml'),
            conf.get('icon', 'https://img-os-static.hoyolab.com/favicon.ico'),
            conf.get('title', 'Untitled'),
            conf.get('author', 'Unknown'),
            int(conf.get('entries', '5')),
            conf.get('language', 'en-US')
        )

        # precaution against rate limits
        if sleep_between and len(games) > 1:
            sleep(1)


if __name__ == '__main__':
    create_game_feeds_from_config()
