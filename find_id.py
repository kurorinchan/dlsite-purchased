import argparse
from dataclasses import dataclass
import os
import pathlib
from typing import List, Set, Tuple

# TODO: This should be configurable.
_WATCHED_DIR_NAME = "視聴済み"


@dataclass
class Item:
    """Class representing an item.

    dir is the whole directory name that the item is contained in. (This does
        not require further processing to get the actual directory, i.e.
        item_id and prefix is in this path.)
    item_id is the item ID of the item.
    prefix it any symbols that prefix the item ID.

    """

    directory: pathlib.Path
    item_id: str
    prefix: str


# Split the name by any number of '#' with the rest.
def _SplitPrefix(name):
    """Split the given name by any number of '#' or '!'.

    If no such prefix is found, an empty string is returned as the first
    element of the tuple and the original name as the second element.

    Args:
        name (str): The name to be split.

    Returns:
        Tuple[str, str]: A tuple containing the prefix and the rest of the
        name, respectively.

    """

    for i in range(len(name)):
        if name[i] != "#" and name[i] != "!":
            return name[:i], name[i:]

    return "", name


# Split the name by a valid prefix followed by the rest. If there isn't a
# valid prefix, the first item returned is an empty string.
def _SplitByCategoryPrefix(name):
    POSSIBLE_ITEM_PREFIXES = ["RJ", "VJ", "BJ"]
    for item_prefix in POSSIBLE_ITEM_PREFIXES:
        if name.startswith(item_prefix):
            return item_prefix, name[len(item_prefix) :]
    return "", name


# Split the the number prefix in |name|. If the prefix is not a number,
# returns an empty string.
def _SplitByNumber(name: str) -> Tuple[str, str]:
    """Split the the number prefix in |name|. If the prefix is not a number,
    returns an empty string.

    Args:
        name (str): The name to be split.

    Returns:
        Tuple[str, str]: A tuple containing the number prefix and the rest of the
        name, respectively. If the prefix is not a number, the first element is an
        empty string.
    """
    if name.isnumeric():
        return name, ""
    for i in range(len(name)):
        ch = name[i]
        if not ch.isdigit():
            return name[:i], name[i:]

    return "", name


class Items:
    def __init__(self) -> None:
        self.items = {}

    def Add(self, directory: pathlib.Path):
        name = directory.name
        prefix, name = _SplitPrefix(name)
        category, name = _SplitByCategoryPrefix(name)

        if not category:
            return

        item_num, _ = _SplitByNumber(name)
        if not item_num.isnumeric():
            return
        id = category + item_num
        self.items[id] = Item(directory, id, prefix)

    def Find(self, id: str) -> Item | None:
        """Find an item by its ID.

        Args:
            id (str): The ID of the item.

        Returns:
            Optional[Item]: The found item, or None if not found.
        """
        return self.items.get(id)

    def GetItemsAsList(self) -> List[Item]:
        return list(self.items.values())


def _AddItemsInDir(directory: pathlib.Path, items: Items):
    """Add all the subfolders under the directory to the items.

    Args:
        directory (pathlib.Path): The directory to start searching from.
        items (Items): The items to add the subfolders to.

    Returns:
        None
    """

    subfolders = [d for d in directory.iterdir() if d.is_dir()]
    for subfolder in subfolders:
        items.Add(subfolder)


def GetItemsInDir(directory: str | pathlib.Path) -> Items:
    """Get items in the directory and its subdirectories.

    This function searches for all the subfolders under the directory and
    adds them to the `items` as `Item` objects. The `Items` object contains
    all the found items.

    Args:
        directory (str): The directory to start searching from.

    Returns:
        Items: The items in the directory and its subdirectories.
    """

    items = Items()
    watched = pathlib.Path(directory) / _WATCHED_DIR_NAME
    if watched.is_dir():
        _AddItemsInDir(watched, items)
    _AddItemsInDir(pathlib.Path(directory), items)
    return items


def CheckAleadyDownloaded(items_to_download: Set[str], management_dir: str) -> Set[str]:
    """Checks whether the item has been downloaded already.

    Args:
        items_to_download is the ids that are requested for download.
        management_dir is the directory to check whether the items are present.

    Returns:
        A set of item ids that is not in the management_dir (not downloaded).
    """
    items = FindItems(management_dir, items_to_download)

    for item in items:
        print(f"Skipping {item.item_id}. Already at {item.directory}.")

    return items_to_download - set(item.item_id for item in items)


def FindItems(directory: str, ids: Set[str]) -> List[Item]:
    """Returns a list of items found.

    Args:
        directory is the target directory for checking whether the ids are
            already present (downloaded).
        ids is the list of ids to look for under the directory.

    Returns:
        A list of items that were found under the specified directory, specified
        by ids argument. If the item is not found, then it would not be in
        the list.
    """
    items = GetItemsInDir(directory)

    found_items = []
    for id in ids:
        item = items.Find(id)
        if item:
            found_items.append(item)

    return found_items


def GetAllItemPaths(directory: str) -> List[pathlib.Path]:
    """Returns a list of paths to items under directory.

    Returns:
        A list of paths of items under directory. This contains all watched
        items too.
    """
    items = GetItemsInDir(directory)
    return [pathlib.Path(item.directory) for item in items.GetItemsAsList()]


def GetAllWatchedItemPaths(directory: str) -> List[pathlib.Path]:
    """Returns a list of watched item paths to under directory.

    The directory should be the top directory that contians all items, i.e.
    the magament directory. This will explore the watched items directory and
    returns list.

    Args:
        directory is the top level directory that contains all the items.

    Returns:
        A list of paths of items under directory. This contains all watched
        items too.
    """
    items = GetItemsInDir(os.path.join(directory, _WATCHED_DIR_NAME))
    return [pathlib.Path(item.directory) for item in items.GetItemsAsList()]


def GetAllWatchedItems(directory: str) -> List[Item]:
    """Same as GetAllWatchedItemPaths() but returns Item objects."""
    items = GetItemsInDir(os.path.join(directory, _WATCHED_DIR_NAME))
    return items.GetItemsAsList()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("ids", nargs="+")

    args = parser.parse_args()
    items = FindItems(args.directory, args.ids)
    for item in items:
        print(f"{item.item_id}: {item.directory} prefix:{item.prefix}")
