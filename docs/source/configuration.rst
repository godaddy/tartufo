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

Note that all options specified in a configuration file are treated as
defaults, and will be overridden by any options specified on the command line.

For a full list of configuration options, check out the :doc:`usage` document.

.. _TOML: https://github.com/toml-lang/toml
