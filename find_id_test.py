from tempfile import tempdir
import unittest

from pathlib import Path

from tempfile import TemporaryDirectory

import find_id


class FindIdTest(unittest.TestCase):
    def testAddItemsInDirOnlyItemId(self):
        with TemporaryDirectory() as tmpdir:
            test_item_dir = Path(tmpdir) / "RJ1232"
            test_item_dir.mkdir()

            items = find_id.Items()
            find_id.AddItemsInDir(tmpdir, items)
            self.assertIsNotNone(items.Find("RJ1232"))

    def testAddItemsInDirWithTitle(self):
        with TemporaryDirectory() as tmpdir:
            test_item_dir = Path(tmpdir) / "RJ1232 with some titl"
            test_item_dir.mkdir()

            items = find_id.Items()
            find_id.AddItemsInDir(tmpdir, items)
            self.assertIsNotNone(items.Find("RJ1232"))

    # Verify that all items under the directory are added.
    def testAddItemsGetAll(self):
        with TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "RJ23123").mkdir()
            (Path(tmpdir) / "RJ23").mkdir()
            (Path(tmpdir) / "RJ787").mkdir()
            (Path(tmpdir) / "VJ2333623").mkdir()
            (Path(tmpdir) / "RJ111").mkdir()

            items = find_id.Items()
            find_id.AddItemsInDir(tmpdir, items)
            all_items = items.GetItemsAsList()
            self.assertIsNotNone(all_items)
            self.assertEquals(len(all_items), 5)
            all_item_ids = [item.item_id for item in all_items]
            self.assertIn("RJ23123", all_item_ids)
            self.assertIn("RJ23", all_item_ids)
            self.assertIn("RJ787", all_item_ids)
            self.assertIn("VJ2333623", all_item_ids)
            self.assertTrue("RJ111", all_item_ids)

    def testGetAllItemPaths(self):
        with TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "RJ23123").mkdir()
            (Path(tmpdir) / "視聴済み" / "RJ23").mkdir(parents=True)

            paths = find_id.GetAllItemPaths(tmpdir)

            self.assertIn((Path(tmpdir) / "RJ23123"), paths)
            self.assertIn((Path(tmpdir) / "視聴済み" / "RJ23"), paths)

    def testGetAllWatchedItemPaths(self):
        with TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "RJ23123").mkdir()
            (Path(tmpdir) / "視聴済み" / "RJ23").mkdir(parents=True)

            paths = find_id.GetAllWatchedItemPaths(tmpdir)

            self.assertEquals(len(paths), 1)
            self.assertIn((Path(tmpdir) / "視聴済み" / "RJ23"), paths)
