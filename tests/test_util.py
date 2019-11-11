import unittest

from tartufo import util

try:
    from unittest import mock
except ImportError:
    import mock  # type: ignore


class GitTests(unittest.TestCase):
    """Test that we interact with git properly.

    We will not test that we get the eventual result desired (e.g. a fully
    cloned repo) for a couple of reasons.

      1. That functionality is not the responsibility of our package;
         it is the responsibility of the `git` package.
      2. Full tests such as those would require an internet connection,
         and rely on the functionality of external systems. Unit tests
         should only ever rely on the code which is being directly tested.
    """

    @mock.patch("tartufo.util.Repo.clone_from")
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_tartufo_clones_git_repo_into_temp_dir(self, mock_mkdtemp, mock_clone):
        util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        mock_clone.assert_called_once_with(
            "https://github.com/godaddy/tartufo.git",
            mock_mkdtemp.return_value
        )

    @mock.patch("tartufo.util.Repo.clone_from", new=mock.MagicMock())
    @mock.patch("tartufo.util.tempfile.mkdtemp")
    def test_clone_git_repo_returns_path_to_clone(self, mock_mkdtemp):
        repo_path = util.clone_git_repo("https://github.com/godaddy/tartufo.git")
        self.assertEqual(repo_path, mock_mkdtemp.return_value)
