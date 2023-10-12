import unittest

from pathlib import Path

from tempfile import TemporaryDirectory

import find_id


class FindIdTest(unittest.TestCase):
    def testAddItemsInDirOnlyItemId(self):
        with TemporaryDirectory() as tmpdir:
            test_item_dir = Path(tmpdir) / "RJ1232"
            test_item_dir.mkdir()

            items = find_id.GetItemsInDir(tmpdir)
            self.assertIsNotNone(items.Find("RJ1232"))

    def testAddItemsInDirWithTitle(self):
        with TemporaryDirectory() as tmpdir:
            test_item_dir = Path(tmpdir) / "RJ1232 with some titl"
            test_item_dir.mkdir()

            items = find_id.GetItemsInDir(tmpdir)
            self.assertIsNotNone(items.Find("RJ1232"))

    # Verify that all items under the directory are added.
    def testAddItemsGetAll(self):
        with TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "RJ23123").mkdir()
            (Path(tmpdir) / "RJ23").mkdir()
            (Path(tmpdir) / "RJ787").mkdir()
            (Path(tmpdir) / "VJ2333623").mkdir()
            (Path(tmpdir) / "RJ111").mkdir()

            items = find_id.GetItemsInDir(tmpdir)
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

    def testFindItems(self):
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            (dir_with_archives / "RJ1234").mkdir()
            (dir_with_archives / "RJ4321").mkdir()

            found = find_id.FindItems(str(dir_with_archives), set(["RJ1234"]))
            self.assertEqual(len(found), 1)

            found_ids = [item.item_id for item in found]
            self.assertIn("RJ1234", found_ids)

            found = find_id.FindItems(str(dir_with_archives), set(["RJ1234", "RJ4321"]))
            self.assertEqual(len(found), 2)

            found_ids = [item.item_id for item in found]
            self.assertIn("RJ1234", found_ids)
            self.assertIn("RJ4321", found_ids)

    def testFindItemsNotFound(self):
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            (dir_with_archives / "RJ1234").mkdir()
            found = find_id.FindItems(str(dir_with_archives), set(["RJ0232"]))
            self.assertEqual(len(found), 0)

    def testCheckAlreadyDownloadedOneItem(self):
        with TemporaryDirectory() as dir_with_archives:
            need_download = find_id.CheckAleadyDownloaded(
                set(["RJ3012"]), str(dir_with_archives)
            )

            self.assertEqual(need_download, set(["RJ3012"]))

    def testCheckAlreadyDownloadedMultipleItems(self):
        with TemporaryDirectory() as dir_with_archives:
            need_download = find_id.CheckAleadyDownloaded(
                set(["RJ3012", "RJ7761233"]), str(dir_with_archives)
            )

            self.assertEqual(
                need_download,
                set(["RJ3012", "RJ7761233"]),
            )

    def testCheckAlreadyDownloadedFoundItems(self):
        with TemporaryDirectory() as dir_with_archives:
            dir_with_archives = Path(dir_with_archives)
            (dir_with_archives / "RJ1234").mkdir()
            (dir_with_archives / "RJ4321").mkdir()
            (dir_with_archives / "RJ012112021").mkdir()

            need_download = find_id.CheckAleadyDownloaded(
                set(["RJ1234", "RJ04239", "RJ012112021"]), str(dir_with_archives)
            )
            self.assertEqual(need_download, set(["RJ04239"]))
