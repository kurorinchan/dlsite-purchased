from os import PathLike
import unittest
from unittest.mock import ANY, MagicMock, patch

import all_purchased


class AllPurchased(unittest.TestCase):
    @patch("requests.Session")
    def testNoPurchases(self, session_mock):
        """Verify that it works without any purcheses."""
        response_mock = MagicMock()
        session_mock.get.return_value = response_mock

        response_mock.json.return_value = {
            "user": 0,
            "production": 0,
            "page_limit": 50,
            "concurrency": 500,
        }

        self.assertEqual(len(all_purchased.GetAllPurchases(session_mock)), 0)

    @patch("all_purchased.GetPurchasedItemsInParallel")
    @patch("requests.Session")
    def testGetAllPurchases(
        self, session_mock: MagicMock, parallel_get_mock: MagicMock
    ):
        response_mock = MagicMock()
        session_mock.get.return_value = response_mock

        response_mock.json.return_value = {
            "user": 101,
            "production": 0,
            "page_limit": 50,
            "concurrency": 500,
        }

        parallel_get_mock.return_value = [
            {
                "works": ["a", "bunch", "of", "items"],
            },
            {
                "works": ["a few", "items"],
            },
        ]

        items = all_purchased.GetAllPurchases(session_mock)
        self.assertEqual(len(items), 6)

        for work in ["a", "bunch", "of", "items", "a few", "items"]:
            self.assertIn(work, items)

        parallel_get_mock.assert_called_once_with(3, 500, ANY)

    @patch("requests.Session")
    def testGetPurchasedItemsInParallel(self, session_mock: MagicMock):
        session_mock.get.return_value = MagicMock()
        responses = all_purchased.GetPurchasedItemsInParallel(10, 1, session_mock)

        self.assertEqual(len(responses), 10)

    @patch("requests.Session")
    def testGetPurchasedItemsInParallelRaiseException(self, session_mock: MagicMock):
        response_mock = MagicMock()
        session_mock.get.return_value = response_mock
        response_mock.raise_for_status.side_effect = Exception("test exception!!")
        with self.assertRaises(Exception):
            all_purchased.GetPurchasedItemsInParallel(10, 1, session_mock)
