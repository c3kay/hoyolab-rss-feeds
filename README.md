# Genshin Impact Hoyolab RSS Feeds

This script creates a [JSON Feed](https://jsonfeed.org) and an [Atom Feed](https://validator.w3.org/feed/docs/atom.html)
from Genshin Impact's official [Hoyolab](https://www.hoyolab.com/) news feed.
The script is intended to be run periodically from e.g. a cronjob.

The feeds are currently available under `https://c3kay.de/hoyolab.json` and `https://c3kay.de/hoyolab.xml`.
They are updated every hour.

### Configuration

If you want to run the script by yourself, the following environment variables need to be defined:
- `HOYOLAB_JSON_PATH` - Target JSON feed file path
- `HOYOLAB_ATOM_PATH` - Target Atom feed file path
- `HOYOLAB_JSON_URL` - Public URL of JSON feed
- `HOYOLAB_ATOM_URL` - Public URL of Atom feed
- `HOYOLAB_ENTRIES` - Number of entries fetched *per* category
- `HOYOLAB_MHYUUID` - Value of cookie `_MHYUUID`(*)

(*) Open hoyolab.com to obtain the cookie
