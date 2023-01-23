# Hoyolab RSS Feeds

[![PyPI](https://img.shields.io/pypi/v/hoyolab-rss-feeds)](https://pypi.org/project/hoyolab-rss-feeds/)
[![Python Version](https://img.shields.io/pypi/pyversions/hoyolab-rss-feeds)](https://pypi.org/project/hoyolab-rss-feeds/)
[![Tests Status](https://img.shields.io/github/actions/workflow/status/c3kay/hoyolab-rss-feeds/test.yaml?branch=master)](https://github.com/c3kay/hoyolab-rss-feeds/actions/workflows/test.yaml)
[![Codecov](https://img.shields.io/codecov/c/gh/c3kay/hoyolab-rss-feeds/master)](https://app.codecov.io/gh/c3kay/hoyolab-rss-feeds)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

Generate RSS news feeds for games like *Genshin Impact* or *Honkai Impact 3rd* based 
on the official [Hoyolab](https://www.hoyolab.com) forum posts. The current available 
feed formats are [Atom](https://datatracker.ietf.org/doc/html/rfc4287) and 
[JSON Feed](https://jsonfeed.org). This feed generator is supposed to be run
periodically by e.g. a cronjob.

There are [some feeds](https://c3kay.de/hoyolab-rss-feeds) already hosted by myself!

## Installation

You need at least Python 3.8 and the package manager Pip installed. You can then 
install this package from PyPI with:

```shell
pip install hoyolab-rss-feeds
```

To get the latest development version, you can also install it directly from GitHub:

```shell
pip install git+https://github.com/c3kay/hoyolab-rss-feeds.git@master
```

## Usage

### CLI

You can run the application with:

```shell
hoyolab-rss-feeds
```

or via Python with:

```shell
python -m hoyolabrssfeeds
```

The first time, when the application is started, it will create a default TOML config
file in your current working directory (`./hoyolab-rss-feeds.toml`) and will exit 
afterwards. You can specify a custom path for the config file via a parameter:

```shell
hoyolab-rss-feeds -c path/to/config.toml
```

or equivalent:

```shell
python -m hoyolabrssfeeds -c path/to/config.toml
```

### Library

It is also possible to generate the feeds directly from your Python application:

```python
from hoyolabrssfeeds import FeedConfigLoader, GameFeed, GameFeedCollection, Game

async def generate_feeds():
    loader = FeedConfigLoader("path/to/config.toml")
    
    # all games in config
    all_configs = await loader.get_all_feed_configs()
    feed_collection = GameFeedCollection.from_configs(all_configs)
    await feed_collection.create_feeds()
    
    # only a single game
    genshin_config = await loader.get_feed_config(Game.GENSHIN)
    genshin_feed = GameFeed.from_config(genshin_config)
    await genshin_feed.create_feed()
```

## Configuration

In the TOML config file you can define for which games you want to create a feed
and in which format they should be. A config file might look like this:

```toml
language = "de-de"
category_size = 15

[genshin]
feed.json.path = "path/to/genshin.json"
feed.json.url = "https://example.org/genshin.json"
title = "Genshin Impact News"
icon = "https://example.org/icon.png"

[honkai]
feed.json.path = "path/to/honkai.json"
feed.json.url = "https://example.org/honkai.json"
feed.atom.path = "path/to/honkai.xml"
feed.atom.url = "https://example.org/honkai.xml"
category_size = 5
```

A minimal configuration requires at least one game section with a `feed.<format>.path` 
entry. Available feed formats are currently `json` and `atom`. You can either use 
only one format or both.

Entries defined at root level are considered default values and will apply to every 
game section. The `feed` key can only be used in a game section. All other keys 
can be defined at root level and can be overwritten by a game section.

The `category_size` entry defines the amount of feed items (default: 5) of a Hoyolab news 
category (Info, Event and Notices) for each feed. Therefore, the maximum size of a 
feed will be `3 * category_size`.

**Note:** When using Windows file paths (like `C:\\path\to\config.toml`), you should
use single quotes (`'`) to avoid a misinterpretation of the backslashes by the TOML 
parser. More info about the TOML format can be found in the 
[official documentation](https://toml.io/en/).

### Options

#### Games

| Game              | Section    |
|-------------------|------------|
| Genshin Impact    | `genshin`  |
| Honkai Impact 3rd | `honkai`   |
| Tears of Themis   | `themis`   |
| Honkai: Starrail  | `starrail` |
| Zenless Zone Zero | `zenless`  |

#### Languages

*English is the default language.*

| Language     | Code    |
|--------------|---------|
| German       | `de-de` |
| English      | `en-us` |
| Spanish      | `es-es` |
| French       | `fr-fr` |
| Indonesian   | `id-id` |
| Italian      | `it-it` |
| Japanese     | `ja-jp` |
| Korean       | `ko-kr` |
| Portuguese   | `pt-pt` |
| Russian      | `ru-ru` |
| Thai         | `th-th` |
| Turkish      | `tr-tr` |
| Vietnamese   | `vi-vn` |
| Chinese (CN) | `zh-cn` |
| Chinese (TW) | `zh-tw` |
