# ChangeLog

## v1.0.0 - 19 November 2019

Version 1.0.0! Initial stable release!

* Finished the "hard fork" process, so that our project is now independent of `truffleHog`.
* #13 - Tests are now split into multiple files/classes
* #14 - `tartufo` is now configurable via `pyproject.toml`
* #15 - Code is fully type annotated
* #16 - Fully fleshed out "Community Health" files
* #20 - Code is now fully formatted by `black`

## v0.0.2 - 23 October 2019

Automated Docker builds!

* Docker images are built and pushed automatically to <https://hub.docker.com/r/godaddy/tartufo>
* The version of these images has been synchronized with the Python version via the VERSION file
* Gave the Python package a more verbose long description for PyPi, straight from the README.

## v0.0.1 - 23 October 2019

This is the first public release of `tartufo`, which has been forked off from `truffleHog`.

The primary new features/bugfixes include:

* Renamed everything to `tartufo`
* #1 - Additive whitelist/blacklist support
* #4 - `--pre_commit` support
* #6 - Documented the `--cleanup` switch which cleans up files in `/tmp`
* #10 - Running `tartufo` with no arguments would produce an error
* Added support for <https://pre-commit.com/> style hooks
