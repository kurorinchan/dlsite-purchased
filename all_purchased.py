import argparse
import pathlib
from typing import Dict, List, Union
import requests
import http.cookiejar
import json
import logging
import login

__URL_TEMPLATE = "https://play.dlsite.com/api/purchases?page={}"


def GetAllPurchasesFromUsernamePassword(username, password):
    session = login.Login(username, password)
    return GetAllPurchases(session)


def GetAllPurchasesFromCookie(cookie):
    session = requests.session()
    session.cookies.update(cookie)
    return GetAllPurchases(session)


def GetAllPurchases(session: requests.Session) -> List:
    """Get all purchased info as dictionary.

    The API is used to get all the purchase info as json and converts it to
    python dictionary.

    Returns:
        JSON-like dictionary.
    """
    current_page_num = 1
    all_works = []

    # response = session.get(__URL_TEMPLATE.format(current_page_num), headers=headers)
    # With the following request, in a browser, HTTP headers:
    # 'x-xsrf-token': session.cookies.get_dict()['XSRF-TOKEN']
    # 'referer': 'https://play.dlsite.com/'
    # are added.
    # This may be useful when they start to require them.
    while True:
        response = session.get(__URL_TEMPLATE.format(current_page_num))
        current_page_num += 1

        response.raise_for_status()
        response_json = response.json()

        # Requesting past all purchased items still works. But the works field
        # will be an empty array.
        works = response_json["works"]
        if not works:
            break
        all_works += works

    return all_works


def _WriteAllworksToFile(all_works: Dict, output_file: Union[str, pathlib.Path]):
    with open(output_file, "w") as f:
        json.dump(all_works, f)


def WriteAllPurchases(cookie_file, output_file):
    cookie_jar = http.cookiejar.MozillaCookieJar(cookie_file)
    cookie_jar.load()

    _WriteAllworksToFile(GetAllPurchasesFromCookie(cookie_jar), output_file)


def WriteAllPurchasesWithUsernamePassword(username, password, output_file):
    _WriteAllworksToFile(
        GetAllPurchasesFromUsernamePassword(username, password), output_file
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--cookie", help="Cookie file.")
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file containing all purchased items.",
    )

    parser.add_argument("--username", help="Login username.")
    parser.add_argument("--password", help="Login password.")

    parser.add_argument(
        "-d",
        "--debug",
        help="Print lots of debugging statements",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Be verbose",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    if not args.cookie and not args.username:
        parser.error("Must specify a cookie file or login credential.")

    if args.username:
        if not args.password:
            parser.error("Password is required if using username.")

        WriteAllPurchasesWithUsernamePassword(args.username, args.password, args.output)
    else:
        WriteAllPurchases(args.cookie, args.output)
