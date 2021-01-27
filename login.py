import argparse
import requests
import http.cookiejar
import json
import logging

LOGIN_URL = 'https://login.dlsite.com/login'
MYPAGE_URL = 'https://ssl.dlsite.com/home/mypage'

def Login(username, password):
    """Logs into DLsite using the username and password.

    Returns:
        requests session. This can be further used as a "logged in" session.
    """

    session = requests.Session()
    session.get("https://login.dlsite.com/login")
    token = session.cookies.get_dict()['XSRF-TOKEN']

    payload = {
        '_token': token,
        'login_id': username,
        'password': password,
    }

    login_response = session.post(LOGIN_URL, data=payload)

    if login_response.status_code != requests.codes.ok:
        logging.error(f'Got status code {login_response.status_code} trying to login.')
        return None

    # Requires cookies from mypage.
    mypage_response = session.get(MYPAGE_URL)

    if mypage_response.status_code != requests.codes.ok:
        logging.error('Failed to get logged in mypage.')
        return None

    return session
