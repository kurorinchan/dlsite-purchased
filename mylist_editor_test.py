import unittest
from unittest.mock import MagicMock, patch

import requests
import mylist_editor
import json


class ResponseLike:
    def __init__(self, status_code, json="") -> None:
        self.status_code = status_code
        self.json_str = json

    def json(self):
        return json.loads(self.json_str)


class ListEditTest(unittest.TestCase):
    @patch("requests.Session.get")
    def testGetListsStatusCodeNotFound(self, get_mock):
        get_mock.return_value = ResponseLike(requests.codes.not_found)
        editor = mylist_editor.MyListEditor(requests.Session())
        self.assertFalse(editor.GetLists())

    @patch("requests.Session.get")
    def testGetLists(self, get_mock):
        get_mock.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [{
                    "id": 1891389,
                    "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["0"]
                }],
                "mylist_works": ["RJ1234"]
            }""",
        )
        editor = mylist_editor.MyListEditor(requests.Session())
        lists = editor.GetLists()
        self.assertTrue(lists)
        self.assertEqual(len(lists), 1)
        mylist = lists[0]
        self.assertEqual(
            mylist.name, "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8"
        )
        self.assertEqual(mylist.id, "1891389")
        self.assertEqual(mylist.creation_date, "Sun, 31 Jan 2021 06:42:26 +0900")
        self.assertListEqual(mylist.item_ids, ["RJ1234"])

    @patch("requests.Session.get")
    def testGetMultipleLists(self, get_mock):
        get_mock.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [
                {
                    "id": 1891,
                    "mylist_name": "abcd",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["3", "0"]
                },
                {
                    "id": 389,
                    "mylist_name": "defg",
                    "insert_date": "Sun, 31 Jan 2021 06:42:28 +0900",
                    "mylist_work_id": ["2", "1"]
                }
                ],
                "mylist_works": ["RJ1234", "RJ879393", "RJ37483", "VJ772"]
            }""",
        )
        editor = mylist_editor.MyListEditor(requests.Session())
        lists = editor.GetLists()
        self.assertTrue(lists)
        self.assertEqual(len(lists), 2)
        self.assertEqual(lists[0].name, "abcd")
        self.assertEqual(lists[0].id, "1891")
        self.assertEqual(lists[0].creation_date, "Sun, 31 Jan 2021 06:42:26 +0900")
        self.assertListEqual(lists[0].item_ids, ["VJ772", "RJ1234"])

        self.assertEqual(lists[1].name, "defg")
        self.assertEqual(lists[1].id, "389")
        self.assertEqual(lists[1].creation_date, "Sun, 31 Jan 2021 06:42:28 +0900")
        self.assertListEqual(lists[1].item_ids, ["RJ37483", "RJ879393"])

    def testDeleteListItemFromListId(self):
        mock_session = MagicMock()
        mock_session.get.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [{
                    "id": 1891389,
                    "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["0"]
                }],
                "mylist_works": ["RJ1234"]
            }""",
        )
        mock_session.post.return_value = ResponseLike(
            requests.codes.ok,
            '{"result":true,"mylist_id":1891389,"mylist_work_id":"0"}',
        )

        editor = mylist_editor.MyListEditor(mock_session)
        self.assertTrue(editor.DeleteItemFromListId("RJ1234", "1891389"))

        mock_session.post.assert_called_once_with(
            "https://play.dlsite.com/api/mylist/update_mylist_work",
            data={
                "type": "delete",
                "mylist_id": "1891389",
                "mylist_work_id": "0",
            },
        )

    def testDeleteListItemFromListName(self):
        mock_session = MagicMock()
        mock_session.get.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [{
                    "id": 1891389,
                    "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["0"]
                }],
                "mylist_works": ["RJ1234"]
            }""",
        )
        mock_session.post.return_value = ResponseLike(
            requests.codes.ok,
            '{"result":true,"mylist_id":1891389,"mylist_work_id":"0"}',
        )

        editor = mylist_editor.MyListEditor(mock_session)
        self.assertTrue(
            editor.DeleteItemFromListName(
                "RJ1234", "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8"
            )
        )
        mock_session.post.assert_called_once_with(
            "https://play.dlsite.com/api/mylist/update_mylist_work",
            data={
                "type": "delete",
                "mylist_id": "1891389",
                "mylist_work_id": "0",
            },
        )

    def testDeleteListItemFromList(self):
        mock_session = MagicMock()
        mock_session.get.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [{
                    "id": 1891389,
                    "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["0"]
                }],
                "mylist_works": ["RJ1234"]
            }""",
        )
        mock_session.post.return_value = ResponseLike(
            requests.codes.ok,
            '{"result":true,"mylist_id":1891389,"mylist_work_id":"0"}',
        )

        editor = mylist_editor.MyListEditor(mock_session)
        lists = editor.GetLists()
        self.assertTrue(editor.DeleteItemFromList("RJ1234", lists[0]))
        mock_session.post.assert_called_once_with(
            "https://play.dlsite.com/api/mylist/update_mylist_work",
            data={
                "type": "delete",
                "mylist_id": "1891389",
                "mylist_work_id": "0",
            },
        )

    def testDeleteItemsFromListWithMulitpleItems(self):
        mock_session = MagicMock()
        mock_session.get.return_value = ResponseLike(
            requests.codes.ok,
            """ {
                "mylists": [{
                    "id": 1891389,
                    "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
                    "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
                    "mylist_work_id": ["0", "2"]
                }],
                "mylist_works": ["RJ1234", "RJ4321", "RJ7890"]
            }""",
        )
        mock_session.post.return_value = ResponseLike(
            requests.codes.ok,
            '{"result":true,"mylist_id":1891389,"mylist_work_id":"0"}',
        )

        editor = mylist_editor.MyListEditor(mock_session)
        lists = editor.GetLists()
        self.assertTrue(editor.DeleteItemFromList("RJ7890", lists[0]))
        mock_session.post.assert_called_once_with(
            "https://play.dlsite.com/api/mylist/update_mylist_work",
            data={
                "type": "delete",
                "mylist_id": "1891389",
                "mylist_work_id": "1",
            },
        )
