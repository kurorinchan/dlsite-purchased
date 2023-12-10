import argparse
from dataclasses import dataclass
from enum import Enum
import functools
from http import HTTPStatus
import logging

import os
import shutil

import dateparser
import login
import pickle
import pathlib
import requests
import sys
import downloader
import click_point
import all_purchased
import json
import dlsite_extract
import find_id

from typing import Callable, List, Optional, Set

from pathlib import Path

from contextlib import contextmanager

# None of these are final.
_MANAGEMENT_DIR_CONFIG_FILE = "management_dir"

_DEFAULT_CONFIG_DIR_FROM_HOME = ".dlsite_manager"

_DEFAULT_CONFIG_DIR = Path.home() / _DEFAULT_CONFIG_DIR_FROM_HOME

_IN_DOWNLOAD_DIR = "downloading"

_RAW_LOGIN_CREDENTAIL_FILE = "login_credential"


def _SetManagementDir(config_dir: Path, management_dir: Path):
    path = config_dir / _MANAGEMENT_DIR_CONFIG_FILE
    with open(path, "w") as f:
        f.write(str(management_dir))

    print(f"Changed management directory to {management_dir}")


def _GetManagementDir(config_dir: Path) -> Optional[str]:
    path = config_dir / _MANAGEMENT_DIR_CONFIG_FILE
    if not path.exists():
        return None
    with open(path, "r") as f:
        return f.read()


@dataclass
class RawCredential:
    username: str
    password: str


def _ReloginWithCredential(config_dir: Path) -> Optional[requests.Session]:
    cred_file = config_dir / _RAW_LOGIN_CREDENTAIL_FILE
    if not cred_file.exists():
        return None

    with open(cred_file, "rb") as f:
        credential: RawCredential = pickle.load(f)
    return login.Login(credential.username, credential.password)



# TODO: Add a relogin message in the exception or handle where its called.
class NoCredentialsException(Exception):
    pass


@contextmanager
def UsingMainSession(config_dir: Path):
    """Context manager for loading and saving the used session.

    This loads the main session. After it has been used (goes out of
    context) the session is saved to the same file.

    Args:
        config_dir: Configuration directory containing the main session.
    """
    session_file = config_dir / "main.session"
    session = LoadSessionFromFile(session_file)
    try:
        yield session
    finally:
        SaveMainSessionToConfigDir(config_dir, session)


def LoadSessionFromFile(session_file: Path) -> requests.Session:
    if not session_file.is_file():
        raise NoCredentialsException()
    with open(session_file, "rb") as f:
        session = requests.Session()
        session.cookies.update(pickle.load(f))
        return session


def SaveMainSessionToConfigDir(config_dir: Path, session: requests.Session):
    session_file = config_dir / "main.session"
    logging.debug("Saving session to file.")
    with open(session_file, "wb") as f:
        pickle.dump(session.cookies, f)


def Extract(in_download_dir: Path, management_dir: Path, keep_archive: bool):
    new_directories = dlsite_extract.CreateArchivesDirs(in_download_dir)
    for new_dir in new_directories:
        print(f"Extracting files in: {new_dir}")
        dlsite_extract.Unarchive(new_dir, keep_archive)

        print(f"Moving {new_dir} to {management_dir}")

        # Before moving the directory, check whether the same name directory
        # exists. If so delete it then move. This only really happens when
        # using the 'force' flag so, it is safe to do so (for now).
        move_destination_dir = management_dir / new_dir.name

        if move_destination_dir.exists():
            print(f"{management_dir} exists. Removing before move.")
            shutil.rmtree(move_destination_dir)

        # Want to move to management_dir here because new_dir is the directory
        # name.
        shutil.move(new_dir, management_dir)



def Download(
    session: requests.Session,
    config_dir: Path,
    management_dir: str,
    items_to_download: Set[str],
    extract: bool,
    keep_archive: bool,
):
    dl = downloader.Downloader(session)
    in_download_dir = Path(management_dir) / _IN_DOWNLOAD_DIR
    in_download_dir.mkdir(exist_ok=True)

    # Keeping track of relogins. Relogging in too many times is probably not
    # in a good state, so exit.
    _RELOGIN_THRESHOLD = 5
    num_relogin = 0
    while len(items_to_download) > 0:
        downloaded_items = set()
        for item_id in items_to_download:
            try:
                dl.DownloadTo(item_id, in_download_dir)
                downloaded_items.add(item_id)
            except downloader.HttpUnauthorizeException:
                if num_relogin > _RELOGIN_THRESHOLD:
                    print(
                        f"Tried relogin {num_relogin} times but still failing. Terminating."
                    )
                    raise

                print("Download unauthorized. Trying to relogin.")
                new_session = _ReloginWithCredential(config_dir)
                if not new_session:
                    print("Failed to find credential for login.")
                    raise
                print("Retrying.")
                dl.session = session
                num_relogin += 1

        items_to_download -= downloaded_items

    SaveMainSessionToConfigDir(config_dir, dl.session)

    if extract:
        Extract(in_download_dir, Path(management_dir), keep_archive)


def MakeItemIdsSet(items_to_download: List[str]) -> Set[str]:
    """Convert comma separated items into set of distinct item IDs.

    Args:
        items_to_download is the comma separated items. Each item could be an
            ID or a URL. Usually the command line argument.

    Returns:
        A set of item IDs.
    """
    item_ids_list = items_to_download
    item_ids_set = set()
    for item_id in item_ids_list:
        if item_id.startswith("http"):
            item_ids_set.add(downloader.FindItemIdFromUrl(item_id))
        else:
            item_ids_set.add(item_id)

    return item_ids_set


def _DownloadSubcommand(
    config_dir: Path,
    items: List[str],
    force: bool,
    extract: bool,
    keep_extracted_archive: bool,
):
    management_dir = _GetManagementDir(config_dir)
    if not management_dir:
        print(
            "Management dir is not specified. Specify the management dir "
            "with `config` first."
        )
        sys.exit(1)

    item_ids = MakeItemIdsSet(items)
    if force:
        items_to_download = set(item_ids)
    else:
        items_to_download = find_id.CheckAleadyDownloaded(item_ids, management_dir)

    with UsingMainSession(config_dir) as session:
        try:
            Download(
                session,
                config_dir,
                management_dir,
                items_to_download,
                extract,
                keep_extracted_archive,
            )
        except downloader.HttpUnauthorizeException:
            print("Unauthorized download. Try relogin and see if it gets fixed.")
            return


def _DownloadHandler(args):
    return _DownloadSubcommand(
        args.config_dir,
        args.items,
        args.force,
        args.extract,
        args.keep_extracted_archive,
    )


def _ConfigSubcommand(
    config_dir: Path,
    management_dir: Optional[Path],
    username: Optional[str],
    password: Optional[str],
    save_raw_credentials: bool,
) -> bool:
    config_dir.mkdir(parents=True, exist_ok=True)
    if management_dir:
        _SetManagementDir(config_dir, management_dir)
        return True

    if not (username and password):
        print("Username and password are required for login.")
        return False

    session = login.Login(username, password)

    SaveMainSessionToConfigDir(config_dir, session)

    if not save_raw_credentials:
        return True

    raw_credential_file = config_dir / _RAW_LOGIN_CREDENTAIL_FILE
    with open(raw_credential_file, "wb") as f:
        creds = RawCredential(username=username, password=password)
        pickle.dump(creds, f)

    return True


def _ConfigHandler(args):
    _ConfigSubcommand(
        args.config_dir,
        args.management_dir,
        args.username,
        args.password,
        not args.no_save_raw_credential,
    )


def _RemoveFilesInDir(directory: pathlib.Path):
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)


def _CleanSubcommand(args):
    management_dir = _GetManagementDir(args.config_dir)
    if not management_dir:
        print(
            "Management dir is not specified. Specify the management dir "
            "with `config` first."
        )
        sys.exit(1)

    watched_items = find_id.GetAllWatchedItems(management_dir)
    paths_to_be_removed: List[Path] = []
    for item in watched_items:
        # TODO: Check whether there are files in the directory. Otherwise
        # the same list of tiles are reprintted every time clean command is run.
        if item.prefix:
            print(f"SKIP: {item.directory} which is prefixed with {item.prefix}.")
            continue

        print(f"DELETE: {item.directory}.")
        paths_to_be_removed.append(item.directory)

    if args.dryrun:
        print("Dryrun complete. No files are deleted.")
        return

    if not args.yes:
        yes_no = input(
            "\n\nContinuing will delete all the files in the directory prefixed "
            "with DELETE above. "
            "Continue cleaning? "
            "[Y/n]:"
        )
        if not yes_no in ["yes", "Y"]:
            print("Aborting.")
            return

    for p in paths_to_be_removed:
        _RemoveFilesInDir(p)


def _FindSubcommand(args):
    management_dir = _GetManagementDir(args.config_dir)
    if not management_dir:
        print(f"Failed to find management directory. Try configuring first.")
        return 1

    items = find_id.FindItems(management_dir, args.ids)
    for item in items:
        print(f"{item.item_id}: {item.directory} prefix:{item.prefix}")


def _PurchasedHandler(args):
    with UsingMainSession(args.config_dir) as session:
        purchases = all_purchased.GetAllPurchases(session)

        if args.list_purchase_within:
            item_ids = []
            # The dates in the purchased info is in Z time (a.k.a. UTC but Z time is
            # treated differently from UTC time).
            target_date = dateparser.parse(f"{args.list_purchase_within} Z")
            if not target_date:
                logging.error(f"Failed to understand {args.list_purchase_within}")
                return
            logging.debug("target date:", target_date)
            for purchase in purchases:
                # The date here is in Z time (JSON)
                purchase_date = dateparser.parse(purchase["sales_date"])
                if not purchase_date:
                    logging.error(
                        f"Failed to parse date sales_date field in {purchase}"
                    )
                    continue
                logging.debug("Item date:", purchase_date)
                if purchase_date >= target_date:
                    item_ids.append(purchase["workno"])

            print("Pass these to download command:\n\n" + " ".join(item_ids) + "\n\n")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(purchases, f)


def _PointsHandler(args):
    with UsingMainSession(args.config_dir) as session:
        click_point.ClickForPoints(session)


# All the flags for this script is not final. It might change to use commands
# e.g. config, download, etc., instead of specifying with '--' prefixed flags.
def _ParseArgs(arg_array):
    """Parse command line arguments from an array.

    This may be helpful for testing too. The result could be passed to
    different subcommand handlers.

    Args:
        arg_array (Array[str]): Command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    parser_dl = subparsers.add_parser("download", help="see `download -h`")
    parser_dl.add_argument("items", nargs="+")
    parser_dl.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Force (re)download all items.",
    )
    parser_dl.add_argument(
        "--extract",
        action="store_true",
        default=True,
        help="Extract downloaded archives.",
    )
    parser_dl.add_argument(
        "--keep-extracted-archive",
        action="store_true",
        default=False,
        help="Keeps the extracted archive file. "
        "Set to false to keep the archives after extraction. "
        "This flag is only meaningful with the extract flag.",
    )
    parser_dl.set_defaults(handler=_DownloadHandler)

    parser_config = subparsers.add_parser("config", help="see config -h")
    parser_config.add_argument("-u", "--username", help="Login username.")
    parser_config.add_argument("-p", "--password", help="Login password.")
    parser_config.add_argument(
        "-m",
        "--management-dir",
        type=Path,
        help=("Place where all the files are downloaded files are managed."),
    )
    parser_config.add_argument(
        "--no-save-raw-credential",
        action="store_true",
        default=False,
        help=(
            "When passing login credentials (id/password) do not save it to "
            "a file. The session (cookie) would still be saved."
        ),
    )
    parser_config.set_defaults(handler=_ConfigHandler)

    parser_clean = subparsers.add_parser("clean")
    parser_clean.add_argument(
        "-n",
        "--dryrun",
        action="store_true",
        default=False,
        help="Dry run. Lists the files that will get cleaned.",
    )
    parser_clean.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Answer yes to all.",
    )
    parser_clean.set_defaults(handler=_CleanSubcommand)

    parser_find = subparsers.add_parser("find")
    parser_find.add_argument("ids", nargs="+")
    parser_find.set_defaults(handler=_FindSubcommand)

    parser_purchased = subparsers.add_parser("purchased")
    parser_purchased.add_argument("-o", "--output", help="Output file location.")
    parser_purchased.add_argument(
        "--list-latest-purchase", help="Downloads the latest purchases."
    )
    parser_purchased.add_argument(
        "--list-purchase-within",
        help="Prints the list of items purchased within "
        "the specified timedelta. "
        "The output can be pasted to the download command. "
        "This can handle anything parsable with dateparser library. "
        'E.g. "2 days", "1 week", "30 min ago"',
    )
    parser_purchased.set_defaults(handler=_PurchasedHandler)

    parser_points = subparsers.add_parser("lottery")
    parser_points.set_defaults(handler=_PointsHandler)

    parser.add_argument(
        "-d",
        "--debug",
        help="Print debugging logs.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Print verbose logs.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    parser.add_argument(
        "--config-dir",
        default=_DEFAULT_CONFIG_DIR,
        type=Path,
        help="Configuration directory. Use this if you want to "
        "use a different directory than the default config "
        "directory. Useful for testing.",
    )

    return parser.parse_args(arg_array)


def main(arg_array):
    args = _ParseArgs(arg_array)
    logging.basicConfig(level=args.loglevel)

    if hasattr(args, "handler"):
        args.handler(args)


if __name__ == "__main__":
    main(sys.argv[1:])
