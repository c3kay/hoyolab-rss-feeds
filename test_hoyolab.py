import hoyolab
import atoma
from configparser import ConfigParser
from os.path import exists
from os.path import join
from os import environ


def setup_config(conf_file, json_file, atom_file, game_name):
    conf_parser = ConfigParser()
    conf_parser.add_section(game_name)
    conf_parser.set(game_name, 'json_path', json_file)
    conf_parser.set(game_name, 'atom_path', atom_file)
    conf_parser.set(game_name, 'entries', '1')

    with open(conf_file, 'w') as f:
        conf_parser.write(f)

    environ['HOYOLAB_CONFIG_PATH'] = conf_file


def check_feeds(json_file, atom_file):
    assert exists(json_file)
    assert exists(atom_file)

    json_feed = atoma.parse_json_feed_file(json_file)
    assert len(json_feed.items) == 3

    atom_feed = atoma.parse_atom_file(atom_file)
    assert len(atom_feed.entries) == 3


def test_genshin_en(tmpdir):
    json_file = join(tmpdir, 'genshin.json')
    atom_file = join(tmpdir, 'genshin.xml')

    hoyolab.create_game_feeds(2, json_file, atom_file, json_file, atom_file, 'icon.png', 'Genshin News', 'Paimon', 1)
    check_feeds(json_file, atom_file)


def test_honkai_de(tmpdir):
    json_file = join(tmpdir, 'honkai.json')
    atom_file = join(tmpdir, 'honkai.xml')

    hoyolab.create_game_feeds(1, json_file, atom_file, json_file, atom_file, 'icon.png', 'Honkai News', 'AI-Chan', 1,
                              'de-DE')
    check_feeds(json_file, atom_file)


def test_starrail_config(tmpdir):
    conf_file = join(tmpdir, 'myfeed.conf')
    json_file = join(tmpdir, 'starrail.json')
    atom_file = join(tmpdir, 'starrail.xml')

    setup_config(conf_file, json_file, atom_file, 'starrail')
    hoyolab.main()
    check_feeds(json_file, atom_file)
