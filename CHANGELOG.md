v2.0.0a1 - 18 November 2020
---------------------------

This is a whole brand new tartufo! It's been entirely restructured, rewritten,
retested, rebuilt, and remade! It's now more extensible, readable, testable,
and usable.

New features include:

* #2 - Verified/approved exclusions are now handled by way of hash signatures.
  * These hashes are created on a combination of the matched string and filename
    where the match was found. They are generated using the `BLAKE2` hashing
    algorithm. (via #61)
* #7 - A working directory can now be specified to clone to when scanning a
  remote repository. (via #81)
* #11 - Removed the `--cleanup` option and added a `--output-dir` in its place.
  Issues are now written to disk only when specifically requested by providing
  an output directory. (via #82)
* #39 - The functionality is now split into sub-commands (via #78) Available
  sub-commands are, for now:
  * pre-commit
  * scan-local-repo
  * scan-remote-repo
* The entire library has been refactored and nearly all logic has been put
  into its most appropriate place. It should now be possible to use this whole
  tool as a library, and not just a CLI application. (via #29, #65, #67, #70)

Bug fixes include:

* #55 - The tests no longer iterate over this repository's history; everything
  has been sufficiently split out to make it more testable without needing to
  look at an actual git history. (via #70)
* #72 - Specifying a non-git path no longer causes an error (via #80)

Other changes:

* Issues found during the scan are now represented by a class, instead of some
  amorphous dictionary (via #29)
  * Further, since a single `Issue` is instantiated per match, the output key
    for the matches has changed from `strings_found` to `matched_string`.
* #25 - Set up full documentation on Read The Docs (via #38)
* #30 - Support for Python 2 has been dropped (via #31)
* #58 - CI is now handled by GitHub Actions (via #59)

v1.1.2 - 21 April 2020
----------------------

* #48 (Backport of #45 & #46)
  * Documented Docker usage
  * Small fixes to Docker to allow SSH clones and avoid scanning tartufo itself
* Docs have been backported from the `master` branch.

v1.1.1 - 13 December 2019
-------------------------

* Fix the docs and pre-commit hook to use hyphens in CLI arguments, as opposed
  to underscores.

v1.1.0 - 27 November 2019
-------------------------

* Support reading config from `tartufo.toml` for non-Python projects
* #17 - A separate repository can be used for storing rules files
* #18 - Read the `pyproject.toml` or `tartufo.toml` from the repo being scanned

v1.0.2 - 19 November 2019
-------------------------

This release is essentially the same as the v1.0.0 release, but with a new number.
Unfortunately, we had historical releases versioned as v1.0.0 and v1.0.1. Due to
limitations in PyPI (https://pypi.org/help/#file-name-reuse), even if a previous
release has been deleted, the version number may not be reused.

v1.0.0 - 19 November 2019
-------------------------

Version 1.0.0! Initial stable release!

* Finished the "hard fork" process, so that our project is now independent of `truffleHog`.
* #13 - Tests are now split into multiple files/classes
* #14 - `tartufo` is now configurable via `pyproject.toml`
* #15 - Code is fully type annotated
* #16 - Fully fleshed out "Community Health" files
* #20 - Code is now fully formatted by `black`

v0.0.2 - 23 October 2019
------------------------

Automated Docker builds!

* Docker images are built and pushed automatically to https://hub.docker.com/r/godaddy/tartufo
* The version of these images has been synchronized with the Python version via the VERSION file
* Gave the Python package a more verbose long description for PyPi, straight from the README.

v0.0.1 - 23 October 2019
------------------------

This is the first public release of `tartufo`, which has been forked off from `truffleHog`.

The primary new features/bugfixes include:

* Renamed everything to `tartufo`
* #1 - Additive whitelist/blacklist support
* #4 - `--pre_commit` support
* #6 - Documented the `--cleanup` switch which cleans up files in `/tmp`
* #10 - Running `tartufo` with no arguments would produce an error
* Added support for https://pre-commit.com/ style hooks
