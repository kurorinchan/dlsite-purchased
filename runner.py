# Most of the flags in this file is not final and is unstable.

import argparse
import logging

import mylist_editor
import login
import pickle
import pathlib
import requests
import sys

def _RequireLoginCredentialsExit():
    logging.error('Username and password required to login.')
    sys.exit(1)

def _CreateLoggedInSession(args):
    if args.save_session:
        if not args.save_session_to:
            args.save_session_to = 'session.bin'
    
    if args.save_session_to:
        args.save_session = True

    use_session_file = args.save_session or args.save_session_to
    if not use_session_file:
        if not args.username or not args.password:
            _RequireLoginCredentialsExit()
            
        return login.Login(args.username, args.password)

    session_file = pathlib.Path(args.save_session_to)
    if session_file.is_file():
        with open(session_file, 'rb') as f:
            session = requests.Session()
            session.cookies.update(pickle.load(f))
            return session

    if not args.username or not args.password:
        _RequireLoginCredentialsExit()
    return login.Login(args.username, args.password)

def _SaveSession(args):
    save_session_file = args.save_session or args.save_session_to
    with open(args.save_session_to, 'wb') as f:
        pickle.dump(session.cookies, f)


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

    session = _CreateLoggedInSession(args)

    if args.show_mylists:
        editor = mylist_editor.MyListEditor(session)
        print(editor.GetLists())
        
    _SaveSession(args)