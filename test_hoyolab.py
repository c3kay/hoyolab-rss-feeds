from hoyolab import main
from os import environ
from os.path import exists
import atoma


def init_environ(d):
    environ['HOYOLAB_JSON_PATH'] = '{}/hoyolab.json'.format(d)
    environ['HOYOLAB_ATOM_PATH'] = '{}/hoyolab.xml'.format(d)
    environ['HOYOLAB_JSON_URL'] = 'hoyolab.json'
    environ['HOYOLAB_ATOM_URL'] = 'hoyolab.xml'
    environ['HOYOLAB_ENTRIES'] = '1'


def test_feeds(tmpdir):
    init_environ(tmpdir)

    json_path = environ['HOYOLAB_JSON_PATH']
    atom_path = environ['HOYOLAB_ATOM_PATH']
    num_entries = int(environ['HOYOLAB_ENTRIES']) * 3

    main()

    assert exists(json_path)
    assert exists(atom_path)

    json_feed = atoma.parse_json_feed_file(json_path)

    assert len(json_feed.items) == num_entries

    atom_feed = atoma.parse_atom_file(atom_path)

    assert len(atom_feed.entries) == num_entries
