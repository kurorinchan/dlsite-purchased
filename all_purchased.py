import argparse
import pathlib
from typing import Dict, List
import requests
import http.cookiejar
import json
import logging
import login
import concurrent.futures

import time

__URL_TEMPLATE = "https://play.dlsite.com/api/purchases?page={}"
__PURCHASED_COUNT_URL = "https://play.dlsite.com/api/product_count"


def GetAllPurchasesFromUsernamePassword(username, password):
    session = login.Login(username, password)
    return GetAllPurchases(session)


def GetAllPurchasesFromCookie(cookie):
    session = requests.session()
    session.cookies.update(cookie)
    return GetAllPurchases(session)


def GetPurchasedItemsInParallel(
    num_pages: int, max_parallel_tasks: int, session: requests.Session
) -> List[Dict]:
    """Get purchased items in parallel.

    Args:
        num_pages (int): _description_
        max_sessions (int): _description_
        session (requests.Session): _description_

    Returns:
        List[Dict]: A list of JSON-like dictionaries, from getting all the
                    items. Combining them should result in a full list of items.

    Raises:
        HTTPError when there is a problem fetching data.
    """
    _FIRST_PAGE_NUM = 1
    max_page_num = _FIRST_PAGE_NUM + num_pages

    urls = [
        __URL_TEMPLATE.format(page_num)
        for page_num in range(_FIRST_PAGE_NUM, max_page_num)
    ]

    if not urls:
        return []

    # Note that this could throw an exception when the response status is not OK.
    def _FetchOne(url):
        # With the following request, in a browser, HTTP headers:
        # 'x-xsrf-token': session.cookies.get_dict()['XSRF-TOKEN']
        # 'referer': 'https://play.dlsite.com/'
        # are added.
        start_get = time.perf_counter()
        response = session.get(url)
        end_get = time.perf_counter()
        response.raise_for_status()

        start_json_parse = time.perf_counter()
        response_json = response.json()
        end_json_parse = time.perf_counter()

        logging.info(
            f"{url}: Get took {end_get - start_get}. Parse json took {end_json_parse - start_json_parse}"
        )

        return response_json

    # Looks like 10 is the reasonable amount of parallelism. Increasing this
    # could result in an error or no speed-up.
    _SIMULTANEOUS_CONNETIONS = 10
    pool_size = min(max_parallel_tasks, _SIMULTANEOUS_CONNETIONS)
    responses = []
    with concurrent.futures.ThreadPoolExecutor(pool_size) as executor:
        future_to_url = {executor.submit(_FetchOne, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                logging.info(f"Got response for {url}")
                responses.append(data)
            except:
                logging.info(f"Fetching {url} raised an exception.")
                raise
    return responses


def GetAllPurchases(session: requests.Session) -> List:
    """Get all purchased info as dictionary.

    The API is used to get all the purchase info as json and converts it to
    python dictionary.

    Returns:
        JSON-like dictionary.

    Raises:
        HTTPError when there is a problem.
    """

    response = session.get(__PURCHASED_COUNT_URL)
    response.raise_for_status()
    purchased_json = response.json()
    num_items: int = purchased_json["user"]
    logging.info(f"Purchase count json is: {purchased_json}")
    if num_items == 0:
        logging.info("No items.")
        return []

    items_per_page: int = purchased_json["page_limit"]

    num_pages = num_items // items_per_page
    if num_items % items_per_page != 0:
        num_pages += 1

    results = GetPurchasedItemsInParallel(
        num_pages, purchased_json["concurrency"], session
    )

    all_works = []
    for json_response in results:
        works = json_response["works"]
        if not works:
            logging.info("No works info. Skipping.")
            continue
        all_works += works

    return all_works


def _WriteAllworksToFile(all_works: Dict, output_file: str | pathlib.Path):
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
