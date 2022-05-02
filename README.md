# Hoyolab RSS Feeds

![Build Status](https://img.shields.io/github/workflow/status/c3kay/hoyolab-rss-feeds/Main?style=flat)
![Deploy Status](https://img.shields.io/github/deployments/c3kay/hoyolab-rss-feeds/c3kay-server?label=deploy)
![Codecov](https://img.shields.io/codecov/c/gh/c3kay/hoyolab-rss-feeds/master?style=flat)

This script creates [JSON Feeds](https://jsonfeed.org) and [Atom Feeds](https://datatracker.ietf.org/doc/html/rfc4287)
for Hoyoverse games like [Genshin Impact](https://genshin.hoyoverse.com/en/home) or
[Honkai Impact 3rd](https://honkaiimpact3.hoyoverse.com/global/en-us/home) based on the official
[Hoyolab](https://www.hoyolab.com) news. The script is intended to be run periodically by e.g. a cronjob.

Some feeds are already [hosted by myself](https://c3kay.de/hoyolab-rss-feeds), which are updated hourly.

### Installation

You can download the latest distribution zip-archive on the
[release page](https://github.com/c3kay/hoyolab-rss-feeds/releases) of this repository. This archive contains
the script, the requirements file and the example config.

After downloading, you could create a virtual environment and activate it with:

```sh
$ python3 -m venv venv
$ source venv/bin/active
```

Install the dependencies with:

```sh
$ pip3 install -r requirements.txt
```

### Usage

To run the script, you need to do some configuration via the config file.
You can set a custom path to the config file with the environment variable `HOYOLAB_CONFIG_PATH`.
The default path is `./feeds.conf`.

A JSON and Atom feed is created for each configured section/game.
Check the `example.conf` file for further details.

A sample cronjob could look like this:

```
HOYOLAB_CONFIG_PATH="/path/to/feeds.conf"
0 * * * * /path/to/venv/python3 /path/to/hoyolab.py
```


<sub>*Disclaimer: The content of the generated feeds is the property of Cognosphere PTE., LTD. and their respective owners.*</sub>
