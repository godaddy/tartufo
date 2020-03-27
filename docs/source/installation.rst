.. _installation:

Installation
============

You can install ``tartufo`` in the usual ways you would for a Python Package.
The easiest way is with ``pip``.

   .. code-block:: console

      $ pip install tartufo

If you would like to install the latest in-development version of ``tartufo``,
this can also be done with ``pip``.

   .. code-block:: console

      $ pip install -e git+ssh://git@github.com/godaddy/tartufo.git#egg=tartufo

.. note::

   Installing in this way is NOT guaranteed to be stable. You will get the
   latest set of features and fixes, but we CAN NOT guarantee that it will
   always work.

Checking the installation
-------------------------

When ``tartufo`` is installed, it inserts an eponymous command into your path.
So if everything went well, the easiest way to verify your installation is to
simply run that command:

   .. code-block:: console

      $ tartufo --help
