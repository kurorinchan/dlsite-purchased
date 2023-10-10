#!/usr/bin/env python3


from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import dlsite_extract


class ExtractTest(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def testPopOneWorkNormal(self):
        with TemporaryDirectory() as dir_with_archives:
            # Preparation. Create a bunch of files for testing.
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ1234.zip",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]

            # The function takes file names only.
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

            # The function takes file names only.
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
            # Preparation. Create a bunch of files for testing.
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "somename.txt",
                dir_with_archives / "RJ1234.part1.exe",
                dir_with_archives / "RJ1234.part2.rar",
                dir_with_archives / "RJ1234.part3.rar",
            ]

            # The function takes file names only.
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
            # Preparation. Create a bunch of files for testing.
            dir_with_archives = Path(dir_with_archives)
            files = [
                dir_with_archives / "RJ1234.zip",
                dir_with_archives / "RJ4321.part1.exe",
                dir_with_archives / "RJ4321.part2.rar",
            ]
            for f in files:
                f.touch()

            directories = dlsite_extract.CreateArchivesDirs(str(dir_with_archives))
            self.assertEqual(
                directories,
                set(
                    [
                        dir_with_archives / "RJ1234",
                        dir_with_archives / "RJ4321",
                    ]
                ),
            )
