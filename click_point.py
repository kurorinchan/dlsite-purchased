# Do a get request to the following url with cookies.
# https://www.dlsite.com/maniax/event/dlfarm/ajax?act=draw

from http import HTTPStatus
import logging
from requests import Session
from datetime import datetime, timezone
import pytz


_DLFARM_CLICK_URL = "https://www.dlsite.com/maniax/event/dlfarm/ajax?act=draw"
_JST = pytz.timezone("Asia/Tokyo")


def ClickForPoints(session: Session) -> bool:
    response = session.get(_DLFARM_CLICK_URL)
    logging.info(f"click response: {response.text}")
    if response.status_code != HTTPStatus.OK:
        print(f"Got HTTP status {response.status_code}. Something went wrong.")
        return False
    res_json = response.json()
    if "class" not in res_json:
        print(f"Unknown response {res_json}")
        return False

    if "name" not in res_json:
        print("Result name not found. Maybe you have claimed it already?")
        return False

    result_name = response.json()["name"]
    jst_time = datetime.now(timezone.utc).astimezone(_JST).isoformat()
    print(f"Japan time: {jst_time}\nGot {result_name}")
    return True
