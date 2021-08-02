# Hoyolab Json Feed

This script creates a [JSON Feed](https://jsonfeed.org) file from
Genshin Impact's official [Hoyolab](https://www.hoyolab.com/genshin/home/3) news feed.
The script is intended to be run periodically from e.g. a cronjob.

The feed is currently available under `https://c3kay.de/hoyolab.json` and is refreshed every hour.

### Configuration

If you want to run the script by yourself, the following environment variables need to be defined:
- `HOYOLAB_FEED_PATH` - Target json file path
- `HOYOLAB_FEED_URL` - URL under which the feed will be available
- `HOYOLAB_FEED_ICON` - URL for a feed image file
- `HOYOLAB_MHYUUID` - Value of cookie `_MHYUUID`*

(*) Open hoyolab.com to obtain the cookie
