=========
Upgrading
=========

Upgrading ``tartufo`` from release 2 to release 3 introduces some behavioral and
interface changes. Current users of release 2 should review this summary to
understand how to transition to release 3 as painlessly as possible.

General Behavioral Changes
--------------------------

``tartufo`` release 3 is generally more accurate than previous releases. It may
detect problems that were not recognized by release 2 scans (especially earlier
2.x releases). A scan of your code base prior to upgrading will simplify the
process of identifying new findings that are attributable to these behavior
changes so they can be remediated or suppressed.

Remote Repository Scanning
++++++++++++++++++++++++++

``tartufo`` releases between 2.2.0 and 2.9.0 (inclusive) mishandled remote
repositories. Only the repository's default branch was scanned; secrets
present only on other branches would not be discovered.

Additionally, the ``--branch branch-name`` option did not operate correctly.
Some versions scanned nothing and reported no errors, and other versions aborted
immediately after reporting the branch did not exist (even when it did).

``tartufo`` release 3 scans all remote repository branches by default, and
correctly scans only a single branch if one is specified using ``--branch``. As
a consequence, it may discover secrets that were not reported by earlier versions.

These fixes were backported to ``tartufo`` release 2.10.0.

Live Output
+++++++++++

``tartufo`` release 3 reports findings incrementally as a scan progresses; previous
releases did not perform any reporting until the entire scan was completed.

Entropy Scanning
++++++++++++++++

Beginning with release 3, ``tartufo`` recognizes base64url-encoded strings in
addition to base64-encoded strings.

If your code contains base64url encodings (or strings that look like base64url
encodings), these strings now will be checked for high entropy and may produce
new findings.

Additionally, strings that contain combinations of base64 and base64url character
sets (whether they are actual encodings or not) will be scanned differently by
release 3. Previously, base64 substrings would be extracted and scanned independently,
but now the larger string will be scanned (once) in its entirety. This can result
in signature changes (because the new suspect string is larger than the string
recognized by release 2.x) and possibly fewer findings (because one longer string
will be flagged instead of multiple substrings). Real-life files do not typically
contain sequences that will exhibit this behavior.

Shallow Repositories
++++++++++++++++++++

When ``tartufo`` release 2 scanned a shallow repository (a repository with no
refs or branches found locally), it did not actually scan anything.

In the same situation, ``tartufo`` release 3 scans the repository HEAD as a single
commit, effectively scanning the entire existing codebase (but none of its history)
at once.

This scenario is commonly encountered in GitHub actions, which perform shallow
checkouts.

Nonfunctional Options
+++++++++++++++++++++

``tartufo`` release 3 uses `pygit2`_ instead of `GitPython`_ to access git repositories.
While this provides vastly improved performance with
generally equivalent functionality, some less-frequently used options require
reimplementation and currently are nonfunctional. We plan to provide either
replacements or reimplementations in the future.

The ``--since-commit`` option is intended to restrict scans to a subset of
repository history; the ``--max-depth`` option provides roughly the same
functionality specified differently. Both options are ignored by ``tartufo``
release 3. Refer to `#267`_ for more information about this topic.

Changes to Default Behavior
---------------------------

Some defaults have changed for the new release. If you wish to retain the previous
behavior, adjust your configuration options to request it explicitly.

Regex Scanning
++++++++++++++

Previously, ``tartufo`` did not perform regex scanning for sensitive strings by
default. Release 3 *does* perform regex scanning by default.

Explicitly disable regex scanning to preserve the old behavior:

.. code-block:: toml

    [tool.tartufo]
    regex = false

Alternatively, add ``--no-regex`` to your ``tartufo`` command line.

Retired Options
---------------

Some options that were deprecated in later 2.x releases no longer are supported
by version 3. You will need to alter your command line and/or configuration options
to specify the required information in a release 3-compatible manner.

Fetch Before Local Scans
++++++++++++++++++++++++

``tartufo`` release 2 supported command option ``--fetch`` for local repository
scans, in order to force an update of the repository before scanning it. ``tartufo``
release 3 no longer recognizes this option.

Instead of using ``--fetch``, perform an explicit ``git fetch`` command prior to
executing ``tartufo``.

If you were using ``--no-fetch``, simply remove the option. ``tartufo`` release 3
never performs fetches prior to scanning local repositories.

Output Formatting
+++++++++++++++++

``tartufo`` release 2 supported command options ``--json`` and ``--compact`` to
control output formatting. ``tartufo`` release 3 no longer recognizes these options.

Replace ``--json`` with ``--output-format json``, and replace ``--compact`` with
``--output-format compact``.

Path Scoping
++++++++++++

``tartufo`` release 2 supported command options ``--include-paths`` and
``--exclude-paths`` in order to control which files were (or were not) scanned.
In either case, the option accepted a filename which was expected to contain path
patterns to include or exclude, respectively. ``tartufo`` release 3 no longer
recognizes these options.

It is recommended that these path expressions be migrated from the external file
to your ``pyproject.toml`` file and converted to `TOML`_ `array of tables`_ format.
The supported formats are described in :ref:`limiting-scans-by-paths`.

Deprecated Options
------------------

``tartufo`` release 3 deprecates some release 2 options. Although no action is
required at this time, replacing these options with their newer equivalents will
reduce future disruptions when they are retired.

Updating Signatures
-------------------

``tartufo`` release 3.2.0 deprecated a number of signatures that were generated
with the leading `+`/`-` from the git diff erroneously. These signatures will no
longer work in release 4. An additional command ``tartufo update-signatures`` was
added which scans a local repository, automatically updates the deprecated
exclude-signatures in your tartufo config file, and removes any resulting duplicates.

Use ``--no-update-configuration`` to prevent ``tartufo`` from overwriting your config.
Use ``--no-remove-duplicates`` to prevent ``tartufo`` from removing duplicate signatures.

When removing duplicate signatures ``tartufo`` will keep the first signature it finds
and discard the rest.

External Rules Files
++++++++++++++++++++

The ``--rules`` command option accepts a filename that is expected to contain
one or more rule patterns. ``tartufo`` release 3 deprecates this option.

It is recommended that these patterns be migrated from the external file to your
``pyproject.toml`` file and converted to `TOML`_ `array of tables`_ format.
The supported formats are described in :ref:`rule-patterns`.

Entropy Scan Sensitivity
++++++++++++++++++++++++

The new ``--entropy-sensitivity`` option is intended to replace both
``--b64-entropy-score`` and ``--hex-entropy-score``. The new option adjusts
sensitivity for both encodings consistently, using a scale of 0-100. To convert:

* Users of ``--b64-entropy-score`` should divide the provided value by 0.06 to
  obtain the equivalent ``--entropy-sensitivity`` setting
* Users of ``--hex-entropy-score`` should divide the provided value by 0.04 to
  obtain the equivalent ``--entropy-sensitivity`` setting

Users who require different base64 and hexadecimal sensitivities should open an
issue that explains their use case.

.. _TOML: https://toml.io/
.. _array of tables: https://toml.io/en/v1.0.0#array-of-tables
.. _pygit2: https://pygit2.readthedocs.io/en/latest/
.. _GitPython: https://gitpython.readthedocs.io/en/stable/
.. _#267: https://github.com/godaddy/tartufo/issues/267
