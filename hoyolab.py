import requests
import json
from os import environ
from datetime import datetime
from collections import deque


def request_news(category, num_entries, mhyuuid):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US',
        'Origin': 'https://www.hoyolab.com',
        'Referer': 'https://www.hoyolab.com/genshin/home/3',
        'x-rpc-language': 'en-us'
    }

    params = {
        'gids': 2,
        'page_size': num_entries,
        'type': category
    }

    cookies = {
        'mi18nLang': 'en-us',
        '_MHYUUID': mhyuuid
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getNewsList'
    res = requests.get(url, headers=headers, params=params, cookies=cookies)

    try:
        j = res.json()
        return j['data']['list'] if j['retcode'] == 0 else None
    except KeyError:
        print('[request_news] Unexpected response!')
        return None
    except json.JSONDecodeError:
        print('[request_news] Error parsing json!')
        return None


def request_post(post_id, mhyuuid):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US',
        'Origin': 'https://www.hoyolab.com',
        'x-rpc-language': 'en-us'
    }

    params = {
        'gids': 2,
        'post_id': post_id,
        'read': 1
    }

    cookies = {
        'mi18nLang': 'en-us',
        '_MHYUUID': mhyuuid
    }

    url = 'https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull'
    res = requests.get(url, headers=headers, params=params, cookies=cookies)

    try:
        j = res.json()
        return j['data']['post'] if j['retcode'] == 0 else None
    except KeyError:
        print('[request_post] Unexpected response!')
        return None
    except json.JSONDecodeError:
        print('[request_post] Error parsing json!')
        return None


def create_feed_item(post):
    ct = datetime.fromtimestamp(post['post']['created_at']).astimezone().isoformat()
    post_id = post['post']['post_id']

    item = {
        'id': post_id,
        'url': 'https://www.hoyolab.com/genshin/article/{}'.format(post_id),
        'title': post['post']['subject'],
        'content_html': post['post']['content'],
        'date_published': ct
    }

    if post['last_modify_time'] > 0:
        mt = datetime.fromtimestamp(post['last_modify_time']).astimezone().isoformat()
        item['date_modified'] = mt

    return item


def create_feed_file(path, url, icon, items):
    feed = {
        'version': 'https://jsonfeed.org/version/1.1',
        'title': 'Hoyolab News',
        'home_page_url': 'https://www.hoyolab.com/genshin/home/3',
        'feed_url': url,
        'icon': icon,
        'language': 'en',
        'items': items
    }

    try:
        with open(path, 'w') as fd:
            json.dump(feed, fd)
    except IOError:
        print('[create_feed_file] Could not write json file to {}!'.format(path))


def load_feed_items(path, num_entries):
    try:
        with open(path, 'r') as fd:
            feed = json.load(fd)
        # limit returned feed items
        return feed['items'][:num_entries*3*5]
    except IOError:
        # file not found -> create new feed list
        return []


def collect_known_ids(feed_items):
    known_ids = {}

    for item in feed_items:
        modified_ts = 0
        if 'date_modified' in item:
            modified_ts = datetime.fromisoformat(item['date_modified']).timestamp()

        known_ids[item['id']] = modified_ts

    return known_ids


def main():
    try:
        feed_path = environ['HOYOLAB_FEED_PATH']
        feed_url = environ['HOYOLAB_FEED_URL']
        feed_icon = environ['HOYOLAB_FEED_ICON']
        mhyuuid = environ['HOYOLAB_MHYUUID']
    except KeyError:
        print('Error at loading environment variables!')
        return

    num_entries = 5

    feed_items = load_feed_items(feed_path, num_entries)
    known_ids = collect_known_ids(feed_items)

    # create list of all news items from all 3 categories
    all_posts = []
    for cat in range(1, 4):
        cat_news = request_news(cat, num_entries, mhyuuid)

        if cat_news is None:
            return

        all_posts.extend(cat_news)


    fetched_ids = {p['post']['post_id']: p['last_modify_time'] for p in all_posts}

    # get posts which need to be fetched or updated
    new_ids = []
    for post_id, modified in fetched_ids.items():
        if post_id not in known_ids or (post_id in known_ids and modified > known_ids[post_id]):
            new_ids.append(post_id)

    # remove modified items and create feed as deque
    if len(new_ids) > 0:
        feed_items = deque(filter(lambda x: x['id'] not in new_ids, feed_items))

    # prepend items to existing feed
    for post_id in new_ids:
        post = request_post(post_id, mhyuuid)

        if post is None:
            return

        new_item = create_feed_item(post)
        feed_items.appendleft(new_item)

    create_feed_file(feed_path, feed_url, feed_icon, list(feed_items))


if __name__ == '__main__':
    main()
