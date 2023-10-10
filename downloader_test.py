import tempfile
import unittest
from unittest.mock import MagicMock, patch
import downloader


class DownloaderTest(unittest.TestCase):
    def testFindItemIdFromUrl(self):
        self.assertEqual(
            "RJ75123", downloader.FindItemIdFromUrl("http://anydomain.any/RJ75123.html")
        )

    def testFindItemIdFromUrlNoItemId(self):
        with self.assertRaises(Exception):
            downloader.FindItemIdFromUrl("http://anydomain.any/example")

    @patch("downloader.Downloader._Get")
    def testGetDownloadUrlsSingleFile(self, get_mock):
        dl = downloader.Downloader(MagicMock())
        response_mock = MagicMock()
        response_mock.headers = {
            "content-type": "application/zip",
            "content-length": 1234321,
        }
        response_mock.url = "https://download.url/123.zip"
        get_mock.return_value = response_mock
        self.assertEqual(["https://download.url/123.zip"], dl.GetDownloadUrls("RJ123"))

    @patch("downloader.Downloader._Get")
    def testGetDownloadUrlsSplitArchive(self, get_mock):
        dl = downloader.Downloader(MagicMock())
        response_mock = MagicMock()
        response_mock.headers = {
            "content-type": "text/html",
            "content-length": 1234321,
        }
        response_mock.url = "https://download.url/split/page.html"
        response_mock.text = """
            <html>
              <div id="download_division_file">
                <div class="work_download">
                  <a href="https://download.url/file1.rar">file1</a>
                </div>
                <div class="work_download">
                  <a href="https://download.url/file2.rar">file2</a>
                </div>
                <div class="work_download">
                  <a href="https://download.url/file3.rar">file3</a>
                </div>
              </div>
            </html>
        """
        get_mock.return_value = response_mock
        self.assertEqual(
            [
                "https://download.url/file1.rar",
                "https://download.url/file2.rar",
                "https://download.url/file3.rar",
            ],
            dl.GetDownloadUrls("RJ123"),
        )

    def testGetContentDispositionFilename(self):
        self.assertEqual(
            "something.jpg",
            downloader._GetContentDispositionFilename(
                'attachment; filename="something.jpg"'
            ),
        )

    def testGetContentDispositionNoFilename(self):
        self.assertEqual(
            "",
            downloader._GetContentDispositionFilename("attachment"),
        )

    @patch("downloader.Downloader._Get")
    @patch("downloader.Downloader.GetDownloadUrls")
    @patch("downloader._DownloadWithProgress")
    def testDownloadTo(self, dl_with_progress_mock, get_download_urls_mock, get_mock):
        get_download_urls_mock.return_value = ["https://download.url/1.zip"]
        dl_with_progress_mock.return_value = "download_file_name.zip"
        response_mock = MagicMock()
        response_mock.headers = {
            "content-type": "text/html",
            "content-length": 1234321,
            "content-disposition": 'inline; filename="download_file_name.zip"',
        }
        get_mock.return_value = response_mock
        dl = downloader.Downloader(MagicMock())
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(
                [
                    "download_file_name.zip",
                ],
                dl.DownloadTo("RJ30123", tmpdir),
            )
