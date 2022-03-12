from hoyolab import create_game_feeds
from os.path import exists
import atoma


def check_feeds(json_file, atom_file):
    assert exists(json_file)
    assert exists(atom_file)

    json_feed = atoma.parse_json_feed_file(json_file)

    assert len(json_feed.items) == 3

    atom_feed = atoma.parse_atom_file(atom_file)

    assert len(atom_feed.entries) == 3


def test_genshin_en(tmpdir):
    json_file = '{}/genshin.json'.format(tmpdir)
    atom_file = '{}/genshin.xml'.format(tmpdir)

    create_game_feeds(2, json_file, atom_file, json_file, atom_file, 'icon.png', 'Genshin News', 'Paimon', 1)

    check_feeds(json_file, atom_file)


def test_honkai_de(tmpdir):
    json_file = '{}/honkai.json'.format(tmpdir)
    atom_file = '{}/honkai.xml'.format(tmpdir)

    create_game_feeds(1, json_file, atom_file, json_file, atom_file, 'icon.png', 'Honkai News', 'AI-Chan', 1, 'de-DE')

    check_feeds(json_file, atom_file)
