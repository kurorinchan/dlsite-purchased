import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory, NamedTemporaryFile
import unittest
from unittest import mock
from unittest.mock import MagicMock, call, patch
import downloader
import manager


class ManagerTest(unittest.TestCase):
    def testRemoveFilesInDir(self):
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
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
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
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
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
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
        # On non-Windows platforms, `NamedTemporaryFile()` can be used here,
        # but it won't work on Windows.
        # This is because the file gets opened on call to NamedTemporaryFile(),
        # but manager.LoadSessionFromFile also opens it. Behavior for double
        # open is undefined. So a temporary directory is created instead.
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            session_file = Path(tmpdir) / "session.pkl"
            session_file.touch()  # Ensure the file exists before LoadSessionFromFile is called.
            mock_session_create.return_value = mock_session
            result = manager.LoadSessionFromFile(session_file)
            self.assertEquals(result, mock_session)

        mock_session_create.assert_called()
        mock_session.cookies.update.assert_called()

    def testSaveSession(self):
        session_mock = MagicMock()
        session_mock.cookies = "any value"
        with TemporaryDirectory() as config_dir:
            manager.SaveMainSessionToConfigDir(Path(config_dir), session_mock)

    @patch("login.Login")
    def testCreateLoginSession(self, mock_login):
        mock_login.return_value = MagicMock()
        mock_login.return_value.cookies = "any value"
        with TemporaryDirectory(ignore_cleanup_errors=True) as config_dir:
            os.chdir(config_dir)
            manager._ConfigSubcommand(
                Path(config_dir),
                None,
                "fakeusername",
                "fakepass",
                True,
            )
            self.assertTrue((Path(config_dir) / "main.session").exists())
            cred_file = Path(config_dir) / "login_credential"
            self.assertTrue(cred_file.exists())
            with open(cred_file, "rb") as f:
                raw_cred: manager.RawCredential = pickle.load(f)
                self.assertEqual(raw_cred.username, "fakeusername")
                self.assertEqual(raw_cred.password, "fakepass")

        mock_login.assert_called_once_with("fakeusername", "fakepass")

    def testCreateLoginSessionOnlyUsername(self):
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            self.assertFalse(
                manager._ConfigSubcommand(
                    Path(tmpdir),
                    None,
                    "fakeusername",
                    "",
                    True,
                )
            )

    def testCreateLoginSessionOnlyPassword(self):
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            self.assertFalse(
                manager._ConfigSubcommand(
                    Path(tmpdir),
                    None,
                    "",
                    "fakepass",
                    True,
                )
            )

    @patch("downloader.Downloader.DownloadTo")
    def testDownloadUnauthorized(self, download_to_mock: MagicMock):
        download_to_mock.side_effect = downloader.HttpUnauthorizeException(MagicMock())
        with TemporaryDirectory(ignore_cleanup_errors=True) as management_dir:
            with TemporaryDirectory(ignore_cleanup_errors=True) as config_dir:
                mock_session = MagicMock()
                with self.assertRaises(downloader.HttpUnauthorizeException):
                    manager.Download(
                        mock_session,
                        Path(config_dir),
                        str(management_dir),
                        set(["any_item"]),
                        False,
                        False,
                    )

    @patch("manager.SaveMainSessionToConfigDir")
    @patch("manager._ReloginWithCredential")
    @patch("downloader.Downloader.DownloadTo")
    def testDownloadRetryOnRelogin(
        self,
        download_to_mock: MagicMock,
        relogin_mock: MagicMock,
        save_session_mock: MagicMock,
    ):
        """Verify that relogin retries the same item.

        An exception is raised on the first download, then the mock should
        behave normally (as if it has successfully downloaded).
        Retry should happen with the item that caused an exception.
        """
        num_called = 0

        def download_mock_sideeffect(any, arg):
            """Raise exception on first call then behave normally."""
            nonlocal num_called
            num_called += 1
            if num_called == 1:
                raise downloader.HttpUnauthorizeException(MagicMock())
            return MagicMock()

        download_to_mock.side_effect = download_mock_sideeffect
        relogin_mock.return_value = MagicMock()

        with TemporaryDirectory() as management_dir:
            with TemporaryDirectory() as config_dir:
                mock_session = MagicMock()
                manager.Download(
                    mock_session,
                    Path(config_dir),
                    str(management_dir),
                    set(["item1"]),
                    False,
                    False,
                )

        self.assertEqual(download_to_mock.call_count, 2)
        download_to_mock.assert_has_calls(
            [call("item1", mock.ANY), call("item1", mock.ANY)]
        )

    @patch("login.Login")
    def testRelogin(self, login_mock: MagicMock):
        with TemporaryDirectory(ignore_cleanup_errors=True) as config_dir:
            with open(
                Path(config_dir) / manager._RAW_LOGIN_CREDENTAIL_FILE, "wb"
            ) as test_cred_file:
                cred = manager.RawCredential(username="any", password="string")
                pickle.dump(cred, test_cred_file)

            manager._ReloginWithCredential(Path(config_dir))

        login_mock.assert_called_once_with("any", "string")

    @patch("login.Login")
    def testReloginNoCredFile(self, login_mock: MagicMock):
        with TemporaryDirectory(ignore_cleanup_errors=True) as config_dir:
            self.assertIsNone(manager._ReloginWithCredential(Path(config_dir)))

        login_mock.assert_not_called()

    @patch("manager.SaveMainSessionToConfigDir")
    @patch("manager.LoadSessionFromFile")
    def testSessionContextManager(
        self, load_mock: MagicMock, save_session_mock: MagicMock
    ):
        with TemporaryDirectory(ignore_cleanup_errors=True) as config_dir:
            with manager.UsingMainSession(Path(config_dir)) as s:
                pass
        load_mock.assert_called_once()
        save_session_mock.assert_called_once()
