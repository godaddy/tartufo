============
Installation
============

You can install ``tartufo`` in the usual ways you would for a Python Package, or using ``docker`` to pull the latest ``tartufo`` docker image from Docker Hub.

Installation with ``pip``:

   .. code-block:: console

      $ pip install tartufo

Installation with ``docker``:

   .. code-block:: console

      $ docker pull godaddy/tartufo

If you would like to install the latest in-development version of ``tartufo``,
this can also be done with ``pip``.

   .. code-block:: console

      $ pip install -e git+ssh://git@github.com/godaddy/tartufo.git#egg=tartufo

.. note::

   Installing the in-development version is NOT guaranteed to be stable. You will get the
   latest set of features and fixes, but we CAN NOT guarantee that it will
   always work.

Checking the installation
-------------------------

When ``tartufo`` is installed, it inserts an eponymous command into your path.
So if everything went well, the easiest way to verify your installation is to
simply run that command:

Checking the ``pip`` installation:

   .. code-block:: console

      $ tartufo --help

Checking the ``docker`` installation:

   .. code-block:: console

      $ docker run godaddy/tartufo --help
