=============
Configuration
=============

``tartufo`` has a wide variety of options to customize its operation available
:doc:`on the command line<usage>`. Some of these options, however, can be a bit
unwieldy and lead to an overly cumbersome command. It also becomes difficult to
reliably reproduce the same command in all environments when done this way.

To help with these problems, ``tartufo`` can also be configured by way of a
configuration file! You can `tell tartufo what config file to use
<usage.html#cmdoption-tartufo-config>`__, or, it will automatically discover one
for you. Starting in the current working directory, and traversing backward up
the directory tree, it will search for both a ``tartufo.toml`` and a
``pyproject.toml``. The latter is searched for as a matter of convenience for
Python projects, such as ``tartufo`` itself. For an example of the tree
traversal, let's say you running ``tartufo`` from the directory
``/home/my_user/projects/my_project``. ``tartufo`` will look for the
configuration files first in this directory, then in ``/home/my_user/projects/``,
then in ``/home/my_user``, etc.

Within these files, ``tartufo`` will look for a section labeled
``[tool.tartufo]`` to find its configuration, and will load all items from there
just as though they had been specified on the command line. This file must be
written in the `TOML`_ format, which should look mostly familiar if you have
dealt with any other configuration file format before.

All command line options can be specified in the configuration file, with or
without the leading dashes, and using either dashes or underscores for word
separators. When the configuration is read in, this will all be normalized
automatically. For example, the configuration for `tartufo` itself looks like
this:

.. code-block:: toml

   [tool.tartufo]
   repo-path = "."
   json = false
   regex = true
   entropy = true
   exclude-path-patterns = [
    {path-pattern = 'poetry\.lock'},
    {path-pattern = 'pyproject\.toml'},
    # To not have to escape `\` in regexes, use single quoted
    # TOML 'literal strings'
    {path-pattern = 'docs/source/(.*)\.rst'},
   ]
   exclude-signatures = [
       {signature = "62f22e4500140a6ed959a6143c52b0e81c74e7491081292fce733de4ec574542"},
       {signature = "ecbbe1edd6373c7e2b88b65d24d7fe84610faafd1bc2cf6ae35b43a77183e80b"},
   ]

Note that all options specified in a configuration file are treated as
defaults, and will be overridden by any options specified on the command line.

For a full list of available command line options, check out the :doc:`usage`
document.

.. _exclude-signatures:

Excluding Signatures
--------------------

You might see the following header in the output for an issue:

.. image:: _static/img/issue-signature.png

Looking at this information, it's clear that this issue was found in a test
file, and it's probably okay. Of course, you will want to look at the actual
body of what was found and determine that for yourself. But let's say that this
really is okay, and we want tell ``tartufo`` to ignore this issue in future
scans. To do this, you can either specify it on the command line...

.. code-block:: sh

    > tartufo -e 2a3cb329b81351e357b09f1b97323ff726e72bd5ff8427c9295e6ef68226e1d1
    # No output! Success!
    >

Or you can add it to your config file, so that this exclusion is always
remembered!

.. code-block:: toml

    [tool.tartufo]
    exclude-signatures = [
      "2a3cb329b81351e357b09f1b97323ff726e72bd5ff8427c9295e6ef68226e1d1",
    ]

Done! This particular issue will no longer show up in your scan results.

As of version 3.0, a new format for specifying exclusion signatures has been added.

.. code-block:: toml

    [tool.tartufo]
    exclude-signatures = [
        {signature = "2a3cb329b81351e357b09f1b97323ff726e72bd5ff8427c9295e6ef68226e1d1", reason = "reason for exclusion"},
    ]

.. note::

    Currently all 3 formats of signature exclusions are supported. However, only `TOML`_ `array of tables`_ format
    will be supported in future versions.

.. _limiting-scans-by-paths:

Limiting Scans by Path
----------------------
You can include or exclude paths for scanning using
Python Regular Expressions (regex) and the `--include-path-patterns` and
`--exclude-path-patterns` options.

.. warning::

   Using include patterns is more dangerous, since it's easy to miss the
   creation of new secrets if future files don't match an existing include
   rule. We recommend only using fine-grained exclude patterns instead.

.. code-block:: toml

   [tool.tartufo]
   include-path-patterns = [
      'src/',
      'gradle/',
      # regexes must match the entire path, but can use python's regex syntax
      # for case-insensitive matching and other advanced options
      '(.*/)?id_[rd]sa$',
      # Single quoted strings in TOML don't require escapes for `\` in regexes
      '(?i).*\.(properties|conf|ini|txt|y(a)?ml)$',
   ]
   exclude-path-patterns = [
      '(.*/)?\.classpath$',
      '.*\.jmx$',
      '(.*/)?test/(.*/)?resources/',
   ]

The filter expressions can also be specified as command line arguments.
Patterns specified like this are merged with any patterns specified
in the config file:

.. code-block:: sh

   > tartufo \
     --include-path-patterns 'src/' -ip 'gradle/' \
     --exclude-path-patterns '(.*/)?\.classpath$' -xp '.*\.jmx$' \
     scan-local-repo file://path/to/my/repo.git

As of version 3.0, a new format for specifying paths has been added.

.. code-block:: toml

   [tool.tartufo]
   include-path-patterns = [
      {path-pattern = 'src/', reason='reason for inclusion'},
   ]
   exclude-path-patterns = [
      {path-pattern = 'poetry\.lock', reason='reason for exclusion'},
   ]

.. note::

    Currently all 3 formats are supported. However, only `TOML`_ `array of tables`_ format
    will be supported in future versions.

Configuration File Exclusive Options
------------------------------------

.. versionadded:: 3.0

As of version 3.0, we have added several configuration options which are
available only in the configuration file. This is due to the nature of their
construction, and the fact that they would be exceedingly difficult to
represent on the command line.

.. _rule-patterns:

Rule Patterns
+++++++++++++

.. versionadded:: 3.0

``tartufo`` comes bundled with a number of regular expression rules that it will
check your code for by default. If you would like to scan for additional regular
expressions, you may add them to your configuration with the ``rule-patterns``
directive. This directive utilizes a `TOML`_ `array of tables`_, and thus can
take one of two forms:

Option 1: Keeping it contained in your ``[tool.tartufo]`` table.

.. code-block:: toml

    [tool.tartufo]
    rule-patterns = [
        {reason = "RSA private key 2", pattern = "-----BEGIN EC PRIVATE KEY-----"},
        {reason = "Null characters in GitHub Workflows", pattern = '\0', path-pattern = '\.github/workflows/(.*)\.yml'}
    ]

Option 2: Separating each rule out into its own table.

.. code-block:: toml

    [[tool.tartufo.rule-patterns]]
    reason = "RSA private key 2"
    pattern = "-----BEGIN EC PRIVATE KEY-----"

    [[tool.tartufo.rule-patterns]]
    reason = "Null characters in GitHub Workflows"
    pattern = '\0'
    path-pattern = '\.github/workflows/(.*)\.yml'

.. note::

    There are 3 different keys used here: ``reason``, ``pattern``, and ``path-pattern``.
    Only ``reason`` and ``pattern`` are required. If no ``path-pattern`` is
    specified, then the pattern will be used to scan against all files.

.. _entropy-exclusion-patterns:

Entropy Exclusion Patterns
++++++++++++++++++++++++++

Entropy scans can produce a high number of false positive matches such as git
SHAs or MD5 digests. To avoid these false positives, you can use the
``exclude-entropy-patterns`` configuration option. These patterns will be
applied to and matched against any strings flagged by entropy checks. As above,
this directive utilizes an `array of tables`_, enabling two forms:

Option 1:

.. code-block:: toml

    [tool.tartufo]
    exclude-entropy-patterns = [
        {path-pattern = 'docs/.*\.md$', pattern = '^[a-zA-Z0-9]$', reason = 'exclude all git SHAs in the docs'},
        {path-pattern = '\.github/workflows/.*\.yml', pattern = 'uses: .*@[a-zA-Z0-9]{40}', reason = 'GitHub Actions'}
    ]

Option 2:

.. code-block:: toml

    [[tool.tartufo.exclude-entropy-patterns]]
    path-pattern = 'docs/.*\.md$'
    pattern = '^[a-zA-Z0-9]$'
    reason = 'exclude all git SHAs in the docs'

    [[tool.tartufo.exclude-entropy-patterns]]
    path-pattern = '\.github/workflows/.*\.yml'
    pattern = 'uses: .*@[a-zA-Z0-9]{40}'
    reason = 'GitHub Actions'


There are 5 relevant keys for this directive, as described below.

============ ======== ============================ ==============================================================
Key          Required Value                        Description
============ ======== ============================ ==============================================================
pattern      Yes      Regular expression           The pattern used to check against the match
path-pattern No       Regular expression           A pattern to specify to what files the exclusion will apply
reason       No       String                       A plaintext reason the exclusion has been added
match-type   No       String ("match" or "scope")  Whether to perform a `search or match`_ regex operation
scope        No       String ("word" or "line")    Whether to match against the current word or full line of text
============ ======== ============================ ==============================================================

.. _TOML: https://toml.io/
.. _array of tables: https://toml.io/en/v1.0.0#array-of-tables
.. _search or match: https://docs.python.org/3/library/re.html#search-vs-match
