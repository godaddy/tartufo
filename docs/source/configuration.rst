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
       'poetry.lock',
       # To not have to escape `\` in regexes, use single quoted
       # TOML 'literal strings'
       'docs/source/(.*)\.rst',
   ]
   exclude-signatures = [
       "62f22e4500140a6ed959a6143c52b0e81c74e7491081292fce733de4ec574542",
       "ecbbe1edd6373c7e2b88b65d24d7fe84610faafd1bc2cf6ae35b43a77183e80b",
   ]

Note that all options specified in a configuration file are treated as
defaults, and will be overridden by any options specified on the command line.

For a full list of available command line options, check out the :doc:`usage`
document.

Configuration File Exclusive Options
------------------------------------

.. versionadded:: 3.0

As of version 3.0, we have added several configuration options which are
available only in the configuration file. This is due to the nature of their
construction, and the fact that they would be exceedingly difficult to
represent on the command line.

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

.. _TOML: https://toml.io/
.. _array of tables: https://toml.io/en/v1.0.0#array-of-tables
