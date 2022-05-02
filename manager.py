import argparse
from cgitb import handler
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
import all_purchased
import json
import dlsite_extract
import find_id

from typing import List, Optional, Set

from pathlib import Path

# None of these are final.
_MANAGEMENT_DIR_CONFIG_FILE = 'management_dir'

_DEFAULT_CONFIG_DIR_FROM_HOME = '.dlsite_manager'

_DEFAULT_CONFIG_DIR = Path.home() / _DEFAULT_CONFIG_DIR_FROM_HOME

_IN_DOWNLOAD_DIR = 'downloading'


def _SetManagementDir(config_dir: str, management_dir: str):
    path = Path(config_dir) / _MANAGEMENT_DIR_CONFIG_FILE
    with open(path, 'w') as f:
        f.write(management_dir)

    print(f'Changed management directory to {management_dir}')


def _GetManagementDir(config_dir: str) -> Optional[str]:
    path = Path(config_dir) / _MANAGEMENT_DIR_CONFIG_FILE
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return f.read()


def _RequireLoginCredentialsExit():
    logging.error('Username and password required to login.')
    sys.exit(1)


# TODO: Make this smarter and relogin if the saved session is expired.
# Trying getting the lists and see if it fails, if it does then it probably
# needs relogin.
def CreateLoggedInSession(save_session: bool, save_session_to: Optional[str],
                          username: str, password: str) -> requests.Session:
    if save_session:
        if not save_session_to:
            save_session_to = 'session.bin'

    if save_session_to:
        save_session = True

    if username and password:
        return login.Login(username, password)

    use_session_file = save_session or save_session_to
    if not use_session_file:
        if not username or not password:
            _RequireLoginCredentialsExit()

        return login.Login(username, password)

    session_file = pathlib.Path(save_session_to)
    if session_file.is_file():
        with open(session_file, 'rb') as f:
            session = requests.Session()
            session.cookies.update(pickle.load(f))
            return session

    if not username or not password:
        _RequireLoginCredentialsExit()
    return login.Login(username, password)


def SaveSession(save_session: bool, save_session_to: Optional[str],
                session: requests.Session):
    save_session_file = save_session or save_session_to
    if save_session_file:
        logging.debug('Saving session to file.')
        with open(save_session_to, 'wb') as f:
            pickle.dump(session.cookies, f)


def Extract(in_download_dir: pathlib.Path, management_dir: pathlib.Path,
            keep_archive: bool):
    new_directories = dlsite_extract.CreateArchivesDirs(in_download_dir)
    for new_dir in new_directories:
        print(f'Extracting files in: {new_dir}')
        dlsite_extract.Unarchive(new_dir, keep_archive)

        print(f'Moving {new_dir} to {management_dir}')

        # Before moving the directory, check whether the same name directory
        # exists. If so delete it then move. This only really happens when
        # using the 'force' flag so, it is safe to do so (for now).
        move_destination_dir = management_dir / new_dir.name

        if move_destination_dir.exists():
            print(f'{management_dir} exists. Removing before move.')
            shutil.rmtree(move_destination_dir)

        # Want to move to management_dir here because new_dir is the directory
        # name.
        shutil.move(new_dir, management_dir)


def Download(session: requests.Session, management_dir: str,
             items_to_download: Set[str], extract: bool, keep_archive: bool):
    dl = downloader.Downloader(session)
    in_download_dir = Path(management_dir) / _IN_DOWNLOAD_DIR
    in_download_dir.mkdir(exist_ok=True)

    for item_id in items_to_download:
        dl.DownloadTo(item_id, in_download_dir)

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
        if item_id.startswith('http'):
            item_ids_set.add(downloader.FindItemIdFromUrl(item_id))
        else:
            item_ids_set.add(item_id)

    return item_ids_set


def _DownloadSubcommand(items: str, force: bool, extract: bool,
                        keep_extracted_archive: bool):
    management_dir = _GetManagementDir(_DEFAULT_CONFIG_DIR)
    if not management_dir:
        print('Management dir is not specified. Specify the management dir '
              'with `config` first.')
        sys.exit(1)

    item_ids = MakeItemIdsSet(items)
    if force:
        items_to_download = set(item_ids)
    else:
        items_to_download = find_id.CheckAleadyDownloaded(
            item_ids, management_dir)

    session_file = _DEFAULT_CONFIG_DIR / 'main.session'
    session = CreateLoggedInSession(True, session_file, None, None)

    SaveSession(True, session_file, session)

    Download(session, management_dir, items_to_download, extract,
             keep_extracted_archive)


def _DownloadHandler(args):
    return _DownloadSubcommand(args.items, args.force, args.extract,
                               args.keep_extracted_archive)


def _ConfigSubcommand(args):
    Path(_DEFAULT_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    if args.management_dir:
        _SetManagementDir(_DEFAULT_CONFIG_DIR, args.management_dir)

    session_file = _DEFAULT_CONFIG_DIR / 'main.session'
    session = CreateLoggedInSession(True, session_file, args.username,
                                    args.password)

    SaveSession(True, session_file, session)


def _RemoveFilesInDir(directory: pathlib.Path):
    for f in os.scandir(directory):
        if f.is_dir():
            shutil.rmtree(f)
        else:
            os.remove(f)


def _CleanSubcommand(args):
    management_dir = _GetManagementDir(_DEFAULT_CONFIG_DIR)
    if not management_dir:
        print('Management dir is not specified. Specify the management dir '
              'with `config` first.')
        sys.exit(1)

    watched_items = find_id.GetAllWatchedItems(management_dir)
    paths_to_be_removed: List[Path] = []
    for item in watched_items:
        # TODO: Check whether there are files in the directory. Otherwise
        # the same list of tiles are reprintted every time clean command is run.
        if item.prefix:
            print(
                f'SKIP: {item.directory} which is prefixed with {item.prefix}.'
            )
            continue

        print(f'DELETE: {item.directory}.')
        paths_to_be_removed.append(item.directory)

    if args.dryrun:
        print('Dryrun complete. No files are deleted.')
        return

    if not args.yes:
        yes_no = input(
            '\n\nContinuing will delete all the files in the dirctory prefixed '
            'with DELETE above. '
            'Continue cleaning? '
            '[Y/n]:')
        if not yes_no in ['yes', 'Y']:
            print('Aborting.')

    for p in paths_to_be_removed:
        _RemoveFilesInDir(p)


def _FindSubcommand(args):
    items = find_id.FindItems(_GetManagementDir(_DEFAULT_CONFIG_DIR), args.ids)
    for item in items:
        print(f'{item.item_id}: {item.directory} prefix:{item.prefix}')


def _PurchasedHandler(args):
    session_file = _DEFAULT_CONFIG_DIR / 'main.session'
    session = CreateLoggedInSession(True, session_file, None, None)
    purchases = all_purchased.GetAllPurchases(session)

    if args.list_purchase_within:
        item_ids = []
        # The dates in the purchased info is in Z time (a.k.a. UTC but Z time is
        # treated differently from UTC time).
        target_date = dateparser.parse(f'{args.list_purchase_within} Z')
        logging.debug('target date:', target_date)
        for purchase in purchases:
            # The date here is in Z time (JSON)
            purchase_date = dateparser.parse(purchase['sales_date'])
            logging.debug('Item date:', purchase_date)
            if purchase_date >= target_date:
                item_ids.append(purchase['workno'])

        print('Pass these to download command:\n\n' + ' '.join(item_ids) +
              '\n\n')

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(purchases, f)


# All the flags for this script is not final. It might change to use commands
# e.g. config, download, etc., instead of specifying with '--' prefixed flags.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    parser_dl = subparsers.add_parser('download', help='see `download -h`')
    parser_dl.add_argument('items', nargs='+')
    parser_dl.add_argument('-f',
                           '--force',
                           action='store_true',
                           default=False,
                           help='Force (re)download all items.')
    parser_dl.add_argument('--extract',
                           action='store_true',
                           default=True,
                           help='Extract downloaded archives.')
    parser_dl.add_argument(
        '--keep-extracted-archive',
        action='store_true',
        default=False,
        help='Keeps the extracted archive file. '
        'Set to false to keep the archives after extraction. '
        'This flag is only meaningful with the extract flag.')
    parser_dl.set_defaults(handler=_DownloadHandler)

    parser_config = subparsers.add_parser('config', help='see config -h')
    parser_config.add_argument('-u', '--username', help='Login username.')
    parser_config.add_argument('-p', '--password', help='Login password.')
    parser_config.add_argument(
        '-m',
        '--management-dir',
        default='',
        help=('Place where all the files are downloaded files are managed.'))
    parser_config.add_argument(
        '--no-save-raw-credential',
        action='store_true',
        default=False,
        help=('When passing login credentials (id/password) do not save it to '
              'a file. The session (cookie) would still be saved.'))
    parser_config.set_defaults(handler=_ConfigSubcommand)

    parser_clean = subparsers.add_parser('clean')
    parser_clean.add_argument(
        '-n',
        '--dryrun',
        action='store_true',
        default=False,
        help='Dry run. Lists the files that will get cleaned.',
    )
    parser_clean.add_argument(
        '-y',
        '--yes',
        action='store_true',
        default=False,
        help='Answer yes to all.',
    )
    parser_clean.set_defaults(handler=_CleanSubcommand)

    parser_find = subparsers.add_parser('find')
    parser_find.add_argument('ids', nargs='+')
    parser_find.set_defaults(handler=_FindSubcommand)

    parser_purchased = subparsers.add_parser('purchased')
    parser_purchased.add_argument('-o',
                                  '--output',
                                  help='Output file location.')
    parser_purchased.add_argument('--list-latest-purchase',
                                  help='Downloads the latest purchases.')
    parser_purchased.add_argument(
        '--list-purchase-within',
        help='Prints the list of items purchased within '
        'the specified timedelta. '
        'The output can be pasted to the download command. '
        'This can handle anything parsable with dateparser library. '
        'E.g. "2 days", "1 week", "30 min ago"')
    parser_purchased.set_defaults(handler=_PurchasedHandler)

    parser.add_argument(
        '-d',
        '--debug',
        help="Print debugging logs.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help="Print verbose logs.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    if hasattr(args, 'handler'):
        args.handler(args)