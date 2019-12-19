tartufo
=======

.. image:: https://img.shields.io/travis/godaddy/tartufo
   :alt: Travis (.org)
.. image:: https://img.shields.io/codecov/c/github/godaddy/tartufo
   :alt: Codecov
.. image:: https://img.shields.io/pypi/v/tartufo
   :alt: PyPI
.. image:: https://img.shields.io/pypi/status/tartufo
   :alt: PyPI - Status
.. image:: https://img.shields.io/pypi/pyversions/tartufo
   :alt: PyPI - Python Version
.. image:: https://img.shields.io/pypi/dm/tartufo
   :alt: PyPI - Downloads
.. image:: https://readthedocs.org/projects/tartufo/badge/?version=latest
   :target: https://tartufo.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

`tartufo` searches through git repositories for secrets, digging deep into
commit history and branches. This is effective at finding secrets accidentally
committed. `tartufo` also can be used by git pre-commit scripts to screen
changes for secrets before they are committed to the repository.

Quick start
-----------

Getting started is easy!

#. Install tartufo from the `tartufo page on the Python Package Index`_, or by
   using

   .. code-block:: console

      $ pip install tartufo

   For more detail, see :ref:`installation`.

#. Use ``tartufo`` to scan your repository and find any secrets in its history!

   .. code-block:: console

      # You can scan a remote git repo
      $ tartufo git@github.com:my_user/my_repo.git

      # Or, scan a local clone of a repo!
      $ tartufo --repo-path /path/to/your/git/repo

.. toctree::
   :maxdepth: 1
   :caption: More information

   installation
   usage
   configuration
   changelog


.. _tartufo page on the Python Package Index: https://pypi.python.org/pypi/tartufo
