# tartufo

![Travis (.org)](https://img.shields.io/travis/godaddy/tartufo)
![Codecov](https://img.shields.io/codecov/c/github/godaddy/tartufo)
![PyPI](https://img.shields.io/pypi/v/tartufo)
![PyPI - Status](https://img.shields.io/pypi/status/tartufo)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tartufo)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tartufo)

Searches through git repositories for secrets, digging deep into commit history and branches.
This is effective at finding secrets accidentally committed. tartufo also can be used by git
pre-commit scripts to screen changes for secrets before they are committed to the repository.

## Features

tartufo offers the following features:

### Regex Checking

tartufo previously functioned by running entropy checks on git diffs. This functionality still exists, but high signal regex checks have been added, and the ability to surpress entropy checking has also been added.

This performs only regular expression checking:

```bash
tartufo --regex --entropy=False https://github.com/godaddy/tartufo.git
```

while this checks only for patterns with high entropy:

```bash
tartufo file:///user/godaddy/codeprojects/tartufo/
```

Specifying either `--regex` or `--entropy` without a value implies `=True`; if these arguments
are missing, the default behavior is to perform entropy checking but not regex checking.

If all types of checking are disabled, a RuntimeError exception is raised. It is presumed that
the caller did not intend to request an operation that scans nothing.

### Limiting Scans by Path

With the `--include_paths` and `--exclude_paths` options, it is also possible to limit scanning to a subset of objects in the Git history by defining regular expressions (one per line) in a file to match the targeted object paths. To illustrate, see the example include and exclude files below:

_include-patterns.txt:_

```ini
src/
# lines beginning with "#" are treated as comments and are ignored
gradle/
# regexes must match the entire path, but can use python's regex syntax for
# case-insensitive matching and other advanced options
(?i).*\.(properties|conf|ini|txt|y(a)?ml)$
(.*/)?id_[rd]sa$
```

_exclude-patterns.txt:_

```ini
(.*/)?\.classpath$
.*\.jmx$
(.*/)?test/(.*/)?resources/
```

These filter files could then be applied by:

```bash
tartufo --include_paths include-patterns.txt --exclude_paths exclude-patterns.txt file://path/to/my/repo.git
```

With these filters, issues found in files in the root-level `src` directory would be reported, unless they had the `.classpath` or `.jmx` extension, or if they were found in the `src/test/dev/resources/` directory, for example. Additional usage information is provided when calling `tartufo` with the `-h` or `--help` options.

These features help cut down on noise, and makes the tool easier to shove into a devops pipeline.

![Example](https://i.imgur.com/YAXndLD.png)

### Specifying Repositories

Normally, the URL of the repository to scan is supplied on the command line:

```bash
tartufo https://github.com/godaddy/tartufo.git
```

When invoked in this way, tartufo clones the repository to a scratch directory, scans the
local clone, and then deletes it. If a local repository clone already exists, it can be scanned
directly:

```bash
tartufo --repo_path /my/local/clone
```

If both `--repo_path` and a URL are supplied, the URL is ignored and the specified local clone
is scanned. If neither is provided, a SyntaxError exception is raised.

### Pre-Commit Scans

The `--pre_commit` flag instructs tartufo to scan staged, uncommitted changes in a local
repository. The repository location can be specified using `--repo_path`, but it is legal to
not supply a location; in this case, the caller's current working directory is assumed to be
somewhere within the local clone's tree and the repository root is determined automatically.

The following example demonstrates how tartufo can be used to verify secrets will not be
committed to a git repository in error:

_.git/hooks/pre-commit:_

```bash
#!/bin/sh

# Redirect output to stderr.
exec 1>&2

# Check for suspicious content.
tartufo --pre_commit --regex --entropy
```

Git will execute tartufo before committing any content. If problematic changes are detected,
they are reported by tartufo and git aborts the commit process. Only when tartufo returns a
success status (indicating no potential secrets were discovered) will git commit the staged changes.

Note that it is always possible, although not recommended, to bypass the pre-commit hook by
using `git commit --no-verify`.

If you would like to automate these hooks, you can use the [pre-commit] tool by
adding a `.pre-commit-config.yaml` file to your repository similar to the following:

```yaml
- repo: https://github.com/godaddy/tartufo
  rev: master
  hooks:
  - id: tartufo
```

That's it! Now your contributors only need to run `pre-commit install --install-hooks`,
and `tartufo` will automatically be run as a pre-commit hook.

### Temporary file cleanup

tartufo stores the results in temporary files, which are left on disk by default, to allow
inspection if problems are found. To automatically delete these files when tartufo completes, specify
the `--cleanup` flag:

```bash
tartufo --cleanup
```

## Install

```bash
pip install tartufo
```

## Customizing

Custom regexes can be added with the following flag `--rules /path/to/rules`. This should be a json file of the following format:

```ini
{
    "RSA private key": "-----BEGIN EC PRIVATE KEY-----"
}
```

Things like subdomain enumeration, s3 bucket detection, and other useful regexes highly custom to the situation can be added.

Normally, the custom regexes are added to the default regexes. If the default regexes should not be included, add the following flag: `--default-regexes=False`

Feel free to also contribute high signal regexes upstream that you think will benefit the community. Things like Azure keys, Twilio keys, Google Compute keys, are welcome, provided a high signal regex can be constructed.

tartufo's base rule set sources from <https://github.com/dxa4481/truffleHogRegexes/blob/master/truffleHogRegexes/regexes.json>

## How it works

This module will go through the entire commit history of each branch, and check each diff from each commit, and check for secrets. This is both by regex and by entropy. For entropy checks, tartufo will evaluate the shannon entropy for both the base64 char set and hexidecimal char set for every blob of text greater than 20 characters comprised of those character sets in each diff. If at any point a high entropy string >20 characters is detected, it will print to the screen.

## Help

```bash
Usage: tartufo [OPTIONS] [GIT_URL]

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
                                  [default: --default-regexes]
  --entropy / --no-entropy        Enable entropy checks. [default: True]
  --regex / --no-regex            Enable high signal regexes checks. [default:
                                  False]
  --since-commit TEXT             Only scan from a given commit hash.
  --max-depth INTEGER             The max commit depth to go back when
                                  searching for secrets. [default: 1000000]
  --branch TEXT                   Specify a branch name to scan only that
                                  branch.
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
  --repo-path DIRECTORY           Path to local repo clone. If provided,
                                  git_url will not be used.
  --cleanup / --no-cleanup        Clean up all temporary result files.
                                  [default: False]
  --pre-commit                    Scan staged files in local repo clone.
  --config FILENAME               Read configuration from specified file.
                                  [default: pyproject.toml]
  -h, --help                      Show this message and exit.
```

## Contributing

Please see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Attributions

This project was inspired by and built off of the work done by Dylan Ayrey on
the [truffleHog] project.

[pre-commit]: https://pre-commit.com/
[truffleHog]: https://github.com/dxa4481/truffleHog
