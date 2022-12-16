# Contribution Guidelines

Thanks for your interest in contributing to this project! This brief guide shows
you the basics to get started.

## Issues

If you have encountered a bug, please check at first if it has been 
[already reported](https://github.com/c3kay/hoyolab-rss-feeds/issues) or is currently
being worked on! If the bug is new, please open an issue and describe the problem 
as detailed as possible. Console output, the config file or the feed files can also be 
very helpful for debugging. So please attach them if needed!

You can use the discussion page to ask questions about the project, but please also 
check if they have already been answered before!

## Developing

### Getting Started

After cloning this repo, you need to install the dev-dependencies and an 
["editable install"](https://pip.pypa.io/en/latest/topics/local-project-installs/)
of the package:

```shell
pip install -e ".[dev]"
```

### Testing

Please make sure that every code you add has at least some basic unittests! You can 
run the test suite simply with `tox` or `python -m tox`. If you just want to quickly 
check the core tests for a single python version, you can run:

```shell
tox -e py38 -- -m "not hoyolabapi"
```

This will only run the Python 3.8 environment and will instruct pytest to exclude the
Hoyolab API tests (which are kind of slow due to the amount of requests being made).

### Tools

To ensure a common code style, the 
[black format](https://black.readthedocs.io/en/stable/) is used for this project. For
basic code linting `flake8` is used. The codebase is also type checked with `mypy`.
You can run these tools via tox:

```shell
tox -e flake,black,type
```

## Pull Requests

Before submitting, make sure your code is...

- in the black format
- type checked (with mypy)
- documented (docstrings and comments are sufficient)
- well tested
- in a dedicated branch

If all checks pass, your code can be merged after a review! :)
