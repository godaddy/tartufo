v4.1.0 - April 3 2023
--------------------

Features:
* [#473](https://github.com/godaddy/tartufo/pull/473) - Introduces new flag `--target-config/--no-target-config` to enable or disable processing of the config file in the repository or folder being scanned
* [#455](https://github.com/godaddy/tartufo/pull/455) - Update documentation to fix incorrect wording
* [#458](https://github.com/godaddy/tartufo/pull/458) - Adds `--exclude-regex-patterns` to allow for regex-based exclusions
* [#479](https://github.com/godaddy/tartufo/pull/479) - Remove upward traversal logic for config discovery

Bug fixes:
* [#482](https://github.com/godaddy/tartufo/pull/482) - Code updates to process rule-patterns set up in the target's default config file i.e. tartufo.toml or pyproject.toml
* [#467](https://github.com/godaddy/tartufo/issues/467) - Multiple fixes to configuration
  file processing:
  - If multiple configuration files were specified, only the last was processed
    and no error or warning was generated. Now files are processed in order.
  - When multiple configuration files are specified, list-valued parameters are
    concatenated and single-valued parameters are overwritten by the last file
    that defines them.
  - Configuration files located in the target of a `scan-folder` operation were
    ignored; now they are located and processed in the same manner as for a
    `scan-local-repo` or `scan-remote-repo` operation.

v4.0.1 - Mar 1 2023
--------------------

Features:
* [#448](https://github.com/godaddy/tartufo/pull/448) - Update `GitPython` to `3.1.30` following [CVE-2022-24439](https://github.com/advisories/GHSA-hcpj-qp55-gfph)
* [#449](https://github.com/godaddy/tartufo/pull/449) - Update documentation to remove deprecated config items.

v4.0.0 - Jan 17 2023
--------------------

Features:
* [#433](https://github.com/godaddy/tartufo/pull/433) - Dropped support for deprecated flags rules, b64, hex 
  and corresponding code around deprecated options. Removed support for old signatures which generated with +/- 
  chars in git diff.

* [#411](https://github.com/godaddy/tartufo/pull/411) - Drop support for python 3.6.
  This version reached end of life several years ago, and end of security support at
  the end of 2021. Users with a requirement to run tartufo on this python version
  should remain at v3.3.x.
 
* [#403](https://github.com/godaddy/tartufo/pull/403) - Add support for python 3.11.
  * Update various support libraries to current versions
  * Rebase container to python 3.11
  * Add CI step to verify container is operational

* [#348](https://github.com/godaddy/tartufo/pull/348) - Add --no-git-check option
  to skip confirmation dialog for scan-folder

v3.3.1 - 23 Nov 2022
--------------------

Bug fixes:
* [#408](https://github.com/godaddy/tartufo/issues/408) - 3.3.0 container broken
  * Rebuild container using python 3.10 base instead of python 3.11
  * Eliminates reference to missing library present in 3.3.0 container
  * Eliminates requirement for build-it-yerself libraries in container

v3.3.0 - 22 Nov 2022
--------------------
Features:
* [#401](https://github.com/godaddy/tartufo/pull/401) - Add report output format

Bug fixes:
* [#375](https://github.com/godaddy/tartufo/pull/376) - Update the "Password in URL" default_regexes.json to identify the following:
  * usernames of lengths between 3-40
  * passwords of length between 3-40 
  * URL domain name, port, path, query parameters, and fragments of any length

* [#372](https://github.com/godaddy/tartufo/pull/372) Handle the case where exclude-signatures is a list of strings

v3.2.1 - 20 July 2022
----------------------

Features:
* [#368](https://github.com/godaddy/tartufo/pull/368) - Add update-signatures command to migrate deprecated signatures

v3.2.0 - 6 July 2022
----------------------

Bug fixes:
* [#360](https://github.com/godaddy/tartufo/issues/360) - Fix ANSI escape sequences being written to files on redirection
* [#363](https://github.com/godaddy/tartufo/pull/363) - Fix leading +/- in Tartufo matched_strings

v3.1.4 - 31 May 2022
----------------------

Bug fixes:

* [#352](https://github.com/godaddy/tartufo/pull/352) - Fix tartufo ignoring new files added to a Git repo
* [#351](https://github.com/godaddy/tartufo/pull/351) - Make pre-commit check staged changes instead of entire working directory

Misc:
* [356](https://github.com/godaddy/tartufo/pull/356) - Update documentation
* [354](https://github.com/godaddy/tartufo/pull/354) - Add a tartufo scan step in Tartufo's CI

v3.1.3 - 4 April 2022
----------------------

Bug fixes:

* [#329](https://github.com/godaddy/tartufo/issues/329) - Entropy exclusions(exclude-entropy-patterns) ignored when using
scan-local-repo
* [#343](https://github.com/godaddy/tartufo/issues/343) - Entropy exclusions(exclude-entropy-patterns) ignored when using
scan-remote-repo

v3.1.2 - 28 March 2022
----------------------

Bug fixes:

* [#339](https://github.com/godaddy/tartufo/issues/339) - Fix `click` compatibility issues. Specifically:
  * Pin to < 8.1.0 for Python 3.6, as support for that version was dropped
  * Pin to >= 8.1.0 for Python 3.7+, and change `resultcallback` usage to `result_callback`
  * Upgraded to the latest version of `black`

v3.1.1 - 25 March 2022
----------------------

Bug fixes:

* [#336](https://github.com/godaddy/tartufo/issues/336) - `_issue_file` was not defined by default, causing all scans to fail

v3.1.0 - 24 March 2022
----------------------

Features:

* [#328](https://github.com/godaddy/tartufo/pull/328) - Buffer issues beyond --buffer-size to a temporary file

Bug fixes:

* [#330](https://github.com/godaddy/tartufo/pull/330) - Allow newer versions of pygit2 for newer versions of Python

v3.0.0 - 5 January 2022
-----------------------

Version 3.0.0. Stable Release.

v3.0.0-rc.3 - 13 December 2021
------------------------------

Bug fixes:

* [#301](https://github.com/godaddy/tartufo/issues/301) - Parse new-style option
  values correctly, avoid duplicate processing of global options, and don't
  generate spurious deprecation warnings for these options.
* [#303](https://github.com/godaddy/tartufo/pull/303) - Include or exclude git submodules
  only if we're not working with a mirror clone.

v3.0.0-rc.2 - 09 December 2021
------------------------------

Bug fixes:

* [#296](https://github.com/godaddy/tartufo/pull/296), [#297](https://github.com/godaddy/tartufo/pull/297) -
  Fix our Docker image so that it actually builds, and the tartufo command works
* [#298](https://github.com/godaddy/tartufo/pull/298) - Fix how we determine whether
  we are scanning a shallow clone, so that it is more bulletproof.

v3.0.0-rc.1 - 09 December 2021
------------------------------

Bug fixes:

* [#284](https://github.com/godaddy/tartufo/pull/284) - Fix handling of first
  commit during local scans; an exception was raised instead of processing the
  commit.

Misc:

* [#282](https://github.com/godaddy/tartufo/pull/282) - Remove old style config for `exclude-entropy-patterns`
* [#292](https://github.com/godaddy/tartufo/pull/292) - Use the latest `click`
  to provide better output on boolean flag defaults

Features:

* [#270](https://github.com/godaddy/tartufo/issues/270) - When no refs/branches
  are found locally, tartufo will now scan the repo HEAD as a single commit,
  effectively scanning the entire codebase at once.
* [#265](https://github.com/godaddy/tartufo/issues/265) - Adds new `--entropy-sensitivity`
  option which provides a friendlier way to adjust entropy detection sensitivity.
  This replaces `--b64-entropy-score` and `--hex-entropy-score`, which now are
  marked as deprecated.
* [#273](https://github.com/godaddy/tartufo/issues/273) - Entropy checking support
  routines have been rewritten to utilize library abstractions and operate more
  efficiently while returning identical results.
* [#177](https://github.com/godaddy/tartufo/issues/177) -
  [base64url](https://datatracker.ietf.org/doc/html/rfc4648#section-5) encodings
  are now recognized and scanned for entropy.
* [#268](https://github.com/godaddy/tartufo/issues/268) - Adds a new
  `--recurse / --no-recurse` flag which allows users to recursively scan the entire directory or just
  the root directory
* [#256](https://github.com/godaddy/tartufo/issues/256) - Deprecated `--rules` in
  favor of a new `rule-patterns` config option. This is the final piece of config
  that was still stored in an external file.
* [#202](https://github.com/godaddy/tartufo/issues/202) - Supports new format of exclusions in config file
  with the ability to specify the reason along with exclusion
* [#257](https://github.com/godaddy/tartufo/issues/257) - Supports new format of include-path-patterns and
  exclude-path-patterns in config file with the ability to specify the reason along with the path-patterns.

v3.0.0-alpha.1 - 11 November 2021
---------------------------------

Bug fixes:

* [#247](https://github.com/godaddy/tartufo/issues/247) - The `--branch` qualifier
  now works again when using `scan-remote-repo`.

Features:

* [#227](https://github.com/godaddy/tartufo/pull/227) - Report findings incrementally
  as scan progresses instead of holding all of them until it has completed. This
  is a re-implementation of [#108](https://github.com/godaddy/tartufo/pull/108);
  thanks to @dclayton-godaddy for showing the way.
* [#244](https://github.com/godaddy/tartufo/pull/244) - Drops support for
  `--fetch/--no-fetch` option for local scans
* [#253](https://github.com/godaddy/tartufo/issues/253) - Drops support for `--json` and `--compact`
  and consolidates the two options into one `---output-format json/compact/text`
* [#259](https://github.com/godaddy/tartufo/pull/259) - Adds a new
  `--scan-filenames/--no-scan-filenames` flag which allows users to enable or disable file name scanning.
* [#254](https://github.com/godaddy/tartufo/pull/260) - Changes the default value of
  `--regex/--no-regex` to True.

Misc:

* [#255](https://github.com/godaddy/tartufo/issues/255) - Removed deprecated flags
  --include-paths and --exclude-paths

v2.10.1 - 27 December 2021
--------------------------

Bug fixes:

* [#309](https://github.com/godaddy/tartufo/pull/309) Fixes an issue where verbose output display
would error out if the new-style entropy exclusion pattern was used

v2.10.0 - 3 November 2021
-------------------------

Bug fixes:

* [#247](https://github.com/godaddy/tartufo/issues/247) All versions of tartufo from
  v2.2.0 through v2.9.0 inclusive mishandle `scan-remote-repo`. Only the repository's
  default branch was scanned, and secrets present in other branches would not be
  discovered. Additionally, the `--branch branch-name` option did not operate correctly
  for remote repositories. Some versions would scan nothing and report no errors, and
  other versions aborted immediately, claiming the branch did not exist (even if it did).
  v2.10.0 corrects these problems and may detect secrets that were not reported by previous versions.

Features:

* [#231](https://github.com/godaddy/tartufo/issues/231) Change toml parsing library to use tomlkit

Other changes:

* [#251](https://github.com/godaddy/tartufo/issues/251) Document update to use --no-fetch flag
  to all scan-local-repo

v2.9.0 - 19 October 2021
------------------------

Bug fixes:

* Reverted [#222](https://github.com/godaddy/tartufo/pull/222) -- users had been
  relying on the previously implemented behavior, causing this change to break
  their pipelines.

Features:

* Behavior introduced in [#222](https://github.com/godaddy/tartufo/pull/222) is
  now opt-in via an updated config specification for `exclude-entropy-patterns`.
  This is now done via a TOML table, rather than a specifically patterned string.
  Users who have the old style configuration will now receive a
  `DeprecationWarning` stating that the old behavior will go away with v3.0.
* Fixed up warning handling so that we can display `DeprecationWarnings` to users
  more easily.
* [#223](https://github.com/godaddy/tartufo/pull/223) New flags
  (`-b64`/`--b64-entropy-score` and `-hex`/`--hex-entropy-score`) allow for user
  tuning of the entropy reporting sensitivity. They default to 4.5 and 3.0,
  respectively.

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
* #143 - Updated GitHub Action hashes to newest rev to address <https://github.blog/changelog/2020-10-01-github-actions-deprecating-set-env-and-add-path-commands/> where possible

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
limitations in PyPI (<https://pypi.org/help/#file-name-reuse>), even if a previous
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

* Docker images are built and pushed automatically to <https://hub.docker.com/r/godaddy/tartufo>
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
* Added support for <https://pre-commit.com/> style hooks
