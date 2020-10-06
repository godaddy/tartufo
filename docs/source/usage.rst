=====
Usage
=====

While ``tartufo`` started its life with one primary mode of operation, scanning
the history of a git repository, it has grown other time to have a number of
additional uses and modes of operation. These are all invoked via different
sub-commands of ``tartufo``.

Git Repository History Scan
---------------------------

This is the "classic" use case for ``tartufo``: Scanning the history of a git
repository. There are two ways to invoke this functionality, depending if you
are scanning a repository which you already have cloned locally, or one on a
remote system.

Scanning a Local Repository
+++++++++++++++++++++++++++

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
++++++++++++++++++++++++++++

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


Pre-commit Hook
---------------

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
++++++++++++

To set up a pre-commit hook for ``tartufo`` by hand, you can place the following
in a ``.git/hooks/pre-commit`` file inside your local repository clone:

Executing tartufo Directly
**************************

.. code-block:: sh

   #!/bin/sh

   # Redirect output to stderr.
   exec 1>&2

   # Check for suspicious content.
   tartufo --regex --entropy pre-commit

Or, Using Docker
****************

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
+++++++++++++++++++++++++++

If you want a slightly more automated approach which can be more easily shared
to ensure a unified setup across all developer's systems, you can use the
wonderful `pre-commit`_ tool.

Add a ``.pre-commit-config.yaml`` file to your repository. You can use the
following example to get you started:

.. code-block:: yaml

   - repo: https://github.com/godaddy/tartufo
     rev: master
     hooks:
     - id: tartufo

.. warning::

   You probably don't actually want to use the `master` rev. This is the active
   development branch for this project, and can not be guaranteed stable. Your
   best bet would be to choose the latest version, currently |version|.

That's it! Now your contributors only need to `install pre-commit`_, and then
run ``pre-commit install --install-hooks``, and ``tartufo`` will automatically
be run as a pre-commit hook.

:doc:`examplecleanup`

.. _install pre-commit: https://pre-commit.com/#install
.. _pre-commit: https://pre-commit.com/
