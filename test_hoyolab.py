import hoyolab
import atoma
import json
from configparser import ConfigParser
from os import environ
from os.path import exists
from os.path import join
from datetime import datetime
from datetime import timedelta


def setup_config(conf_file, json_file, atom_file, game_name, entries):
    conf_parser = ConfigParser()
    conf_parser.add_section(game_name)
    conf_parser.set(game_name, 'json_path', json_file)
    conf_parser.set(game_name, 'atom_path', atom_file)
    conf_parser.set(game_name, 'entries', str(entries))

    with open(conf_file, 'w') as f:
        conf_parser.write(f)

    environ['HOYOLAB_CONFIG_PATH'] = conf_file


def simulate_feed_changes(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        feed = json.load(f)

    items = feed['items']

    # remove item to simulate new article
    items.pop()

    # change timestamp to simulate update
    pt0 = datetime.fromisoformat(items[0]['date_published'])
    pt = pt0 - timedelta(hours=4)
    mt = pt0 - timedelta(hours=2)
    items[0]['date_published'] = pt.astimezone().isoformat()
    items[0]['date_modified'] = mt.astimezone().isoformat()

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(feed, f)


def check_feeds(json_file, atom_file, total_entries):
    assert exists(json_file)
    assert exists(atom_file)

    json_feed = atoma.parse_json_feed_file(json_file)
    assert len(json_feed.items) == total_entries

    atom_feed = atoma.parse_atom_file(atom_file)
    assert len(atom_feed.entries) == total_entries


def test_genshin_en(tmpdir):
    json_file = join(tmpdir, 'genshin.json')
    atom_file = join(tmpdir, 'genshin.xml')

    hoyolab.create_game_feeds(2, json_file, atom_file, json_file, atom_file, 'icon.png', 'Genshin News', 'Paimon', 1)
    check_feeds(json_file, atom_file, 3)


def test_honkai_de(tmpdir):
    json_file = join(tmpdir, 'honkai.json')
    atom_file = join(tmpdir, 'honkai.xml')

    hoyolab.create_game_feeds(1, json_file, atom_file, json_file, atom_file, 'icon.png', 'Honkai News', 'AI-Chan', 1,
                              'de-DE')
    check_feeds(json_file, atom_file, 3)


def test_themis_update(tmpdir):
    json_file = join(tmpdir, 'themis.json')
    atom_file = join(tmpdir, 'themis.xml')

    hoyolab.create_game_feeds(4, json_file, atom_file, json_file, atom_file, 'icon.png', 'Themis News', '-', 1)
    check_feeds(json_file, atom_file, 3)
    simulate_feed_changes(json_file)
    hoyolab.create_game_feeds(4, json_file, atom_file, json_file, atom_file, 'icon.png', 'Themis News', '-', 1)
    check_feeds(json_file, atom_file, 3)


def test_starrail_config(tmpdir):
    conf_file = join(tmpdir, 'myfeed.conf')
    json_file = join(tmpdir, 'starrail.json')
    atom_file = join(tmpdir, 'starrail.xml')

    setup_config(conf_file, json_file, atom_file, 'starrail', 1)
    hoyolab.main()
    check_feeds(json_file, atom_file, 3)
