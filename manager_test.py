import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
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
