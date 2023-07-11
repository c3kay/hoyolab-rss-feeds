# Hoyolab RSS Feeds

[![PyPI](https://img.shields.io/pypi/v/hoyolab-rss-feeds)](https://pypi.org/project/hoyolab-rss-feeds/)
[![Python Version](https://img.shields.io/pypi/pyversions/hoyolab-rss-feeds)](https://pypi.org/project/hoyolab-rss-feeds/)
[![Tests Status](https://img.shields.io/github/actions/workflow/status/c3kay/hoyolab-rss-feeds/test.yaml?branch=master)](https://github.com/c3kay/hoyolab-rss-feeds/actions/workflows/test.yaml)
[![Codecov](https://img.shields.io/codecov/c/gh/c3kay/hoyolab-rss-feeds/master)](https://app.codecov.io/gh/c3kay/hoyolab-rss-feeds)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

Generate RSS news feeds for Hoyoverse games like Genshin Impact or Honkai Starrail based
on the official [Hoyolab](https://www.hoyolab.com) forum posts. Available feed formats
are [Atom](https://datatracker.ietf.org/doc/html/rfc4287) and [JSON Feed](https://jsonfeed.org).
This application is supposed to run periodically by a cronjob for example.

There are some [feeds](https://c3kay.de/hoyolab-rss-feeds) already hosted by myself!

## Installation

You need at least Python 3.8 and the package manager Pip installed. You can then
install this package from PyPI with:

```shell
pip install hoyolab-rss-feeds
```

## Usage

### CLI

You can run the application like this:

```shell
hoyolab-rss-feeds
```

or as module:

```shell
python -m hoyolabrssfeeds
```

If no configuration can be found, the application will create a default config
in your current directory (`./hoyolab-rss-feeds.toml`) and will exit afterwards.

You can specify a path for the config file with a parameter:

```shell
hoyolab-rss-feeds -c path/to/config.toml
```

### Module

It is also possible to generate the feeds via code:

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

[Here](https://gist.github.com/c3kay/2cd9833ef1c527e210aebf7a866336ed)
you can find an example on how to create a feed without using the TOML config file.

## Configuration

In the TOML config file you can define for which games you want to create a feed
and in which format the feeds should be. Here is an example config:

```toml
language = "de-de"
category_size = 15

[genshin]
feed.json.path = "path/to/genshin.json"
feed.json.url = "https://example.org/genshin.json"
category_size = 5
categories = ["Info", "Notices"]
title = "Genshin Impact News"
icon = "https://example.org/icon.png"

[starrail]
feed.json.path = "path/to/starrail.json"
feed.json.url = "https://example.org/starrail.json"
feed.atom.path = "path/to/starrail.xml"
feed.atom.url = "https://example.org/starrail.xml"
```

A minimal configuration requires at least one game section with a `feed.<format>.path`
entry. Available feed formats are currently `json` and `atom`. You can either use
one format or both.

Entries defined at root level are considered default values and will apply to every
game section. The `feed` key can only be used in a game section. All other keys
can be defined at root level and they can be overwritten by a game section.

The `category_size` entry defines the amount of feed items (default: 5) of a Hoyolab
category (*Info*, *Event* and *Notices*) for each feed. The `category` list entry 
defines the categories selected for this feed. If this entry is omitted, all 
categories are selected.

**Note:** When using Windows file paths (like `C:\\path\to\config.toml`), single quotes
should be used to avoid wrong auto-escaping of backslashes. More info about the TOML 
format can be found in the [official documentation](https://toml.io/en/).

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
