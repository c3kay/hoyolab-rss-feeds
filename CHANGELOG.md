## Changelog

- Added Testing for Windows
- Fixed Windows specific bugs
- Now disallowing identical feed paths in config (*)

_(*) It was possible that different feeds could use the same file (e.g. feed.json) which
produced unwanted behavior because the feeds are created concurrently and non-threadsafe._
