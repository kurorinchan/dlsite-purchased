import os
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
import unittest
from unittest.mock import MagicMock, patch
import downloader
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


    @patch("pickle.load")
    @patch("requests.Session")
    def testLoadSession(self, mock_session_create, mock_load):
        mock_session = MagicMock()
        with NamedTemporaryFile() as f:
            mock_session_create.return_value = mock_session
            result = manager.LoadSession(Path(f.name))
            self.assertEquals(result, mock_session)

        mock_session_create.assert_called()
        mock_session.cookies.update.assert_called()

    def testSaveSession(self):
        session_mock = MagicMock()
        session_mock.cookies = "any value"
        with NamedTemporaryFile() as f:
            manager.SaveSession(Path(f.name), session_mock)


    @patch("login.Login")
    def testCreateLoginSession(self, mock_login):
        mock_login.return_value = MagicMock()
        mock_login.return_value.cookies = "any value"
        with TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            manager._ConfigSubcommand(
                Path(tmpdir), None, "fakeusername", "fakepass", True,
            )
            self.assertTrue((Path(tmpdir) / "main.session").exists())
            self.assertTrue((Path(tmpdir) / "login_credential").exists())

        mock_login.assert_called_once_with("fakeusername", "fakepass")

    def testCreateLoginSessionOnlyUsername(self):
        with TemporaryDirectory() as tmpdir:
            self.assertFalse(
                manager._ConfigSubcommand(
                    Path(tmpdir), None, "fakeusername", "", True,
                ))

    def testCreateLoginSessionOnlyPassword(self):
        with TemporaryDirectory() as tmpdir:
            self.assertFalse(
                manager._ConfigSubcommand(
                    Path(tmpdir), None, "", "fakepass", True,
                ))

    @patch("downloader.Downloader.DownloadTo")
    def testDownloadUnauthorized(self, download_to_mock: MagicMock):
        download_to_mock.side_effect = downloader.HttpUnauthorizeException(MagicMock())
        with TemporaryDirectory() as tmpdir:
            mock_session = MagicMock()
            with self.assertRaises(downloader.HttpUnauthorizeException):
                manager.Download(mock_session, str(tmpdir), set(["any_item"]), False, False)