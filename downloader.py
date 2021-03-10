import logging
import pathlib
from sys import path
from bs4 import BeautifulSoup

# Too small chunk size doesn't make much sense. 25 megabytes is set here.
_DOWNLOAD_CHUNK_SIZE = 25 * 1024 * 1024


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


class Downloader:
    def __init__(self, session) -> None:
        self.__session = session

    def _Get(self, url):
        """Helper function for GETting a URL for downloading.

        This redirects and uses streaming.

        Returns:
            response object.
        """
        return self.__session.get(url, allow_redirects=True, stream=True)

    def GetDownloadUrls(self, item_id):
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

        Returns:
            A list of URLs. The URLs may require a redirect but the redirected
            URL should be an octet stream.
        """
        url = f'https://play.dlsite.com/api/download?workno={item_id}'
        # It always redirects. stream=True is necessary if it directly goes to
        # download.
        response = self._Get(url)
        logging.info(f'The downloaded url was {response.url}')
        content_type = response.headers["content-type"]

        logging.info(f'content type is {content_type}')
        logging.info(f'content length {response.headers["content-length"]}')
        if 'text/html' in content_type:
            # This is a webpage that contains the split files.
            split_page = BeautifulSoup(response.text, 'html.parser')
            div_file = split_page.find(id='download_division_file')
            split_parts = div_file.find_all(class_='work_download')

            return [part.find('a').get('href') for part in split_parts]

        return [response.url]

    def DownloadTo(self, item_id, dir):
        """Downloads item to a directory.

        Note that an item might be split into multiple files, i.e. split
        archive. This function downloads all of them to a directory.
        The file names of the downloaded files would be the names specified
        by the server.

        Args:
            item_id is the ID of the item. Also called work ID.
            dir is where the downoloaded items will be placed.
        """
        urls = self.GetDownloadUrls(item_id)
        dir_path = pathlib.Path(dir)
        for index, url in enumerate(urls):
            response = self._Get(url)
            disposition = response.headers['content-disposition']
            file_name = _GetContentDispositionFilename(disposition)
            if not file_name:
                file_name = f'{item_id}.part{index + 1}'
                logging.info(f'Could not find file name from the server. '
                             f'Naming it {file_name}')

            print(f'Downloading {file_name}: '
                  f'{int(response.headers["content-length"]):,} bytes.')

            with open(dir_path / file_name, 'wb') as f:
                for chunk in response.iter_content(
                        chunk_size=_DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)

        print(f'{item_id} download complete.')
