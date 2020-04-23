
Usage
=====

History Scan
------------

By default, `tartufo` will scan the entire history of a git repo. The repo to
be scanned can be specified in one of two ways. The first, default behavior, is
by passing a git URL to `tartufo`. For example:

.. code-block:: sh

   $ tartufo https://github.com/godaddy/tartufo.git


For ``docker``:

.. code-block:: sh
   
   $ docker run --rm godaddy/tartufo https://github.com/godaddy/tartufo.git
   
When used this way, `tartufo` will clone the repository to a temporary
directory, scan the local clone, and then delete it.

Alternatively, if you already have a local clone, you can scan that directly
without the need for the temporary clone:

.. code-block:: sh

   $ tartufo --repo-path /path/to/my/repo

For ``docker``, mount the local clone to the ``/git`` folder in the docker image:

.. code-block:: sh

   $ docker run --rm -v "/path/to/my/repo:/git" godaddy/tartufo 

When scanning private repositories, the ``docker`` runtime needs to have access to SSH keys for authorization. 
Make sure ``ssh-agent`` is running on your host machine and has the key added. (Verify using ``ssh-add -L`` on host machine).

For Docker for Linux, mount the location of ``SSH_AUTH_SOCK`` to a location in the docker container, and point the environment variable ``SSH_AUTH_SOCK`` to the same location:

.. code-block:: sh
    
    $ docker run --rm -v "/path/to/my/repo:/git" -v $SSH_AUTH_SOCK:/agent -e SSH_AUTH_SOCK=/agent godaddy/tartufo


If using Docker Desktop for Mac, use ``/run/host-services/ssh-auth.sock`` both as source and target, and point the environment variable ``SSH_AUTH_SOCK`` to the same location:

.. code-block:: sh
    
    $ docker run --rm -v "/path/to/my/repo:/git" -v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock -e SSH_AUTH_SOCK="/run/host-services/ssh-auth.sock" godaddy/tartufo


Pre-commit
----------

The ``--pre-commit`` flag instructs tartufo to scan staged, uncommitted changes
in a local repository. The repository location can be specified using
``--repo-path``, but it is legal to not supply a location; in this case, the
caller's current working directory is assumed to be somewhere within the local
clone's tree and the repository root is determined automatically.

The following example demonstrates how tartufo can be used in ``.git/hooks/pre-commit`` to verify that secrets
will not be committed to a git repository in error:

.. code-block:: sh

   #!/bin/sh

   # Redirect output to stderr.
   exec 1>&2

   # Check for suspicious content.
   tartufo --pre-commit --regex --entropy

Git will execute tartufo before committing any content. If problematic changes
are detected, they are reported by tartufo and git aborts the commit process.
Only when tartufo returns a success status (indicating no potential secrets
were discovered) will git commit the staged changes.

Note that it is always possible, although not recommended, to bypass the
pre-commit hook by using ``git commit --no-verify``.

If you would like to automate these hooks, you can use either the ``Python`` or ``Docker`` approach to setting up tartufo as a pre-commit hook

Python pre-commit hook
++++++++++++++++++++++

Add a ``.pre-commit-config.yaml`` file to your repository. You can copy and paste the following to get you started:

.. code-block:: yaml

   - repo: https://github.com/godaddy/tartufo
     rev: master
     hooks:
     - id: tartufo

That's it! Now your contributors only need to run ``pre-commit install
--install-hooks``, and `tartufo` will automatically be run as a pre-commit hook.

.. warning::

   You probably don't actually want to use the `master` rev. This is the active
   development branch for this project, and can not be guaranteed stable. Your
   best bet would be to choose the latest version, currently |version|.
   
Docker pre-commit hook
++++++++++++++++++++++

Use the docker image as pre-commit hook by adding the docker run command to ``.git/hooks/pre-commit``:

.. code-block:: sh

    docker pull godaddy/tartufo
    cat <<EOF > .git/hooks/pre-commit
    docker run -t --rm -v "$PWD:/git" godaddy/tartufo --pre-commit
    EOF


Temporary File Cleanup
----------------------

`tartufo` stores the results in temporary files, which are left on disk by
default, to allow inspection if problems are found. To automatically delete
these files when tartufo completes, specify the ``--cleanup`` flag:

.. code-block:: sh

   tartufo --cleanup


Would you like to know more? See :doc:`examplecleanup`.
