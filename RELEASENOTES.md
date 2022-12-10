## New Features

- Added Italian and Turkish.
- An error is now raised if the config contains unknown entries. This should prevent typos
in config entries.

## Bug Fixes

- Added empty paragraph filtering at beginning of content again (same behaviour as in 1.4.3).
- Fixed a bug in JSON feed writer: `date_updated` instead of `date_modified`. This caused 
feeds, or more precisely articles, to be updated and re-fetched even if they were up-to-date.
