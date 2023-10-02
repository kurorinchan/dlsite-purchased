import logging
import pathlib
from typing import List, Union
import urllib.parse
from tqdm import tqdm
from sys import path
from bs4 import BeautifulSoup
import requests

# Too small chunk size doesn't make much sense. 25 megabytes is set here.
_DOWNLOAD_CHUNK_SIZE = 25 * 1024 * 1024


# Thrown when the HTTP status is 401.
class HttpUnauthorizeException(Exception):
    def __init__(self, response: requests.Response) -> None:
        super().__init__(response)
        self.response = response


def FindItemIdFromUrl(item_url):
    parse_result = urllib.parse.urlparse(item_url)
    path = parse_result.path
    html_name = path.split('/')[-1]
    if not html_name.endswith('.html'):
        logging.error(f'Failed to find item id from {item_url}')
        raise Exception(f'Failed to find item id from {item_url}')

    return html_name.split('.')[0]


def _GetContentDispositionFilename(content_disposition):
    _FILENAME = 'filename='
    split_fields = content_disposition.split(';')
    for field in split_fields:
        field = field.strip()
        if not field.startswith(_FILENAME):
            continue

        field = field[len(_FILENAME):]
        return field.strip('"')

    return ''


def _DownloadWithProgress(response: requests.Response,
                          download_path: pathlib.Path) -> pathlib.Path:
    """Downloads a file using streaming response to a path.

    Note that while it is downloading, it will use a temporary name.

    Args:
        response is the Response object from getting the download object. It
            is used to get the actual bytes from the a (e.g. GET) request.
        download_path is where the downloaded file will be placed on success.

    Returns:
        A Path object the downloaded file.
    """
    _TEMP_DOWNLOAD_FILE_SUFFIX = '.downloading'
    temp_download_path = download_path.with_suffix(_TEMP_DOWNLOAD_FILE_SUFFIX)

    with open(temp_download_path, 'wb') as f:
        progress = tqdm(unit="B",
                        total=int(response.headers['Content-Length']),
                        unit_scale=True)
        for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK_SIZE):
            if not chunk:
                continue
            progress.update(len(chunk))
            f.write(chunk)

    return temp_download_path.rename(download_path)


class Downloader:

    def __init__(self, session: requests.Session) -> None:
        self.__session = session

    def _Get(self, url: str) -> requests.Response:
        """Helper function for GETting a URL for downloading.

        This redirects and uses streaming.

        Raises:
            HttpUnauthorizedException is thrown on HTTP unauthorized.

        Returns:
            response object.
        """
        logging.info(f"Getting {url}.")
        response = self.__session.get(
            url,
            allow_redirects=True,
            stream=True,
            headers={
                'User-Agent':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
            })
        logging.info(f'The downloaded url (after possible redirect) was {response.url}')
        logging.info(f'Response status was: {response.status_code}')

        if response.status_code == 401:
            raise HttpUnauthorizeException(response)
        return response

    def GetDownloadUrls(self, item_id: str):
        """Returns a list of URLs to download the item.

        When the item download is split into multiple files, the list would
        contain multiple URLs. In other workds, the list may only contain one
        url if the item can be downloaded from a single link.

        The URLs in the list may require a redirect to get to the actual
        octet stream. However the URLs should not redirect to an HTML webpage,
        i.e. it should not got to a page that displays a split-file download
        page.
        
        Args:
            item_id is the ID of the item. Also called work ID.

        Raises:
            HttpUnauthorizedException is thrown on HTTP unauthorized.

        Returns:
            A list of URLs. The URLs may require a redirect but the redirected
            URL should be an octet stream.
        """
        url = f'https://play.dlsite.com/api/download?workno={item_id}'
        # It always redirects. stream=True is necessary if it directly goes to
        # download.
        response = self._Get(url)
        content_type = response.headers["content-type"]

        logging.info(f'Response content type is {content_type}')
        logging.info(f'Response content length {response.headers["content-length"]}')
        if 'text/html' in content_type:
            # This is a webpage that contains the split files.
            split_page = BeautifulSoup(response.text, 'html.parser')
            div_file = split_page.find(id='download_division_file')
            split_parts = div_file.find_all(class_='work_download')

            return [part.find('a').get('href') for part in split_parts]

        return [response.url]

    def DownloadTo(self, item_id: str,
                   dir: Union[str, pathlib.Path]) -> List[pathlib.Path]:
        """Downloads item to a directory.

        Note that an item might be split into multiple files, i.e. split
        archive. This function downloads all of them to a directory.
        The file names of the downloaded files would be the names specified
        by the server.

        Args:
            item_id is the ID of the item. Also called work ID. Or this could
              the store URL of the item.
            dir is where the downoloaded items will be placed.

        Raises:
            HttpUnauthorizedException is thrown on HTTP unauthorized.

        Returns:
            A list of paths to the downloaded files.
        """
        if item_id.startswith('http'):
            item_id = FindItemIdFromUrl(item_id)

        logging.debug(f'Processing item: {item_id}')
        downloaded_item_paths = []

        urls = self.GetDownloadUrls(item_id)
        dir_path = pathlib.Path(dir)
        for index, url in enumerate(urls):
            response = self._Get(url)
            disposition = response.headers['content-disposition']
            file_name = _GetContentDispositionFilename(disposition)
            if not file_name:
                file_name = f'{item_id}.part{index + 1}'
                logging.debug(f'Could not find file name from the server. '
                              f'Naming it {file_name}')

            print(f'Downloading {file_name}: '
                  f'{int(response.headers["content-length"]):,} bytes.')

            downloaded_item_paths.append(
                _DownloadWithProgress(response, dir_path / file_name))

        print(f'{item_id} download complete.')
        return downloaded_item_paths