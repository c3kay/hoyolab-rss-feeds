# Genshin Impact Hoyolab RSS Feeds

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/c3kay/hoyolab-rss-feeds/Test%20and%20Deploy)
![JSON Feed](https://img.shields.io/website?down_color=red&down_message=unavailable&label=json%20feed&up_color=green&up_message=available&url=https%3A%2F%2Fc3kay.de%2Fhoyolab.json)
![Atom Feed](https://img.shields.io/website?down_color=red&down_message=unavailable&label=atom%20feed&up_color=green&up_message=available&url=https%3A%2F%2Fc3kay.de%2Fhoyolab.xml)

This script creates a [JSON Feed](https://jsonfeed.org) and an [Atom Feed](https://validator.w3.org/feed/docs/atom.html)
for Genshin Impact's official [Hoyolab](https://www.hoyolab.com) news feed.
The script is intended to be run periodically by e.g. a cronjob.

The feeds are available at `https://c3kay.de/hoyolab.json` and `https://c3kay.de/hoyolab.xml`.
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
