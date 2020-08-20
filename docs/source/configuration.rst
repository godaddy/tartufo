Configuration
=============

`tartufo` has a number of configuration options to customize its operation to
your specific needs. These various options can be specified both on the command
line, and in a configuration file, based on your needs.

Command Line
------------

The basic usage of the command can be seen via the ``-h`` or ``--help`` command
line switch, as seen here:

.. code-block:: sh

   $ tartufo --help
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

     -e, --exclude-signatures TEXT   Specify signatures of matches that you
                                     explicitly want to exclude from the scan,
                                     and mark as okay. These signatures are
                                     generated during the scan process, and
                                     reported out with each individual match.
                                     This option can be specified multiple times,
                                     to exclude as many signatures as you would
                                     like.

     --repo-path DIRECTORY           Path to local repo clone. If provided,
                                     git_url will not be used.

     --cleanup / --no-cleanup        Clean up all temporary result files.
                                     [default: False]

     --pre-commit                    Scan staged files in local repo clone.
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

     -h, --help                      Show this message and exit.

Configuration via File
----------------------

`tartufo` looks for configuration in two files in your current directory:
``tartufo.toml``, and ``pyproject.toml``. The latter is searched for as a
matter of convenience for Python projects, such as `tartufo` itself. Within
these files, `tartufo` will search for a section labeled ``[tool.tartufo]`` for
its configuration.

This file should be written in the `TOML`_ format. All command line options can
be specified in the configuration file, with or without the leading dashes, and
using either dashes or underscores for word separators. When the configuration
is read in, this will all be normalized automatically. For example, the
configuration for `tartufo` itself looks like this:

.. code-block:: toml

   [tool.tartufo]
   repo-path = "."
   json = false
   cleanup = true
   regex = true
   entropy = true

Note that all options specified in a configuration file are treated as
defaults, and will be overridden by any options specified on the command line.

.. _TOML: https://github.com/toml-lang/toml
