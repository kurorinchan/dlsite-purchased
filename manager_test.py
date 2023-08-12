import os
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
import unittest
from unittest.mock import MagicMock, patch
import manager


class ManagerTest(unittest.TestCase):
    def testRemoveFilesInDir(self):
        with TemporaryDirectory() as tmpdir:
            dir_with_items = Path(tmpdir) / "directory_containing_stuff"
            dir_with_items.mkdir()

            # Create files and directories, that should get deleted later in
            # this test.
            with open(dir_with_items / "random file", "w") as f:
                f.write("hello!")

            (dir_with_items / "a_subdirectory 32001230178").mkdir()
            (dir_with_items / "run_remove_from_this_subdir").mkdir()

            os.chdir(dir_with_items / "run_remove_from_this_subdir")

            self.assertNotEquals(len(os.listdir(dir_with_items)), 0)

            manager._RemoveFilesInDir(dir_with_items)

            self.assertTrue(dir_with_items.exists())

            self.assertEquals(len(os.listdir(dir_with_items)), 0)

    # Verify that extract works. Assuming that the managed directory does not
    # already have the same name directory.
    @patch("shutil.move")
    @patch("dlsite_extract.CreateArchivesDirs")
    @patch("dlsite_extract.Unarchive")
    def testExtract(self, mock_unarchive, mock_create_archive_dirs, mock_move):
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            extracted_files_dir = Path(tmpdir) / "some other directory"
            extracted_files_dir.mkdir()

            Path(download_dir / "RJ123").mkdir()
            Path(download_dir / "RJ2786").mkdir()

            mock_create_archive_dirs.return_value = [
                Path(download_dir / "RJ123"),
                Path(download_dir / "RJ2786"),
            ]

            manager.Extract(download_dir, extracted_files_dir, False)

            mock_create_archive_dirs.assert_called()
            mock_unarchive.assert_called()
            mock_move.assert_any_call(Path(download_dir / "RJ123"), extracted_files_dir)

            mock_move.assert_any_call(
                Path(download_dir / "RJ2786"), extracted_files_dir
            )

            self.assertEquals(mock_move.call_count, 2)

    # If the managed directory already has the same name directory as the
    # extracted archive's, then remove it then move.
    @patch("shutil.rmtree")
    @patch("shutil.move")
    @patch("dlsite_extract.CreateArchivesDirs")
    @patch("dlsite_extract.Unarchive")
    def testExtractAlreadyExtracted(
        self, mock_unarchive, mock_create_archive_dirs, mock_move, mock_rmtree
    ):
        with TemporaryDirectory() as tmpdir:
            download_dir = Path(tmpdir) / "downloads"
            download_dir.mkdir()
            extracted_files_dir = Path(tmpdir) / "some other directory"
            extracted_files_dir.mkdir()

            # The destination dir already has the same name directory.
            Path(extracted_files_dir / "RJ123").mkdir()
            Path(download_dir / "RJ123").mkdir()

            mock_create_archive_dirs.return_value = [
                Path(download_dir / "RJ123"),
            ]

            manager.Extract(download_dir, extracted_files_dir, False)

            mock_create_archive_dirs.assert_called()
            mock_unarchive.assert_called()
            mock_rmtree.assert_called_once_with(extracted_files_dir / "RJ123")
            mock_move.assert_called_once_with(
                Path(download_dir / "RJ123"), extracted_files_dir
            )

    @patch("login.Login")
    def testCreateLoggedInSessionWithUsernamePassword(self, mock_login):
        with TemporaryDirectory() as tmpdir:
            manager.CreateLoggedInSession(True, Path(tmpdir) / "sessionfile",
                                          "fakeusername", "fakepass")

        mock_login.assert_called_once_with("fakeusername", "fakepass")

    @patch("pickle.load")
    @patch("requests.Session")
    def testCreateLoggedInSessionUseSavedSession(self,
                                                 mock_session_create, mock_load):
        mock_session = MagicMock()
        with NamedTemporaryFile() as f:
            mock_session_create.return_value = mock_session
            result = manager.CreateLoggedInSession(True, Path(f.name), "", "")
            self.assertEquals(result, mock_session)

        mock_session_create.assert_called()
        mock_session.cookies.update.assert_called()

    @patch("pickle.load")
    @patch("requests.Session")
    def testCreateLoggedInSessionUseSavedSessionNoSaveSession(
            self, mock_session_create, mock_load):
        """This should behave the same as using a session.

        In other words, if a session file is specified, the save_session
        argument should be ignored.
        """
        mock_session = MagicMock()
        with NamedTemporaryFile() as f:
            mock_session_create.return_value = mock_session
            result = manager.CreateLoggedInSession(False, Path(f.name), "", "")
            self.assertEquals(result, mock_session)

        mock_session_create.assert_called()
        mock_session.cookies.update.assert_called()

    def testCreateLoggedInSessionNoSessoin(self):
        with self.assertRaises(SystemExit):
            manager.CreateLoggedInSession(False, None, "", "")

    @patch("login.Login")
    @unittest.skip("Session is not saved if username and pass is used.")
    def testCreateLoggedInSessionSaveSessionButNoPathSpecified(self, mock_login):
        with TemporaryDirectory() as tmpdir:
            # Expect the session to be saved at "tmpdir/session.bin".
            os.chdir(tmpdir)
            manager.CreateLoggedInSession(True, None,
                                          "fakeusername", "fakepass")

        mock_login.assert_called_once_with("fakeusername", "fakepass")
        self.assertTrue((Path(tmpdir) / "session.bin").exists())


    def testCreateLoggedInSessionOnlyUsername(self):
        with self.assertRaises(SystemExit):
            manager.CreateLoggedInSession(False, None, "username", "")

    def testCreateLoggedInSessionOnlyPassword(self):
        with self.assertRaises(SystemExit):
            manager.CreateLoggedInSession(False, None, "", "something")
