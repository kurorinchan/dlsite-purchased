# Since their API is not quite consistent with what they mean for "work ID",
# this document uses "item ID" or just "item" to mean the unique identifier
# for the item. E.g. RJ123456 is an "item ID".

# Creating a list:
# POST to https://play.dlsite.com/api/mylist/update_mylist
# with data
#   type: create
#   mylist_name: 新しいマイリスト
# Note that the name is probably the default created by the browser client.
# The response is a JSON like
# {result: true, mylist_id: 1891389}
# Note that the number is made up for the purpose of this comment.
# Response looks like
# {"result":true,"mylist_id":1891389}

# Updating the list name:
# POST to https://play.dlsite.com/api/mylist/update_mylist
# with data:
#   type: rename
#   mylist_id: 1891389
#   mylist_name: ☆
# The new name is specified in mylist_name
# Response looks like
# {"result":true,"mylist_id":1891389}

# Adding an item to a list:
# POST to https://play.dlsite.com/api/mylist/update_mylist_work
# with data:
#   type: add
#   mylist_id: 1891389
#   workno: RJ9876
# Response looks like
# {
#     "result": true,
#     "mylist_id": 1891389,
#     "mylist_work_id": 1,
#     "workno": "RJ9876"
# }

# Deleting item from a list:
# POST to https://play.dlsite.com/api/mylist/update_mylist_work
# with data:
#   type: delete
#   mylist_id: 1891389
#   mylist_work_id: 0
# mylist_work_id is the index of the deleted item in the list. So deleting the
# first item mylist_work_id == 0. Deleting the 3rd item is mylist_work_id == 2.
# The rsponse looks like
# {"result":true,"mylist_id":1891389,"mylist_work_id":"0"}

# Deleting a list:
# POST to https://play.dlsite.com/api/mylist/update_mylist
# with data:
#   type: delete
#   mylist_id: 1891389
# This deletes the list. Regardless of whether there are items in the list.
# Response looks like {"result":true,"mylist_id":1891389}

# Updating the order of items in list:
# POST to https://play.dlsite.com/api/mylist/update_mylist_work
# with data:
#   type: order
#   mylist_id: 6543
#   new_order: 0,1,2,3,4,5,6,7,8,9,10,12,11
# This list has 13 items.
# The last two items were swapped.
# Note that ths mylist_work_ids of these items are not necessarily in the
# range [0-12].
# So this means the numbers are just (0-start) indecies of the items in the
# list.

# Getting lists:
# Getting mylists is at https://play.dlsite.com/api/mylist/mylists?sync=true
# The response is a JSON.
# An empty list looks like
# {
#     "mylists": [{
#         "id": 1891389,
#         "mylist_name": "\u65b0\u3057\u3044\u30de\u30a4\u30ea\u30b9\u30c8",
#         "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
#         "mylist_work_id": []
#     }],
#     "mylist_works": []
# }
#
# A non empty list looks like.
# {
#     "mylists": [{
#         "id": 1891389,
#         "mylist_name": "\u2606",
#         "insert_date": "Sun, 31 Jan 2021 06:42:26 +0900",
#         "mylist_work_id": ["0"]
#     }],
#     "mylist_works": ["RJ285384"]
# }
#
# Fields:
# |mylist_works| contain all the work IDs in all the lists (any list).
#                There may be duplicates.
# |insert_date| is the date the list was created.
# |mylist_work_id| in each list is the index into |mylist_works|. This is why
# |mylist_works| may contain duplicates.

import requests
import logging

# Not the best name, but this URL is for editing the actual list object.
# For example creating a list, renaming a list, and deleting a list.
# This is NOT for updating the items inside a list.
_LIST_CREATE_URL = "https://play.dlsite.com/api/mylist/update_mylist"

# This URL is for updating the ITEMS within a list.
_LIST_UPDATE_URL = "https://play.dlsite.com/api/mylist/update_mylist_work"
_MYLIST_GET_URL = "https://play.dlsite.com/api/mylist/mylists?sync=true"

MYLIST_WORK_ID = "mylist_work_id"
MYLISTS = "mylists"
MYLIST_WORKS = "mylist_works"
_MYLIST_NAME = "mylist_name"
_ID = "id"
_INSERT_DATE = "insert_date"


# Converts item ID to index in the list.
def _ListItemIndex(mylist, item_id):
    mylist_item_ids = mylist.item_ids
    for i in range(len(mylist_item_ids)):
        if mylist_item_ids[i] == item_id:
            return i
    return len(mylist_item_ids)


class MyList:
    def __init__(self, id, name, creation_date, item_ids) -> None:
        self.id = str(id)
        self.name = name
        self.creation_date = creation_date
        self.item_ids = item_ids


class MyListEditor:
    def __init__(self, session: requests.Session) -> None:
        self.session = session

    def GetListFromListId(self, list_id):
        lists = self.GetLists()
        for list in lists:
            if list.id == list_id:
                return list
        return None

    def GetListsFromListName(self, list_name):
        lists = self.GetLists()
        return [list for list in lists if list.name == list_name]

    def GetLists(self):
        """Returns a list of MyList objects."""
        response = self.session.get(_MYLIST_GET_URL)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to get mylists.")
            return []

        json_response = response.json()

        mylists = []

        # For each list, change mylist_work_id to actually point ot the work
        # ID.
        ids = json_response[MYLIST_WORKS]
        for mylist_json in json_response[MYLISTS]:
            list_as_item_ids = []
            for work_id in mylist_json[MYLIST_WORK_ID]:
                # The json contains the indicies as strings.
                work_id = int(work_id)
                list_as_item_ids.append(ids[work_id])

            mylist = MyList(
                str(mylist_json[_ID]),
                mylist_json[_MYLIST_NAME],
                mylist_json[_INSERT_DATE],
                list_as_item_ids,
            )
            mylists.append(mylist)

        return mylists

    def CreateNewList(self, name):
        data = {
            "type": "create",
            "mylist_name": name,
        }
        response = self.session.post(_LIST_CREATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to create list {name}.")
            return False

        # Comparing against True just incase they change the values from
        # true/false to something else.
        return response.json()["result"] == True

    def UpdateListName(self, list_id, new_name):
        data = {
            "type": "rename",
            "mylist_id": list_id,
            "mylist_name": new_name,
        }
        response = self.session.post(_LIST_CREATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to rename to {new_name}.")
            return False
        return response.json()["result"] == True

    def UpdateListItemOrder(self, list_id, new_order):
        list = self.GetListFromListId(list_id)
        logging.info(f"updating list {list}")
        if len(list[MYLIST_WORK_ID]) != len(new_order):
            logging.error(
                f"New order length {len(new_order)} is different from the "
                f"current list length {len(list[MYLIST_WORK_ID])}."
            )
            return False

        if list[MYLIST_WORK_ID] == new_order:
            logging.warning(f"The current list and new order are the same.")
            return True

        if set(list[MYLIST_WORK_ID]) != set(new_order):
            logging.error(
                f"The new order {new_order} has a different set of items from "
                f"the current list {list[MYLIST_WORK_ID]}."
            )
            return False

        original_order = list[MYLIST_WORK_ID]
        order_dict = {}
        for i in range(len(original_order)):
            order_dict[original_order[i]] = i

        new_order_index = []
        for new_order_item in new_order:
            new_order_index.append(order_dict[new_order_item])

        data = {
            "type": "order",
            "mylist_id": list_id,
            "new_order": ",".join([str(index) for index in new_order_index]),
        }
        response = self.session.post(_LIST_UPDATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to reorder items to {new_order_index}.")
            return False
        return response.json()["result"] == True

    def AddItemToList(self, item_id, list_id):
        data = {
            "type": "add",
            "mylist_id": list_id,
            "workno": item_id,
        }
        response = self.session.post(_LIST_UPDATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to add item {item_id} to {list_id}.")
            return False
        return response.json()["result"] == True

    def _DeleteItemFromListWithIndex(self, index, list_id):
        # This is relatively difficult ot use. DeleteItemFromList is easier.
        data = {
            "type": "delete",
            "mylist_id": list_id,
            "mylist_work_id": str(index),
        }
        response = self.session.post(_LIST_UPDATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to delete item {index} from {list_id}.")
            return False
        return response.json()["result"] == True

    def DeleteItemFromList(self, item_id, list):
        # This takes an actual list returned from GetLists().
        list_name = list.name
        index = _ListItemIndex(list, item_id)
        logging.info(f"Attempting to delete {item_id}:{index} from {list_name}.")
        return self._DeleteItemFromListWithIndex(index, list.id)

    def DeleteItemFromListId(self, item_id, list_id):
        list = self.GetListFromListId(list_id)
        if not list:
            logging.error(f"Failed to find list with ID {list_id}")
            return False
        return self.DeleteItemFromList(item_id, list)

    def DeleteItemFromListName(self, item_id, list_name):
        lists = self.GetListsFromListName(list_name)
        all_succeeded = True
        for list in lists:
            if not self.DeleteItemFromList(item_id, list):
                logging.error(f"Failed to delete {item_id} from {list[_MYLIST_NAME]}")
                all_succeeded = False
        return all_succeeded

    def DeleteList(self, list_id):
        data = {
            "type": "delete",
            "mylist_id": list_id,
        }
        response = self.session.post(_LIST_CREATE_URL, data=data)
        if response.status_code != requests.codes.ok:
            logging.error(f"Failed to delete list {list_id}.")
            return False
        return response.json()["result"] == True
