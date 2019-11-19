# Contributing

Everyone is welcome to contribute to GoDaddy's Open Source Software.
Contributing doesn’t just mean submitting pull requests. To get involved you can
report or triage bugs and participate in discussions on the evolution of each
project.

No matter how you want to get involved, we ask that you first learn what’s
expected of anyone who participates in the project by reading the Contribution
Guidelines.

**Please Note:** GitHub is for bug reports and contributions primarily - if you
have a support question head over to [GoDaddy's Open Source Software Slack][slack].

## Answering Questions

One of the most important and immediate ways you can support this project is to
answer questions on [Slack][slack] or [Github][issues]. Whether you’re helping a
newcomer understand a feature or troubleshooting an edge case with a seasoned
developer, your knowledge and experience with Python or security can go a long
way to help others.

## Reporting Bugs

**Do not report potential security vulnerabilities here. Refer to
[SECURITY.md](./SECURITY.md) for more details about the process of reporting
security vulnerabilities.**

Before submitting a ticket, please be sure to have a simple replication of the
behavior. If the issue is isolated to one of the dependencies of this project,
please create a Github issue in that project. All dependencies are open source
software and can be easily found through [PyPI].

Submit a ticket for your issue, assuming one does not already exist:

- Create it on our [Issue Tracker][issues]
- Clearly describe the issue by following the template layout
  - Make sure to include steps to reproduce the bug.
  - A reproducible (unit) test could be helpful in solving the bug.
  - Describe the environment that (re)produced the problem.

> For a bug to be actionable, it needs to be reproducible. If you or
> contributors can’t reproduce the bug, try to figure out why. Please take care
> to stay involved in discussions around solving the problem.

## Triaging bugs or contributing code

If you're triaging a bug, try to reduce it. Once a bug can be reproduced, reduce
it to the smallest amount of code possible. Reasoning about a sample or unit
test that reproduces a bug in just a few lines of code is easier than reasoning
about a longer sample.

From a practical perspective, contributions are as simple as:

- Forking the repository on GitHub.
- Making changes to your forked repository.
- When committing, reference your issue (if present) and include a note about
  the fix.
- If possible, and if applicable, please also add/update unit tests for your
  changes.
- Push the changes to your fork and submit a pull request to the 'master' branch
  of the projects' repository.

If you are interested in making a large change and feel unsure about its overall
effect, please make sure to first discuss the change and reach a consensus with
core contributors through [slack]. Then ask about the best way to go about
making the change.

## Code Review

Any open source project relies heavily on code review to improve software
quality:

> All significant changes, by all developers, must be reviewed before they are
> committed to the repository. Code reviews are conducted on GitHub through
> comments on pull requests or commits. The developer responsible for a code
> change is also responsible for making all necessary review-related changes.

Sometimes code reviews will take longer than you would hope for, especially for
larger features. Here are some accepted ways to speed up review times for your
patches:

- Review other people’s changes. If you help out, others will be more willing to
  do the same for you. Good will is our currency.
- Split your change into multiple smaller changes. The smaller your change, the
  higher the probability that somebody will take a quick look at it.
- Ping the change on [slack]. If it is urgent, provide reasons why it is
  important to get this change landed. Remember that you’re asking for valuable
  time from other professional developers.

**Note that anyone is welcome to review and give feedback on a change, but only
people with commit access to the repository can approve it.**

## Attribution of Changes

When contributors submit a change to this project, after that change is approved,
other developers with commit access may commit it for the author. When doing so,
it is important to retain correct attribution of the contribution. Generally
speaking, Git handles attribution automatically.

## Writing Code

### Setting Up A Development Environment

As a general best practice, you should work on this project in an isolated
Python virtual environment. The following set of commands will set that up for
you:

```sh
> python -m venv .venv
> source .venv/bin/activate
> pip install -e .[tests]
```

### Code Style

To make code formatting easy on developers, and to simplify the conversation
around pull request reviews, this project has adopted the
[black] code formatter. This formatter must be run against any new code written
for this project. The advantage is, you no longer have to think about how your
code is styled; it's all handled for you!

To make this easier on you, you can [set up most editors][black-editors] to
auto-run `black` for you. We have also set up a [pre-commit] hook to run
automatically on every commit, which is detailed below!

## Running tests

This project support multiple Python versions in this project. Thus, we ask
that you use the `tox` tool to test against them. If you do not have all of the
supported Python versions, that's perfectly okay. They will all be tested
against by our CI process. But keep in mind that this may delay the adoption
of your contribution, if those tests don't all pass.

Finally, this project uses multiple [pre-commit] hooks to help ensure our code
quality. If you have followed the instructions above for setting up your virtual
environment, `pre-commit` will already be installed, and you only need to run
the following:

```sh
> pre-commit install --install-hooks
```

Now, any time you make a new commit to the repository, you will see something
like the following:

```sh
Tartufo..................................................................Passed
mypy.....................................................................Passed
black....................................................................Passed
pylint...................................................................Passed
```

## Additional Resources

- [General GitHub Documentation](https://help.github.com/)
- [GitHub Pull Request documentation](https://help.github.com/send-pull-requests/)

[black]: https://github.com/psf/black
[black-editors]: https://github.com/psf/black#editor-integration
[issues]: https://github.com/godaddy/tartufo/issues
[PEP 8]: https://www.python.org/dev/peps/pep-0008/
[pre-commit]: https://pre-commit.com/
[PyPI]: http://pypi.org/
[slack]: https://godaddy-oss.slack.com/
