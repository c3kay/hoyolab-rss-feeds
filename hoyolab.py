import requests
import json
from os import environ
from os.path import exists
from datetime import datetime
from xml.dom import minidom


# -- REQUESTS -- #

def request_news(category, num_entries):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.hoyolab.com'
    }

    params = {
        'gids': 2,
        'page_size': num_entries,
        'type': category
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'
    res = requests.get(url, headers=headers, params=params)

    try:
        res.raise_for_status()
        j = res.json()

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


def request_post(post_id):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.hoyolab.com'
    }

    params = {
        'gids': 2,
        'post_id': post_id,
        'read': 1
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull'
    res = requests.get(url, headers=headers, params=params)

    try:
        res.raise_for_status()
        j = res.json()

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

def create_json_feed_file(path, feed_url, items):
    feed = {
        'version': 'https://jsonfeed.org/version/1.1',
        'title': 'Genshin Impact News',
        'home_page_url': 'https://www.hoyolab.com/',
        'feed_url': feed_url,
        'icon': 'https://img-os-static.mihoyo.com/avatar/avatar10011.png',
        'language': 'en',
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

    item = {
        'id': post_id,
        'url': 'https://www.hoyolab.com/article/{}'.format(post_id),
        'title': post['post']['subject'],
        'content_html': post['post']['content'],
        'date_published': ct
    }

    if post['last_modify_time'] > 0:
        mt = datetime.fromtimestamp(post['last_modify_time']).astimezone().isoformat()
        item['date_modified'] = mt

    return item


# -- ATOM FEED -- #

def create_atom_feed_file(path, feed_url, items):
    doc = minidom.getDOMImplementation().createDocument(None, 'feed', None)
    root = doc.documentElement

    # workaround...
    root.setAttribute('xmlns', 'http://www.w3.org/2005/Atom')
    root.setAttribute('xml:lang', 'en')

    append_text_node(doc, root, 'id', 'tag:hoyolab.com,2021:/official/2')
    append_text_node(doc, root, 'title', 'Genshin Impact News')
    append_text_node(doc, root, 'updated', datetime.now().astimezone().isoformat())
    append_attr_node(doc, root, 'link', {'href': 'https://www.hoyolab.com/', 'rel': 'alternate', 'type': 'text/html'})
    append_attr_node(doc, root, 'link', {'href': feed_url, 'rel': 'self', 'type': 'application/atom+xml'})
    append_text_node(doc, root, 'icon', 'https://img-os-static.mihoyo.com/avatar/avatar10011.png')

    author = doc.createElement('author')
    append_text_node(doc, author, 'name', 'Paimon')
    root.appendChild(author)

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


def get_latest_post_ids(num_entries):
    all_posts = []

    # collect posts from all 3 news categories
    for cat in range(1, 4):
        cat_news = request_news(cat, num_entries)
        all_posts.extend(cat_news)

    # dict of ids with latest modification timestamp
    return {p['post']['post_id']: max(p['last_modify_time'], p['post']['created_at']) for p in all_posts}


def get_post_id_diff(fetched_ids, known_ids):
    new_ids = []

    for post_id, modified in fetched_ids.items():
        if post_id not in known_ids or (post_id in known_ids and modified > known_ids[post_id]):
            new_ids.append(post_id)

    return new_ids


def main():
    try:
        json_feed_path = environ['HOYOLAB_JSON_PATH']
        atom_feed_path = environ['HOYOLAB_ATOM_PATH']
        json_feed_url = environ['HOYOLAB_JSON_URL']
        atom_feed_url = environ['HOYOLAB_ATOM_URL']
        num_entries = int(environ['HOYOLAB_ENTRIES'])
    except KeyError as err:
        raise RuntimeError('Error at loading feed environment variables!') from err

    # json feed as reference for known items since it is easier to parse...
    feed_items = load_json_feed_items(json_feed_path)

    known_ids = get_known_post_ids(feed_items)
    fetched_ids = get_latest_post_ids(num_entries)
    id_diff = get_post_id_diff(fetched_ids, known_ids)

    # remove modified items from feed item list (if exists)
    if len(id_diff) > 0 and len(feed_items) > 0:
        feed_items = list(filter(lambda x: x['id'] not in id_diff, feed_items))

    # add diff items to existing feed
    for post_id in id_diff:
        post = request_post(post_id)
        feed_items.append(create_json_feed_item(post))

    # feed was updated or atom file is missing (possibly due to error)
    if len(id_diff) > 0 or not exists(atom_feed_path):
        # sort feed items desc. so that latest is at the top
        feed_items.sort(key=lambda x: int(x['id']), reverse=True)

        # cut off older entries to limit file size
        limit = 3 * num_entries  # equals one full fetch
        feed_items = feed_items[:limit]

        create_atom_feed_file(atom_feed_path, atom_feed_url, feed_items)
        create_json_feed_file(json_feed_path, json_feed_url, feed_items)


if __name__ == '__main__':
    main()
