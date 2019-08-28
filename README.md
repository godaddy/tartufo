# truffleHog

Searches through git repositories for secrets, digging deep into commit history and branches.
This is effective at finding secrets accidentally committed. truffleHog also can be used by git
pre-commit scripts to screen changes for secrets before they are committed to the repository.

## Features

truffleHog offers the following features:

### Regex Checking

truffleHog previously functioned by running entropy checks on git diffs. This functionality still exists, but high signal regex checks have been added, and the ability to surpress entropy checking has also been added.

This performs only regular expression checking:

```bash
truffleHog --regex --entropy=False https://github.com/dxa4481/truffleHog.git
```

while this checks only for patterns with high entropy:

```bash
truffleHog file:///user/dxa4481/codeprojects/truffleHog/
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
truffleHog --include_paths include-patterns.txt --exclude_paths exclude-patterns.txt file://path/to/my/repo.git
```

With these filters, issues found in files in the root-level `src` directory would be reported, unless they had the `.classpath` or `.jmx` extension, or if they were found in the `src/test/dev/resources/` directory, for example. Additional usage information is provided when calling `trufflehog` with the `-h` or `--help` options.

These features help cut down on noise, and makes the tool easier to shove into a devops pipeline.

![Example](https://i.imgur.com/YAXndLD.png)

### Specifying Repositories

Normally, the URL of the repository to scan is supplied on the command line:

```bash
truffleHog https://github.com/dxa4481/truffleHog.git
```

When invoked in this way, truffleHog clones the repository to a scratch directory, scans the
local clone, and then deletes it. If a local repository clone already exists, it can be scanned
directly:

```bash
truffleHog --repo_path /my/local/clone
```

If both `--repo_path` and a URL are supplied, the URL is ignored and the specified local clone
is scanned. If neither is provided, a SyntaxError exception is raised.

### Pre-Commit Scans

The `--pre_commit` flag instructs truffleHog to scan staged, uncommitted changes in a local
repository. The repository location can be specified using `--repo_path`, but it is legal to
not supply a location; in this case, the caller's current working directory is assumed to be
somewhere within the local clone's tree and the repository root is determined automatically.

The following example demonstrates how truffleHog can be used to verify secrets will not be
committed to a git repository in error:

_.git/hooks/pre-commit:_

```bash
#!/bin/sh

# Redirect output to stderr.
exec 1>&2

# Check for suspicious content.
truffleHog --pre_commit --regex --entropy
```

Git will execute truffleHog before committing any content. If problematic changes are detected,
they are reported by truffleHog and git aborts the commit process. Only when truffleHog returns a
success status (indicating no potential secrets were discovered) will git commit the staged changes.

Note that it is always possible, although not recommended, to bypass the pre-commit hook by
using `git commit --no-verify`.

## Install

```bash
pip install truffleHog
```

## Customizing

Custom regexes can be added with the following flag `--rules /path/to/rules`. This should be a json file of the following format:

```ini
{
    "RSA private key": "-----BEGIN EC PRIVATE KEY-----"
}
```

Things like subdomain enumeration, s3 bucket detection, and other useful regexes highly custom to the situation can be added.

Feel free to also contribute high signal regexes upstream that you think will benefit the community. Things like Azure keys, Twilio keys, Google Compute keys, are welcome, provided a high signal regex can be constructed.

trufflehog's base rule set sources from <https://github.com/dxa4481/truffleHogRegexes/blob/master/truffleHogRegexes/regexes.json>

## How it works

This module will go through the entire commit history of each branch, and check each diff from each commit, and check for secrets. This is both by regex and by entropy. For entropy checks, truffleHog will evaluate the shannon entropy for both the base64 char set and hexidecimal char set for every blob of text greater than 20 characters comprised of those character sets in each diff. If at any point a high entropy string >20 characters is detected, it will print to the screen.

## Help

```bash
usage: truffleHog [-h] [--json] [--rules RULES] [--entropy [BOOLEAN]]
                  [--regex [BOOLEAN]] [--since_commit SINCE_COMMIT]
                  [--max_depth MAX_DEPTH] [--branch BRANCH]
                  [-i INCLUDE_PATHS_FILE] [-x EXCLUDE_PATHS_FILE]
                  [--repo_path REPO_PATH] [--cleanup] [--pre_commit]
                  [git_url]

Find secrets hidden in the depths of git.

positional arguments:
  git_url               repository URL for secret searching

optional arguments:
  -h, --help            show this help message and exit
  --json                Output in JSON
  --rules RULES         Ignore default regexes and source from json list file
  --entropy [BOOLEAN]   Enable entropy checks [default: True]
  --regex [BOOLEAN]     Enable high signal regex checks [default: False]
  --since_commit SINCE_COMMIT
                        Only scan from a given commit hash
  --max_depth MAX_DEPTH
                        The max commit depth to go back when searching for
                        secrets
  --branch BRANCH       Name of the branch to be scanned
  -i INCLUDE_PATHS_FILE, --include_paths INCLUDE_PATHS_FILE
                        File with regular expressions (one per line), at least
                        one of which must match a Git object path in order for
                        it to be scanned; lines starting with "#" are treated
                        as comments and are ignored. If empty or not provided
                        (default), all Git object paths are included unless
                        otherwise excluded via the --exclude_paths option.
  -x EXCLUDE_PATHS_FILE, --exclude_paths EXCLUDE_PATHS_FILE
                        File with regular expressions (one per line), none of
                        which may match a Git object path in order for it to
                        be scanned; lines starting with "#" are treated as
                        comments and are ignored. If empty or not provided
                        (default), no Git object paths are excluded unless
                        effectively excluded via the --include_paths option.
  --repo_path REPO_PATH
                        Path to local repo clone. If provided, git_url will
                        not be used
  --cleanup             Clean up all temporary result files
  --pre_commit          Scan staged files in local repo clone
```

## Version history

| Version | Change(s)
| ------- | ---
| 2.0.99  | GoDaddy Maintainer information

