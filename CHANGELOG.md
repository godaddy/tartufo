v2.8.1 - 11 October 2021
------------------------

Bug fixes:

* [#222](https://github.com/godaddy/tartufo/pull/222) - Allow
  exclude-entropy-patterns to match lines containing partial matches -- thanks
  to @kbartholomew-godaddy for the work on this one!

v2.8.0 - 14 September 2021
--------------------------

Features:

* [#83](https://github.com/godaddy/tartufo/issues/83) - New `scan-folder` command
  to scan files without viewing as a git repository.

Bug fixes:

* [#220](https://github.com/godaddy/tartufo/pull/220) - Display an explicit error
  message when a requested branch is not found, as opposed to failing silently.

Misc:

* [#219](https://github.com/godaddy/tartufo/pull/219) - Incremental optimizations;
  using `__slots__` for the `Issue` class to improve memory consumption, and
  a small logic speed-up in when we generate the diff between commits. Both of
  these should help at least some when it comes to scanning very large
  repositories.

v2.7.1 - 23 August 2021
-----------------------

Bug fixes:

* [#211](https://github.com/godaddy/tartufo/issues/211) - Attempt to fix a case
  where output encoding could be set to cp1252 on Windows, which would cause a
  crash if unicode characters were printed. Now issues are output as utf-8
  encoded bytestreams instead.

v2.7.0 - 10 August 2021
-----------------------

Features:

* [#96](https://github.com/godaddy/tartufo/issues/96) - Explicitly handle
  submodules. Basically, always ignore them by default. There is also a new
  option to toggle this functionality: `--include-submodules`
* Add `exclude_entropy_patterns` to output

v2.6.0 - 30 June 2021
---------------------

Features:

* [#194](https://github.com/godaddy/tartufo/issues/194) - Half bugfix, half
  feature. Now when an excluded signature in your config file is found as an
  entropy match, tartufo will realize that and no longer report it as an issue.
* [#5](https://github.com/godaddy/tartufo/issues/5) - Remove the dependency on
  `truffleHogRegexes`. This enables us to take full control of the default set
  of regex checks.

Bug fixes:

* [#179](https://github.com/godaddy/tartufo/issues/179) - Iterate over commits
  in topological order, instead of date order.

v2.5.0 - 15 June 2021
---------------------

Features:

* [#145](https://github.com/godaddy/tartufo/issues/145) - Adds
  `--exclude-path-patterns` and `--include-path-patterns` to simplify config in
  a single .toml file
* [#87](https://github.com/godaddy/tartufo/issues/87) - Adds
  `--exclude-entropy-patterns` to allow for regex-based exclusions

Bug fixes:

* Write debug log entries when binary files are encountered
* Pinned all linting tools to specific versions and set all tox envs to use poetry
* Disabled codecov due to security breach

v2.4.0 - 05 March 2021
----------------------

Features:

* #76 - Added logging! You can now use the `-v`/`--verbose` option to increase
  the amount of output from tartufo. Specifying multiple times will incrementally
  increase what is output.
* Added a `--log-timestamps`/`--no-log-timestamps` option (default: True) so that
  timestamps can be hidden in log messages. This could be helpful when, for example,
  comparing the output from multiple runs.
* #107 - Added a `--compact`/`--no-compact` option for abbreviated output on found
  issues, to avoid unintentionally spamming yourself. (Thanks to @dclayton-godaddy
  for his work on this one)

Bug fixes:

* #158 - The `--branch` option was broken and would not actually scan anything

v2.3.1 - 16 February 2021
-------------------------

Bug fixes:

* Added rust toolchain to allow for building of latest cryptography

Other changes:

* Added no-fetch to code snippets and note about what it does

v2.3.0 - 04 February 2021
-------------------------

Features:

* #42 - Report output on clean or successful scan. Add new `-q/--quiet` option to suppress output
* #43 - Report out of the list of exclusions. Add new `-v/--verbose` option to print exclusions
* #159 - Switched our primary development branch from `master` -> `main`
* Updated BFG refs from 1.13.0 to 1.13.2

v2.2.1 - 02 December 2020
-------------------------

Bugfixes:

* Rev build and release versions to match

v2.2.0 - 02 December 2020
-------------------------

Features:

* #119 - Added a new `--fetch`/`--no-fetch` option for local scans, controlling
  whether the local clone is refreshed before scan. (Thanks @jgowdy!)
* #125 - Implement CODEOWNERS and auto-assignment to maintainers on PRs

Bugfixes:

* #115 - Strange behavior can manifest with invalid sub-commands
* #117 - Ignore whitespace-only lines in exclusion files
* #118 - Local scans fetch remote origin
* #121 - Match rules specified with --git-rules-repo were not included in scans
* #140 - Ensure a valid output folder name in Windows

Other changes:

* #95 - Run CI across Linux, Windows, and MacOS
* #130 - Added references to Tartufo GoogleGroups mailing list to docs
* Fixed testing in Pypy3 and explicitly added Python 3.9 support
* #134 - Documented the release process
* #143 - Updated GitHub Action hashes to newest rev to address https://github.blog/changelog/2020-10-01-github-actions-deprecating-set-env-and-add-path-commands/ where possible

v2.0.1 - 09 October 2020
------------------------

* Fix the Docker build & deploy

v2.0.0 - 09 October 2020
------------------------

* #74, #75 - Rewrote and refreshed the documentation for the new 2.0 usage (via
  #111)

v2.0.0a2 - 05 October 2020
--------------------------

This bugfix release is to take care of a handful of issues discovered during the
initial alpha release for 2.0.

* #68 - Added consistent documentation through the codebase for classes,
  methods, and all other API elements (via #92)
* #90 - Presenting a friendlier error message when there is an error interacting
  with git (via #93)
* #94 - Fix tests that were failing on MacOS (via #97)
* #86 - Treat `tartufo.toml` preferentially over `pyproject.toml` when loading
  config (via #101)
* #91 - Load config from scanned repositories. This functionality previously
  existed in 1.x, but was missed during the rebuild for v2.0. This also resulted
  in a bit of an overall rewrite of config file discovery to eliminate some
  duplicated logic. (via #103)

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
