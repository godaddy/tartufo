# Contributing

Everyone is welcome to contribute to GoDaddy's Open Source Software. Contributing doesn't just mean submitting pull
requests. You can also get involved by reporting/triaging bugs, or participating in discussions on the evolution of each
project.

No matter how you want to get involved, we ask that you first learn what's expected of anyone who participates in the
project by reading these Contribution Guidelines.

If you have a support question utilize the [Tartufo Mailing list].

## Table of Contents

* [Answering Questions](#answering-questions)
* [Reporting Bugs](#reporting-bugs)
* [Triaging bugs or contributing code](#triaging-bugs-or-contributing-code)
* [Code Review](#code-review)
* [Attribution of Changes](#attribution-of-changes)
* [Writing Code](#writing-code)
  * [Setting Up A Development Environment](#setting-up-a-development-environment)
  * [Code Style](#code-style)
* [Running tests](#running-tests)
* [Contributing as a Maintainer](#contributing-as-a-maintainer)
  * [Issuing a New Release](#issuing-a-new-release)
* [Additional Resources](#additional-resources)

## Answering Questions

One of the most important and immediate ways you can support this project is to answer questions on
[Github][issues] or the [Tartufo Mailing list]. Whether you're helping a newcomer understand a feature or
troubleshooting an edge case with a seasoned developer, your knowledge and experience with Python or security can go a
long way to help others.

## Reporting Bugs

**Do not report potential security vulnerabilities here. Refer to
[our security policy] for more details about the process of reporting security vulnerabilities.**

Before submitting a ticket, please be sure to have a simple replication of the behavior. If the issue is isolated to one
of the dependencies of this project, please create a Github issue in that project. All dependencies are open source
software and can be easily found through [PyPI].

Submit a ticket for your issue, assuming one does not already exist:

* Create it on our [Issue Tracker][issues]
* Clearly describe the issue by following the template layout
  * Make sure to include steps to reproduce the bug.
  * A reproducible (unit) test could be helpful in solving the bug.
  * Describe the environment that (re)produced the problem.

> For a bug to be actionable, it needs to be reproducible. If you or
> contributors can't reproduce the bug, try to figure out why. Please take care
> to stay involved in discussions around solving the problem.

## Triaging bugs or contributing code

If you're triaging a bug, try to reduce it. Once a bug can be reproduced, reduce it to the smallest amount of code
possible. Reasoning about a sample or unit test that reproduces a bug in just a few lines of code is easier than
reasoning about a longer sample.

From a practical perspective, contributions are as simple as:

* Forking the repository on GitHub.
* Making changes to your forked repository.
* When committing, reference your issue (if present) and include a note about the fix.
* If possible, and if applicable, please also add/update unit tests for your changes.
* Push the changes to your fork and submit a pull request to the 'main' branch of the projects' repository.

If you are interested in making a large change and feel unsure about its overall effect, please make sure to first
discuss the change and reach a consensus with core contributors. Then ask about the best way to go about
making the change.

## Code Review

Any open source project relies heavily on code review to improve software quality:

> All significant changes, by all developers, must be reviewed before they are
> committed to the repository. Code reviews are conducted on GitHub through
> comments on pull requests or commits. The developer responsible for a code
> change is also responsible for making all necessary review-related changes.

Sometimes code reviews will take longer than you would hope for, especially for larger features. Here are some accepted
ways to speed up review times for your patches:

* Review other people's changes. If you help out, others will be more willing to do the same for you. Good will is our
  currency.
* Split your change into multiple smaller changes. The smaller your change, the higher the probability that somebody
  will take a quick look at it.

**Note that anyone is welcome to review and give feedback on a change, but only people with commit access to the
repository can approve it.**

## Attribution of Changes

When contributors submit a change to this project, after that change is approved, other developers with commit access
may commit it for the author. When doing so, it is important to retain correct attribution of the contribution.
Generally speaking, Git handles attribution automatically.

## Writing Code

### Setting Up A Development Environment

This project uses [Poetry] to manage its dependencies and do a lot of the heavy lifting. This includes managing
development environments! If you are not familiar with this tool, we highly recommend checking
out [their docs][poetry docs]
to get used to the basic usage.

Now, setting up a development environment is super simple! Additional info if you run into
trouble: [Poetry Environments]

Step 1: [Install Poetry]  
Step 2: Run ``poetry install``  
Step 3: Optionally Run ``poetry shell``

Done!

### Code Style

From [PEP 8 -- Style Guide for Python Code][PEP 8]
> A style guide is about consistency. Consistency with this style guide is important. Consistency within a project is
> more important. Consistency within one module or function is the most important.

To make code formatting easy on developers, and to simplify the conversation around pull request reviews, this project
has adopted the
[black] code formatter. This formatter must be run against any new code written for this project. The advantage is, you
no longer have to think about how your code is styled; it's all handled for you!

To make this easier on you, you can [set up most editors][black-editors] to auto-run `black` for you. We have also set
up a [pre-commit] hook to run automatically on every commit, which is detailed below!

There can be more to code style than, "spaces vs tabs." Styling conventions, best practices, and language developments
can all lead to changes to what is the best code style be followed. When existing code needs changing, or new code is
submitted, questions can then arise as to what style to follow or what best practice takes precedence.

This isn't something that has a hard and fast rule. As a rule of thumb, we ask that contributors take each pull request
as an opportunity to uplift the code they are touching to be in alignment with current recommendations. In an ideal
world, the newest code in the codebase will reflect the best patterns to use, but if there is existing code being
changed it is a balance between keeping style versus adoption of new ones.

There may be occasions when the maintainers of the project may ask a contributor to adopt a newer style or pattern to
aid in uplifting the project as a whole and to help our community become better software developers.

We understand that time or other constraints may mean such requests are not able to be part of the pull request. In such
cases please engage in communication with the maintainers. We would much rather have a pull request of a feature that
aligns with the current codebase styles and patterns; and add an issue to the backlog to refactor with new patterns when
bandwidth permits; than to have you not contribute a pull request.

## Running tests

This project support multiple Python versions. Thus, we ask that you use the
[tox] tool to test against them. In conjunction with poetry, this will look something like:

```sh
$ poetry run tox
.package recreate: /home/username/tartufo/.tox/.package
.package installdeps: poetry>=0.12
...
  py35: commands succeeded
  py36: commands succeeded
  py37: commands succeeded
  py38: commands succeeded
  pypy3: ignored failed command
  black: commands succeeded
  mypy: commands succeeded
  pylint: commands succeeded
  vulture: commands succeeded
  docs: commands succeeded
  congratulations :)
$
```

If you do not have all the supported Python versions, that's perfectly okay. They will all be tested against by our CI
process. But keep in mind that this may delay the adoption of your contribution, if those tests don't all pass.

Finally, this project uses multiple [pre-commit] hooks to help ensure our code quality. If you have followed the
instructions above for setting up your virtual environment, `pre-commit` will already be installed, and you only need to
run the following:

```sh
$ pre-commit install --install-hooks
pre-commit installed at .git/hooks/pre-commit
$
```

Now, any time you make a new commit to the repository, you will see something like the following:

```sh
Tartufo..................................................................Passed
mypy.....................................................................Passed
black....................................................................Passed
pylint...................................................................Passed
```

## Contributing as a Maintainer

On top of all our lovely contributors, we have a core group of people who act as maintainers of the project. They are
the ones who are the gatekeepers, and make sure that issues are addressed, PRs are merged, and new releases issued, all
while ensuring a high bar of quality for the code and the project.

### Issuing a New Release

This process is thankfully mostly automated. There are, however, a handful of manual steps that must be taken to kick
off that automation. It is all built this way to help ensure that issuing a release is a very conscious decision,
requiring peer review, and cannot easily happen accidentally. The steps involved currently are:

* Create a new branch locally for the release, for example:

  ```console
  > git checkout -b releases/v2.1.0
  ```

* Tell Poetry to [bump the version]:

  ```console
  > poetry version minor
  Bumping version from 2.0.1 to 2.1.0
  ```

  * Note: All this is doing, is updating the version number in the
    `pyproject.toml`. You can totally do this manually. This command just might be a bit quicker. And it's nice to
    have a command to do it for you. Yay automation!
* Update the CHANGELOG with the appropriate new version number and release date.
* Create a pull request for these changes, and get it approved!
* Once your PR has been merged, the final piece is to actually create the new release.

    1. Go to the `tartufo` [releases page] and click on `Draft a new release`.
    2. Enter an appropriate tag version (in this example, `v2.1.0`).
    3. Title the release. Generally these would just be in the form
       `Version 2.1.0`. (Not very creative, I know. But predictable!)
    4. Copy-paste the CHANGELOG entries for this new version into the description.
    5. Click `Publish release`!

Congratulations, you've just issued a new release for `tartufo`. The automation will take care of the rest! 🎉

## Additional Resources

* [General GitHub Documentation](https://help.github.com/)
* [GitHub Pull Request documentation](https://help.github.com/send-pull-requests/)

[black]: https://github.com/psf/black
[black-editors]: https://black.readthedocs.io/en/stable/integrations/editors.html
[bump the version]: https://python-poetry.org/docs/cli/#version
[issues]: https://github.com/godaddy/tartufo/issues
[Install Poetry]: https://python-poetry.org/docs/#installation
[Poetry Environments]: https://python-poetry.org/docs/managing-environments/
[our security policy]: https://github.com/godaddy/tartufo/security/policy
[PEP 8]: https://www.python.org/dev/peps/pep-0008/#a-foolish-consistency-is-the-hobgoblin-of-little-minds
[Poetry]: https://python-poetry.org/
[poetry docs]: https://python-poetry.org/docs/
[pre-commit]: https://pre-commit.com/
[PyPI]: http://pypi.org/
[releases page]: https://github.com/godaddy/tartufo/releases
[tox]: https://tox.readthedocs.io/en/latest/
[Tartufo Mailing list]: https://groups.google.com/g/tartufo-secrets-scanner
