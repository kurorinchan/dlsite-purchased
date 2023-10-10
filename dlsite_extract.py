#!/usr/bin/env python3

import json
from typing import List, Set, Tuple
import ntpath
import os
import urllib.request
import urllib.error
import subprocess

import argparse
import re
import shutil
import pathlib
import logging


# From stackoverflow
# https://stackoverflow.com/questions/431684/how-do-i-change-directory-cd-in-python
class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, new_path):
        self.new_path = os.path.expanduser(new_path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)


def _GetPage(url):
    """Get webpage text for a work."""
    try:
        request = urllib.request.urlopen(url)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        request = urllib.request.urlopen(url)
    return request.read().decode()


def _GetRjCode(file_name) -> str:
    file_name, ext = os.path.splitext(file_name)
    while ext:
        file_name, ext = os.path.splitext(file_name)
    return file_name


def GetWorkNameFromWorkId(work_id: str) -> str:
    """Get name from ID.

    This uses the JSON API to get the work info from its ID.

    Args:
        work_id (str): Target work ID. This function tries to get the info for
            this ID.

    Returns:
        str: Name of work. Empty string on error.
    """
    try:
        url = f"https://www.dlsite.com/maniax/product/info/ajax?product_id={work_id}"
        raw_json_response = _GetPage(url)
        work_info = json.loads(raw_json_response)
        return work_info[work_id]["work_name"]
    except:
        return ""


def Unarchive(archive_dir: pathlib.Path, keep_archive: bool):
    """Extracts the files in the directory.

    Unarchives the archives in the specified directory. The output is also
    put in the same directory.

    Args:
        archive_dir contains the archives that should be extracted.
        keep_archive specifies whether the archives should be kept after extraction.
    """
    archive_files: List[pathlib.Path] = []
    for file in archive_dir.glob("*"):
        if file.is_file():
            archive_files.append(file)

    if len(archive_files) == 0:
        logging.warning(f"No files found in {archive_dir}")
        return

    # If there are multiple files, then only the one that says 'part1' has to
    # be extracted.
    target_file = archive_files[0]
    if len(archive_files) > 1:
        for file in archive_files:
            if file.name.startswith("."):
                continue

            if "part1." in file.name:
                target_file = file
                break

    if not _ExtractZip(archive_dir, target_file):
        return

    if not keep_archive:
        logging.info(f"Cleaning archive files for {archive_dir}")
        for f in archive_files:
            logging.info(f"Removing {f}.")
            os.remove(f)


def _ExtractZip(archive_dir: pathlib.Path, target_file: pathlib.Path) -> bool:
    """Extracts archive.

    Extracts target_file in archive_dir. target_file is passed to the
    unarchiver. For example, for split rar files, it should be the part1 file.

    Args:
        archive_dir is the directory that contains the archive files.
        target_file is the file path that should be passed to the unarchiver
            program to be extracted.

    Returns:
        True on success, False otherwise.
    """
    with cd(archive_dir):
        # Unar handles unicode encoding correctly.
        cmd = [
            "unar",
            "-f",
            "-o",
            str(archive_dir),
            str(target_file),
        ]
        logging.debug(cmd)
        try:
            subprocess.check_call(cmd, cwd=archive_dir)
        except:
            logging.error(f"Failed to extract {target_file}")
            return False
        else:
            logging.info("Extracted %s", target_file)
            return True


def _PopOneWork(files: List[str]) -> Tuple[List[str], List[str]]:
    """Get one archive from files list

    This will remove at least one file from the files list.

    Args:
      A list of files.

    Returns:
      Returns a list of files for an archive and the rest of the files that
      have not been processed.
      If the first file isn't an archive file, then returns an empty list and
      a list of files that have not yet been processed (TBC it removes the first
      file in list).
    """
    archive_paths = []
    if len(files) == 0:
        return [], []

    f = files[0]
    files.remove(f)
    pattern = re.compile(r"^(RJ\d+)\.")
    match = pattern.search(f)
    if not match:
        return [], files

    if f.endswith(".zip"):
        # Zip file is always single file.
        archive_paths.append(f)
        return archive_paths, files

    if "part" not in f:
        return [], files

    # This is a split archive so put it in archive paths immediately.
    archive_paths.append(f)

    # Split archive.
    # Find all relevant files.
    work_name = match[1]
    for f in files:
        if work_name in f:
            archive_paths.append(f)

    for archive in archive_paths:
        if archive in files:
            files.remove(archive)

    return archive_paths, files


class Archive:
    @classmethod
    def Create(cls, dir: pathlib.Path):
        onlyfiles = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

        # Sometimes there are hidden files. Filter them out.
        onlyfiles = [f for f in onlyfiles if not f.startswith(".")]

        archives = []
        while onlyfiles:
            archive_paths, onlyfiles = _PopOneWork(onlyfiles)
            if not archive_paths:
                continue
            archive_paths = [os.path.join(dir, f) for f in archive_paths]
            archives.append(Archive(archive_paths))

        return archives

    def __init__(self, paths: List[str]):
        """Creates an archive representation.

        Args:
          paths should be a full path to the paths for this archive.
          It must be a list of files as an archive can be represented with
          split archive files.
        """
        self.__paths = paths
        self.__work_name = None
        self.__file_name = ntpath.basename(self.__paths[0])
        self.__rj_code = _GetRjCode(self.__file_name)

    # The item page is deleted for items removed from the store. However the
    # Download page might have the name. Change it to get it from there.
    def FetchWorkName(self):
        if not self.__work_name:
            work_name = GetWorkNameFromWorkId(self.__rj_code)
            if not work_name:
                return ""

            if "/" in work_name:
                work_name = work_name.replace("/", "_")

            # Some file systems cannot handle colon.
            if ":" in work_name:
                work_name = work_name.replace(":", "_")
            self.__work_name = work_name

        return self.__work_name

    def Paths(self) -> List[str]:
        return self.__paths

    def WorkCode(self):
        return self.__rj_code


def _MoveArchiveToDir(archive: Archive, out_dir_name: str) -> pathlib.Path:
    """Move all the files in archive to a directory

    Args:
        archive (Archive):
            Object describing an archive which could be multiple files.
        out_dir_name (str):
            Name of the directory the archive should be moved to.

    Returns:
        pathlib.Path: Path to the directory that the archive was moved to.
    """
    file_dir = pathlib.Path(os.path.abspath(archive.Paths()[0])).parent
    out_dir = file_dir / out_dir_name
    out_dir.mkdir(exist_ok=True)

    for f in archive.Paths():
        # Get the file name and move it to out dir. In case if the
        # file already exists, this will overwrite it.
        file_name = ntpath.basename(f)
        shutil.move(f, out_dir / file_name)

    return out_dir


def CreateArchivesDirs(dir_with_archives: pathlib.Path) -> Set[pathlib.Path]:
    """Creates directories and moves the archives into the directory.

    This function takes a directory that contains a bunch of archives.
    It then finds out the title of the archives and makes a directory for each
    title. Then it moves the archives into that directory.

    Args:
        dir_with_archives is the directory containing archives (e.g. zip,
        partial rar files, etc.).

    Returns:
        A set of directories where the archives were moved to.
    """
    archives = Archive.Create(dir_with_archives)

    new_directories: Set[pathlib.Path] = set()
    for archive in archives:
        work_name = archive.FetchWorkName()
        print(f"Extracting {archive.Paths()} for {work_name}.")
        if not work_name:
            output_dir_name = archive.WorkCode()
        else:
            output_dir_name = f"{archive.WorkCode()} {archive.FetchWorkName()}"
        out_dir = _MoveArchiveToDir(archive, output_dir_name)
        new_directories.add(out_dir)

    return new_directories


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory with archives.")
    parser.add_argument(
        "--no-extract",
        default=False,
        action="store_true",
        help="Extract the archives after moving them to their directories.",
    )

    args = parser.parse_args()
    archive_file_path = pathlib.Path(args.directory)

    new_directories = CreateArchivesDirs(archive_file_path)

    if not args.no_extract:
        for new_dir in new_directories:
            print(f"Extracting files in: {new_dir}")
            Unarchive(new_dir, True)


if __name__ == "__main__":
    main()
