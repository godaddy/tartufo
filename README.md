# ![tartufo logo](docs/source/_static/img/tartufo.png)

[![Join Slack](https://img.shields.io/badge/Join%20us%20on-Slack-e01563.svg)](https://www.godaddy.com/engineering/slack/)
[![ci](https://github.com/godaddy/tartufo/workflows/ci/badge.svg)](https://github.com/godaddy/tartufo/actions?query=workflow%3Aci)
[![Codecov](https://img.shields.io/codecov/c/github/godaddy/tartufo)](https://codecov.io/gh/godaddy/tartufo)
[![PyPI](https://img.shields.io/pypi/v/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Status](https://img.shields.io/pypi/status/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tartufo)](https://pypi.org/project/tartufo/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/tartufo)](https://pypi.org/project/tartufo/)
[![Documentation Status](https://readthedocs.org/projects/tartufo/badge/?version=latest)](https://tartufo.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/github/license/godaddy/tartufo)](https://github.com/godaddy/tartufo/blob/main/LICENSE)

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
  --default-regexes / --no-default-regexes
                                  Whether to include the default regex list
                                  when configuring search patterns. Only
                                  applicable if --rules is also specified.
                                  [default: default-regexes]
  --entropy / --no-entropy        Enable entropy checks.  [default: entropy]
  --regex / --no-regex            Enable high signal regexes checks.
                                  [default: regex]
  --scan-filenames / --no-scan-filenames
                                  Check the names of files being scanned as
                                  well as their contents.  [default: scan-
                                  filenames]
  -of, --output-format [json|compact|text|report]
                                  Specify the format in which the output needs
                                  to be generated `--output-format
                                  json/compact/text/report`. Either `json`,
                                  `compact`, `text` or `report` can be
                                  specified. If not provided (default) the
                                  output will be generated in `text` format.
  -od, --output-dir DIRECTORY     If specified, all issues will be written out
                                  as individual JSON files to a uniquely named
                                  directory under this one. This will help
                                  with keeping the results of individual runs
                                  of tartufo separated.
  -td, --temp-dir DIRECTORY       If specified, temporary files will be
                                  written to the specified path
  --buffer-size INTEGER           Maximum number of issue to buffer in memory
                                  before shifting to temporary file buffering
                                  [default: 10000]
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
                                  [default: tartufo.toml]
  --target-config/--no-target-config
                                  Enable or Disable processing of the config file in the
                                  repository or folder being scanned
                                  i.e. config files like tartufo.toml or pyproject.toml
                                  [default: target-config]
  -q, --quiet / --no-quiet        Quiet mode. No outputs are reported if the
                                  scan is successful and doesn't find any
                                  issues
  -v, --verbose                   Display more verbose output. Specifying this
                                  option multiple times will incrementally
                                  increase the amount of output.
  --log-timestamps / --no-log-timestamps
                                  Enable or disable timestamps in logging
                                  messages.  [default: log-timestamps]
  --entropy-sensitivity INTEGER RANGE
                                  Modify entropy detection sensitivity. This
                                  is expressed as on a scale of 0 to 100,
                                  where 0 means "totally nonrandom" and 100
                                  means "totally random". Decreasing the
                                  scanner's sensitivity increases the
                                  likelihood that a given string will be
                                  identified as suspicious.  [default: 75;
                                  0<=x<=100]
  --color / --no-color            Enable or disable terminal color. If not
                                  provided (default), enabled if output is a
                                  terminal (TTY).
  -V, --version                   Show the version and exit.
  -h, --help                      Show this message and exit.

Commands:
  pre-commit        Scan staged changes in a pre-commit hook.
  scan-remote-repo  Automatically clone and scan a remote git repository.
  scan-folder       Scan a folder.
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
