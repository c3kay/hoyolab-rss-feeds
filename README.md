# Hoyolab RSS Feeds

![Workflow Status](https://github.com/c3kay/hoyolab-rss-feeds/actions/workflows/action.yaml/badge.svg)

This script creates [JSON Feeds](https://jsonfeed.org) and [Atom Feeds](https://datatracker.ietf.org/doc/html/rfc4287)
for Hoyoverse games like Genshin Impact or Honkai Impact 3rd based on the official [Hoyolab](https://www.hoyolab.com) news.
The script is intended to be run periodically by e.g. a cronjob.

Some feeds are already hosted by myself. You can find more information about them [here](https://c3kay.de/hoyolab-rss-feeds).

### Configuration

To run the script, you need to do some configuration, which is done via the `feeds.conf` file.
A JSON and Atom feed is created for each configured section/game. Check the example file for further details.
More information about the config file format can be found [here](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure).

<sub>*Disclaimer: The content of the generated feeds is the property of Cognosphere PTE., LTD. and their respective owners.*</sub>
