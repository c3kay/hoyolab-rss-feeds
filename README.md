# Hoyolab RSS Feeds

![PyPI](https://img.shields.io/pypi/v/hoyolab-rss-feeds)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/hoyolab-rss-feeds)
![Tests Status](https://img.shields.io/github/workflow/status/c3kay/hoyolab-rss-feeds/Main/master)
![Codecov](https://img.shields.io/codecov/c/gh/c3kay/hoyolab-rss-feeds/master)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

This project is an RSS news feed generator for games like *Genshin Impact* or 
*Honkai Impact 3rd* based on the official [Hoyolab](https://www.hoyolab.com) forum 
posts. The current available feed formats are 
[Atom](https://datatracker.ietf.org/doc/html/rfc4287) and 
[JSON Feed](https://jsonfeed.org). This feed generator is supposed to be run
periodically by a cronjob for example.

There are also some feeds already 
[hosted by myself](https://c3kay.de/hoyolab-rss-feeds)!

## Installation

You need at least Python 3.8, and it's package manager Pip installed. You can then 
install this package from PyPI with:

```shell
pip install hoyolab-rss-feeds
```

To get the latest development version, you can install it directly from GitHub:

```shell
pip install git+https://github.com/c3kay/hoyolab-rss-feeds.git@master
```

## Usage

After installation, you can run the application with:

```shell
hoyolab-rss-feeds
```

or as Python module with:

```shell
python -m hoyolabrssfeeds
```

The first time the application is being run, it will create a default TOML configuration
file (`hoyolab-rss-feeds.toml`) in your current working directory and will exit 
afterwards. You can specify a custom path for the config file via a CLI parameter:

```shell
hoyolab-rss-feeds -c path/to/config.toml
```

or equivalent:

```shell
python -m hoyolabrssfeeds -c path/to/config.toml
```

If you want to know how to create feeds programmatically, please check out the
[full documentation](https://hrf-docs.c3kay.de)!

## Configuration

In the TOML config file you can define for which games you want to create a feed
and in which format they should be. A config file might look like this:

```toml
language = "de-de"
category_size = 15

[genshin]
file.json.path = "path/to/genshin.json"
file.json.url = "https://example.org/genshin.json"
title = "Genshin Impact News"
icon = "https://example.org/icon.png"

[honkai]
file.json.path = "path/to/honkai.json"
file.json.url = "https://example.org/honkai.json"
file.atom.path = "path/to/honkai.xml"
file.atom.url = "https://example.org/honkai.xml"
category_size = 5
```

A minimal configuration requires at least one game section, a `category_size` entry 
and a `file.<format>.path` entry. Entries defined at root level are considered as 
default values and these will apply to every game section. The `file` key can only be
used in a game section. All other keys can be used at root level and these can be 
overwritten in a game section.

Available feed formats are `json` and `atom`, but currently only Atom is optional and
there **needs to be a JSON-Feed defined**. This will likely change in the next version,
where a feed might only be generated in Atom format!

The `category_size` entry defines the amount of entries of a Hoyolab news category 
(Info, Event and Notices) for each feed. Therefore, the maximum size of a feed will 
be `3 * category_size`.

Available games are: `genshin`, `honkai`, `themis`, `starrail` and `zenless`.

Available languages are:
- Chinese (CN): `zh-cn`
- Chinese (TW): `zh-tw`
- German: `de-de`
- English: `en-us` *(default)*
- Spanish: `es-es`
- French: `fr-fr`
- Indonesian: `id-id`
- Japanese: `ja-jp`
- Korean: `ko-kr`
- Portuguese: `pt-pt`
- Russian: `ru-ru`
- Thai: `th-th`
- Vietnamese: `vi-vn`

More information about the config file can be found in the 
[full documentation](https://hrf-docs.c3kay.de).