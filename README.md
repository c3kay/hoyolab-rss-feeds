# Hoyolab RSS Feeds

![Test Status](https://github.com/c3kay/hoyolab-rss-feeds/actions/workflows/test.yaml/badge.svg)
![Deploy Status](https://github.com/c3kay/hoyolab-rss-feeds/actions/workflows/deploy.yaml/badge.svg)

This script creates [JSON Feeds](https://jsonfeed.org) and [Atom Feeds](https://datatracker.ietf.org/doc/html/rfc4287)
for Hoyoverse games like [Genshin Impact](https://genshin.hoyoverse.com/en/home) or 
[Honkai Impact 3rd](https://honkaiimpact3.hoyoverse.com/global/en-us/home) based on the official 
[Hoyolab](https://www.hoyolab.com) news. The script is intended to be run periodically by e.g. a cronjob.

Some feeds are already [hosted by myself](https://c3kay.de/hoyolab-rss-feeds), which are updated hourly.

### Configuration

To run the script, you need to do some configuration via a config file.
You can set a custom path to the config file via the environment variable `HOYOLAB_CONFIG_PATH`. 
The default path is `./feeds.conf`.

A JSON and Atom feed is created for each configured section/game. Check the `example.conf` file for further details.
More information about the config file format can be found [here](https://en.wikipedia.org/wiki/INI_file).

<sub>*Disclaimer: The content of the generated feeds is the property of Cognosphere PTE., LTD. and their respective owners.*</sub>
