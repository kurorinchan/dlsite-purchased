#!/usr/bin/env python3


from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

import dlsite_extract


class ExtractTest(unittest.TestCase):
    def testPopOneWorkNormal(self):
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ1234.zip",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]

            archives, rest = dlsite_extract._PopOneWork(
                list(map(lambda f: f.name, files))
            )
            self.assertEqual(archives, ["RJ1234.zip"])
            self.assertEqual(rest, ["RJ4321.part1.exe", "RJ4321.part2.rar"])

            archives, rest = dlsite_extract._PopOneWork(rest)
            self.assertEqual(archives, ["RJ4321.part1.exe", "RJ4321.part2.rar"])
            self.assertEqual(len(rest), 0)

    def testPopOneWorkPartsOnly(self):
        with TemporaryDirectory() as dir_with_archives:
            # Preparation. Create a bunch of files for testing.
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ1234.part1.exe",
                dir_with_archives / "RJ1234.part2.rar",
                dir_with_archives / "RJ1234.part3.rar",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]

            archives, rest = dlsite_extract._PopOneWork(
                list(map(lambda f: f.name, files))
            )
            self.assertEqual(
                archives,
                [
                    "RJ1234.part1.exe",
                    "RJ1234.part2.rar",
                    "RJ1234.part3.rar",
                ],
            )
            self.assertEqual(rest, ["RJ4321.part1.exe", "RJ4321.part2.rar"])

            archives, rest = dlsite_extract._PopOneWork(rest)
            self.assertEqual(archives, ["RJ4321.part1.exe", "RJ4321.part2.rar"])
            self.assertEqual(len(rest), 0)

    def testPopOneWorkNoMatch(self):
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "somename.txt",
                dir_with_archives / "RJ1234.part1.exe",
                dir_with_archives / "RJ1234.part2.rar",
                dir_with_archives / "RJ1234.part3.rar",
            ]

            archives, rest = dlsite_extract._PopOneWork(
                list(map(lambda f: f.name, files))
            )
            self.assertEqual(len(archives), 0)
            self.assertEqual(
                rest,
                [
                    # The first file that does not match the pattern should
                    # be ignored.
                    "RJ1234.part1.exe",
                    "RJ1234.part2.rar",
                    "RJ1234.part3.rar",
                ],
            )

    @patch("dlsite_extract._GetWorkName")
    def testCreateArchiveDirs(self, get_work_name_mock):
        get_work_name_mock.return_value = ""
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ1234.zip",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]
            for f in files:
                f.touch()

            directories = dlsite_extract.CreateArchivesDirs(dir_with_archives)
            self.assertEqual(
                directories,
                set(
                    [
                        dir_with_archives / "RJ1234",
                        dir_with_archives / "RJ4321",
                    ]
                ),
            )

    @patch("dlsite_extract._ExtractZip")
    def testUnarchiveMultiFile(self, extract_mock: MagicMock):
        extract_mock.return_value = True
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]
            for f in files:
                f.touch()

            dlsite_extract.Unarchive(dir_with_archives, False)

        extract_mock.assert_called_once_with(
            dir_with_archives, dir_with_archives / "RJ4321.part1.exe"
        )

    @patch("dlsite_extract._ExtractZip")
    def testUnarchiveMultiFileLotsOfParts(self, extract_mock: MagicMock):
        extract_mock.return_value = True
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
                dir_with_archives / "RJ4321.part3.rar",
                dir_with_archives / "RJ4321.part4.rar",
                dir_with_archives / "RJ4321.part5.rar",
                dir_with_archives / "RJ4321.part6.rar",
                dir_with_archives / "RJ4321.part7.rar",
                dir_with_archives / "RJ4321.part8.rar",
                dir_with_archives / "RJ4321.part9.rar",
                dir_with_archives / "RJ4321.part10.rar",
                # Make sure part1 is passed to extract_mock, not part11.
                dir_with_archives / "RJ4321.part11.rar",
            ]
            for f in files:
                f.touch()

            dlsite_extract.Unarchive(dir_with_archives, False)

        extract_mock.assert_called_once_with(
            dir_with_archives, dir_with_archives / "RJ4321.part1.exe"
        )

    @patch("dlsite_extract._ExtractZip")
    def testUnarchiveSkipHiddenFiles(self, extract_mock: MagicMock):
        """Hidden files should be skipped.

        Even if the hidden file contains part1, it should not be passed to
        the extract function.
        """
        extract_mock.return_value = True
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / ".part1.hiddenfile",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]
            for f in files:
                f.touch()

            dlsite_extract.Unarchive(dir_with_archives, False)

        extract_mock.assert_called_once_with(
            dir_with_archives, dir_with_archives / "RJ4321.part1.exe"
        )

    @patch("dlsite_extract._ExtractZip")
    def testUnarchiveNoFiles(self, extract_mock: MagicMock):
        extract_mock.return_value = True
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            dlsite_extract.Unarchive(dir_with_archives, False)

        self.assertEqual(extract_mock.call_count, 0)
