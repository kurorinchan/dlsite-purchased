# Most of the flags in this file is not final and is unstable.

import argparse
import logging

import mylist_editor
import downloader

import manager

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Common flags.
    parser.add_argument('--username', help='Login username.')
    parser.add_argument('--password', help='Login password.')
    parser.add_argument('--save-session',
                        action='store_true',
                        default=False,
                        help='Saves the logged in session to a file.')
    parser.add_argument(
        '--save-session-to',
        help=('Specifies where the session file is stored. '
              'If the file already exists, it tries to load the file before '
              'trying to login. '
              'This flag implies --save-session.'))

    parser.add_argument(
        '--download', help='Comma separated Item IDs (Work IDs) to download.')
    parser.add_argument(
        '--download-dir',
        default='.',
        help=(
            'If --download is specified, this flag may be used to specify the '
            'output directory.'))

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

    # Purchases.
    parser.add_argument(
        '--output-purchased',
        help='Outputs the list of purchased item as JSON to the specified file.'
    )

    # List.
    parser.add_argument('--show-mylists',
                        action='store_true',
                        help='Shows my lists.')

    parser.add_argument(
        '--add-to-list',
        help='Add an item to a list. The format is <list name>:<Item ID>',
    )

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    session = manager.CreateLoggedInSession(args.save_session,
                                            args.save_session_to,
                                            args.username, args.password)

    if args.show_mylists:
        editor = mylist_editor.MyListEditor(session)
        mylists = editor.GetLists()
        for list in mylists:
            print(list.name)

    if args.download:
        dl = downloader.Downloader(session)
        for item_id in args.download.split(','):
            dl.DownloadTo(item_id, args.download_dir)

    manager.SaveSession(args.save_session, args.save_session_to, session)