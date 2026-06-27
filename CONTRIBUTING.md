# Contribution Guidelines

Thanks for your interest in contributing to this project! This brief guide shows
you the basics to get started.

## Issues

If you have encountered a bug, please check at first if it has been 
[already reported](https://github.com/c3kay/hoyolab-rss-feeds/issues) or is currently
being worked on! If the bug is new, please open an issue and describe the problem 
as detailed as possible. Console output, the config file or the feed files can also be 
very helpful for debugging. So please attach them if needed!

## Developing

### Getting Started

After cloning this repo, you need to install the dev-dependencies:

```shell
uv sync
```

... or via pip:

```shell
python3 -m pip install --group dev -e .
```

### Testing

Please make sure that every code you add has at least some basic unittests! You can 
run the test suite simply with `tox` or `python3 -m tox`. If you just want to quickly 
check the core tests for a single python version, you can run:

```shell
tox r -e py313 -- -m not hoyolabapi
```

This will only run the Python 3.13 environment and will instruct `pytest` to exclude the
Hoyolab API tests (which are slow due to the amount of requests being tested).

### Tools

To ensure a common code style and basic code linting
the tool `ruff` is used. The codebase is also type checked with `mypy`.
You can run these tools via tox:

```shell
tox r -e lint,type
```

Format code with:

```shell
tox r -e lint -- format
```

... or directly with `ruff`:

```shell
ruff format
```

## Pull Requests

Before submitting, make sure your code is...

- formated with `ruff`
- type checked with `mypy`
- documented (docstrings and comments are sufficient)
- well tested
- in a dedicated branch

If all checks pass, your code can be merged after a review! :)
