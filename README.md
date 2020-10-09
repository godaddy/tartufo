# ![tartufo logo](docs/source/_static/img/tartufo.png)

[![Join Slack](https://img.shields.io/badge/Join%20us%20on-Slack-e01563.svg)](https://www.godaddy.com/engineering/slack/)
[![ci](https://github.com/godaddy/tartufo/workflows/ci/badge.svg)](https://github.com/godaddy/tartufo/actions?query=workflow%3Aci)
[![Codecov](https://img.shields.io/codecov/c/github/godaddy/tartufo)](https://codecov.io/gh/godaddy/tartufo)
[![PyPI](https://img.shields.io/pypi/v/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Status](https://img.shields.io/pypi/status/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/tartufo)](https://pypi.org/project/tartufo/)
[![Documentation Status](https://readthedocs.org/projects/tartufo/badge/?version=latest)](https://tartufo.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/github/license/godaddy/tartufo)](https://github.com/godaddy/tartufo/blob/master/LICENSE)

`tartufo` searches through git repositories for secrets, digging deep into
commit history and branches. This is effective at finding secrets accidentally
committed. `tartufo` also can be used by git pre-commit scripts to screen
changes for secrets before they are committed to the repository.

This tool will go through the entire commit history of each branch, and check
each diff from each commit, and check for secrets. This is both by regex and by
entropy. For entropy checks, tartufo will evaluate the shannon entropy for both
the base64 char set and hexidecimal char set for every blob of text greater
than 20 characters comprised of those character sets in each diff. If at any
point a high entropy string > 20 characters is detected, it will print to the
screen.

## Example

![Example Issue](docs/source/_static/img/example_issue.png)

## Documentation

Our main documentation site is hosted by Read The Docs, at
<https://tartufo.readthedocs.io>.

## Usage

```bash
Usage: tartufo [OPTIONS] COMMAND [ARGS]...

  Find secrets hidden in the depths of git.

  Tartufo will, by default, scan the entire history of a git repository for
  any text which looks like a secret, password, credential, etc. It can also
  be made to work in pre-commit mode, for scanning blobs of text as a pre-
  commit hook.

Options:
  --json / --no-json              Output in JSON format.
  --rules FILENAME                Path(s) to regex rules json list file(s).
  --default-regexes / --no-default-regexes
                                  Whether to include the default regex list
                                  when configuring search patterns. Only
                                  applicable if --rules is also specified.
                                  [default: True]

  --entropy / --no-entropy        Enable entropy checks.  [default: True]
  --regex / --no-regex            Enable high signal regexes checks.
                                  [default: False]

  -i, --include-paths FILENAME    File with regular expressions (one per
                                  line), at least one of which must match a
                                  Git object path in order for it to be
                                  scanned; lines starting with '#' are treated
                                  as comments and are ignored. If empty or not
                                  provided (default), all Git object paths are
                                  included unless otherwise excluded via the
                                  --exclude-paths option.

  -x, --exclude-paths FILENAME    File with regular expressions (one per
                                  line), none of which may match a Git object
                                  path in order for it to be scanned; lines
                                  starting with '#' are treated as comments
                                  and are ignored. If empty or not provided
                                  (default), no Git object paths are excluded
                                  unless effectively excluded via the
                                  --include-paths option.

  -e, --exclude-signatures TEXT   Specify signatures of matches that you
                                  explicitly want to exclude from the scan,
                                  and mark as okay. These signatures are
                                  generated during the scan process, and
                                  reported out with each individual match.
                                  This option can be specified multiple times,
                                  to exclude as many signatures as you would
                                  like.

  -od, --output-dir DIRECTORY     If specified, all issues will be written out
                                  as individual JSON files to a uniquely named
                                  directory under this one. This will help
                                  with keeping the results of individual runs
                                  of tartufo separated.

  --git-rules-repo TEXT           A file path, or git URL, pointing to a git
                                  repository containing regex rules to be used
                                  for scanning. By default, all .json files
                                  will be loaded from the root of that
                                  repository. --git-rules-files can be used to
                                  override this behavior and load specific
                                  files.

  --git-rules-files TEXT          Used in conjunction with --git-rules-repo,
                                  specify glob-style patterns for files from
                                  which to load the regex rules. Can be
                                  specified multiple times.

  --config FILE                   Read configuration from specified file.
                                  [default: pyproject.toml]

  -V, --version                   Show the version and exit.
  -h, --help                      Show this message and exit.

Commands:
  pre-commit        Scan staged changes in a pre-commit hook.
  scan-remote-repo  Automatically clone and scan a remote git repository.
  scan-local-repo   Scan a repository already cloned to your local system.

```

## Contributing

All contributors and contributions are welcome! Please see [our contributing
docs] for more information.

## Attributions

This project was inspired by and built off of the work done by Dylan Ayrey on
the [truffleHog] project.

[our contributing docs]: https://tartufo.readthedocs.io/en/latest/CONTRIBUTING.html
[pre-commit]: https://pre-commit.com/
[truffleHog]: https://github.com/dxa4481/truffleHog
