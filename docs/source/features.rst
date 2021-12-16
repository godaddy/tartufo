========
Features
========

Modes of Operation
------------------

While ``tartufo`` started its life with one primary mode of operation, scanning
the history of a git repository, it has grown other time to have a number of
additional uses and modes of operation. These are all invoked via different
sub-commands of ``tartufo``.

Git Repository History Scan
+++++++++++++++++++++++++++

This is the "classic" use case for ``tartufo``: Scanning the history of a git
repository. There are two ways to invoke this functionality, depending if you
are scanning a repository which you already have cloned locally, or one on a
remote system.

Scanning a Local Repository
***************************

.. code-block:: sh

   $ tartufo scan-local-repo /path/to/my/repo

To use ``docker``, mount the local clone to the ``/git`` folder in the docker
image:

.. code-block:: sh

   $ docker run --rm -v "/path/to/my/repo:/git" godaddy/tartufo scan-local-repo /git

.. note::

   If you are using ``podman`` in place of ``docker``, you will need to add the
   ``--privileged`` flag to the ``run`` command, in order to avoid a permission
   denied error.

Scanning a Remote Repository
****************************

.. code-block:: sh

   $ tartufo scan-remote-repo https://github.com/godaddy/tartufo.git

To use ``docker``:

.. code-block:: sh

   $ docker run --rm godaddy/tartufo scan-remote-repo https://github.com/godaddy/tartufo.git

When used this way, `tartufo` will clone the repository to a temporary
directory, scan the local clone, and then delete it.

Accessing Repositories via SSH from Docker
******************************************

When accessing repositories via SSH, the ``docker`` runtime needs to have
access to your SSH keys for authorization. To allow this, make sure
``ssh-agent`` is running on your host machine and has the key added. You can
verify this by running ``ssh-add -L`` on your host machine. You then need to
point Docker at that running SSH agent.

Using Docker for Linux, that will look something like this:

.. code-block:: sh

    $ docker run --rm -v "/path/to/my/repo:/git" \
      -v $SSH_AUTH_SOCK:/agent -e SSH_AUTH_SOCK=/agent \
      godaddy/tartufo scan-local-repo /git


When using Docker Desktop for Mac, use ``/run/host-services/ssh-auth.sock`` as
both source and target, then point the environment variable ``SSH_AUTH_SOCK`` to
this same location:

.. code-block:: sh

    $ docker run --rm -v "/path/to/my/repo:/git" \
      -v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock \
      -e SSH_AUTH_SOCK="/run/host-services/ssh-auth.sock" godaddy/tartufo

Scanning a Folder
+++++++++++++++++++++++++++

Operating in this mode, tartufo scans the files in a local folder, rather than
operating on git commit history. This is ideal for locating secrets in the latest
version of source files, or files not in source control.

.. code-block:: sh

   $ tartufo scan-folder .

.. code-block:: sh

   $ docker run --rm -v "/path/to/my/repo:/git" godaddy/tartufo scan-folder /git

.. note::

   If you are using ``podman`` in place of ``docker``, you will need to add the
   ``--privileged`` flag to the ``run`` command, in order to avoid a permission
   denied error.

   This will scan all files and folders in the specified directory including
   .git and any other files that may not be in source control. Perform a git clean
   or use a fresh clone of the repository before running scanning a folder and add
   ``.git`` to the ``exclude-paths``.

Pre-commit Hook
+++++++++++++++

This mode of operation instructs tartufo to scan staged, uncommitted changes
in a local repository. This is the flip-side of the primary mode of operation.
Instead of checking for secrets you have already checked in, this helps prevent
you from committing new secrets!

When running this sub-command, the caller's current working directory is assumed
to be somewhere within the local clone's tree and the repository root is
determined automatically.

.. note::

   It is always possible, although not recommended, to bypass the pre-commit
   hook by using ``git commit --no-verify``.

Manual Setup
************

To set up a pre-commit hook for ``tartufo`` by hand, you can place the following
in a ``.git/hooks/pre-commit`` file inside your local repository clone:

Executing tartufo Directly
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sh

   #!/bin/sh

   # Redirect output to stderr.
   exec 1>&2

   # Check for suspicious content.
   tartufo --regex --entropy pre-commit

Or, Using Docker
^^^^^^^^^^^^^^^^

.. code-block:: sh

    #!/bin/sh

    # Redirect output to stderr.
    exec 1>&2

    # Check for suspicious content.
    docker run -t --rm -v "$PWD:/git" godaddy/tartufo pre-commit

Git will execute ``tartufo`` before actually committing any of your changes. If
any problems are detected, they are reported by ``tartufo``, and git aborts the
commit process. Only when ``tartufo`` returns a success status (indicating no
potential secrets were discovered) will git commit the staged changes.



Using the "pre-commit" tool
***************************

.. versionadded:: 2.0.0

If you want a slightly more automated approach which can be more easily shared
to ensure a unified setup across all developer's systems, you can use the
wonderful `pre-commit`_ tool.

Add a ``.pre-commit-config.yaml`` file to your repository. You can use the
following example to get you started:

.. code-block:: yaml

   - repo: https://github.com/godaddy/tartufo
     rev: main
     hooks:
     - id: tartufo

.. warning::

   You probably don't actually want to use the `main` rev. This is the active
   development branch for this project, and can not be guaranteed stable. Your
   best bet would be to choose the latest version, currently |version|.

That's it! Now your contributors only need to `install pre-commit`_, and then
run ``pre-commit install --install-hooks``, and ``tartufo`` will automatically
be run as a pre-commit hook.


Scan Types
----------

``tartufo`` offers multiple types of scans, each of which can be optionally
enabled or disabled, while looking through its target for secrets.

Regex Checking
++++++++++++++

``tartufo`` can scan for a pre-built list of known signatures for things such as
SSH keys, EC2 credentials, etc. These scans are activated by use of the
``--regex`` flag on the command line. They will be reported with an issue type
of ``Regular Expression Match``, and the issue detail will be the name of the
regular expression which was matched.

Customizing
***********

Additional rules can be specified as described in the :ref:`rule-patterns`
section of the :doc:`configuration` document.

Things like subdomain enumeration, s3 bucket detection, and other useful
regexes highly custom to the situation can be added.

If you would like to deactivate the default regex rules, using only your custom
rule set, you can use the ``--no-default-regexes`` flag.

Feel free to also contribute high signal regexes upstream that you think will
benefit the community. Things like Azure keys, Twilio keys, Google Compute
keys, are welcome, provided a high signal regex can be constructed.

tartufo's base rule set can be found in the file ``data/default_regexes.json``.

High Entropy Checking
+++++++++++++++++++++

``tartufo`` calculates the `Shannon entropy`_ of each commit, finding strings
which appear to be generated from a stochastic source. In short, it looks for
pieces of data which look random, as these are likely to be things such as
cryptographic keys. These scans are activated by usage of the ``--entropy``
command line flag.

.. _configuring-exclusions:

Scan Limiting (Exclusions)
--------------------------

By its very nature, especially when it comes to high entropy scans, ``tartufo``
can encounter a number of false positives. Whether those are things like links
to git commit hashes, tokens/passwords used for tests, or any other variety of
thing, there needs to be a way to tell ``tartufo`` to ignore those things, and
not report them out as issues. For this reason, we provide multiple methods for
excluding these items.

Excluding Submodule Paths
+++++++++++++++++++++++++

.. versionadded:: 2.7.0

By default, any path in the repository specified as a `submodule`_ will be
excluded from scans. Since these are upstream repositories over which you may
not have direct control, ``tartufo`` will not hold you accountable for the
secrets in those. If you want to include these in your scans, you can specify
the ``--include-submodules`` option.

.. code-block:: sh

    > tartufo ... --include-submodules

Entropy Limiting
++++++++++++++++

.. versionadded:: 2.5.0

If you find that you are getting a high number of false positives from entropy
scanning, you can configure highly granular exclusions to these findings as
described in the :ref:`entropy-exclusion-patterns` section of the
:doc:`configuration` document.

Limiting by Signature
+++++++++++++++++++++

.. versionadded:: 2.0.0

Every time an issue is found during a scan, ``tartufo`` will generate a
"signature" for that issue. This is a stable hash generated from the filename
and the actual string that was identified as being an issue.

For example, you might see the following header in the output for an issue:

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

Limiting Scans by Path
++++++++++++++++++++++

.. versionadded:: 2.5.0

By default ``tartufo`` will scan all objects tracked by Git. You can limit
scanning by either including fewer paths or excluding some of them using
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


Additional usage information is provided when calling ``tartufo`` with the
``-h`` or ``--help`` options.

These features help cut down on noise, and makes the tool easier to shove into
a devops pipeline.

:doc:`examplecleanup`

.. _array of tables: https://toml.io/en/v1.0.0#array-of-tables
.. _install pre-commit: https://pre-commit.com/#install
.. _pre-commit: https://pre-commit.com/
.. _Shannon entropy: https://en.wiktionary.org/wiki/Shannon_entropy
.. _submodule: https://git-scm.com/book/en/v2/Git-Tools-Submodules
