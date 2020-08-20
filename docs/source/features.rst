Features
========

Regex Checking
--------------

`tartufo` can scan for a pre-built list of known signatures for things such as
SSH keys, EC2 credentials, etc. These scans are activated by use of the
``--regex`` flag on the command line. They will be reported with an issue type
of ``Regular Expression Match``, and the issue detail will be the name of the
regular expression which was matched.

Customizing
+++++++++++

Additional rules can be specified in a JSON file, pointed to on the command
line with the ``--rules`` argument. The file should be in the following format:

.. code-block:: json

   {
       "RSA private key": "-----BEGIN EC PRIVATE KEY-----"
   }

Things like subdomain enumeration, s3 bucket detection, and other useful
regexes highly custom to the situation can be added.

If you would like to deactivate the default regex rules, using only your custom
rule set, you can use the ``--no-default-regexes`` flag.

Feel free to also contribute high signal regexes upstream that you think will
benefit the community. Things like Azure keys, Twilio keys, Google Compute
keys, are welcome, provided a high signal regex can be constructed.

tartufo's base rule set sources from <https://github.com/dxa4481/truffleHogRegexes/blob/master/truffleHogRegexes/regexes.json>

High Entropy Checking
---------------------

`tartufo` calculates the `Shannon entropy`_ of each commit, finding strings
which appear to be generated from a stochastic source. In short, it looks for
pieces of data which look random, as these are likely to be things such as
cryptographic keys. These scans are activated by usage of the ``--entropy``
command line flag.

Limiting Scans by Signatures
----------------------------

.. versionadded:: 2.0.0

Every time an issue is found during a scan, `tartufo` will generate a
"signature" for that issue. This is a stable hash generated from the filename
and the actual string that was identified as being an issue.

For example, you might see the following header in the output for an issue:

.. image:: _static/img/issue-signature.png

Looking at this information, it's clear that this issue was found in a test
file, and it's probably okay. Of course, you will want to look at the actual
body of what was found and determine that for yourself. But let's say that this
really is okay, and we want tell `tartufo` to ignore this issue in future scans.
To do this, you can either specify it on the command line...

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
----------------------

With the ``--include-paths`` and ``--exclude-paths`` options, it is also
possible to limit scanning to a subset of objects in the Git history by
defining regular expressions (one per line) in a file to match the targeted
object paths. To illustrate, see the example include and exclude files below:

.. code-block:: ini
   :caption: include-patterns.txt

   src/
   # lines beginning with "#" are treated as comments and are ignored
   gradle/
   # regexes must match the entire path, but can use python's regex syntax for
   # case-insensitive matching and other advanced options
   (?i).*\.(properties|conf|ini|txt|y(a)?ml)$
   (.*/)?id_[rd]sa$

.. code-block:: ini
   :caption: exclude-patterns.txt

   (.*/)?\.classpath$
   .*\.jmx$
   (.*/)?test/(.*/)?resources/

These filter files could then be applied by:

.. code-block:: sh

   tartufo --include-paths include-patterns.txt --exclude-paths exclude-patterns.txt file://path/to/my/repo.git

With these filters, issues found in files in the root-level ``src`` directory
would be reported, unless they had the ``.classpath`` or ``.jmx`` extension, or
if they were found in the ``src/test/dev/resources/`` directory, for example.
Additional usage information is provided when calling ``tartufo`` with the
``-h`` or ``--help`` options.

These features help cut down on noise, and makes the tool easier to shove into
a devops pipeline.


.. _Shannon entropy: https://en.wiktionary.org/wiki/Shannon_entropy
