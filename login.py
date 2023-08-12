import requests
import logging

from requests.adapters import HTTPAdapter, Retry

LOGIN_URL = 'https://login.dlsite.com/login'
MYPAGE_URL = 'https://ssl.dlsite.com/home/mypage'

class LoginFailureException(Exception):
    pass

def Login(username: str, password: str) -> requests.Session:
    """Logs into DLsite using the username and password.

    Returns:
        requests session. This can be further used as a "logged in" session.
    """

    logging.info('Logging in.')
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
        logging.error(
            f'Got status code {login_response.status_code} trying to login.')
        raise LoginFailureException()

    # Requires cookies from mypage.
    mypage_response = session.get(MYPAGE_URL)

    if mypage_response.status_code != requests.codes.ok:
        logging.error('Failed to get logged in mypage.')
        raise LoginFailureException()

    # Not sure if this is absolutely necessary but does not seem to hurt.
    session.cookies.set('adultchecked', '1', domain='.dlsite.com', path='/')

    # Get cookies for play.dlsite.com.
    session.get('https://play.dlsite.com/')

    # Note that when visiting https://play.dlsite.com/ in a browser, it also
    # accesses https://play.dlsite.com/login. This gets redirected and seems to
    # get a bunch more cookie entries.
    # This may be useful when they start to require them.

    # Also https://play.dlsite.com/api/authorize is accessed but does not seem
    # to add any cookie entries.

    # Setup automatic retries for this session. Any http and https requests
    # using this session will have this retry configured.
    # It often gets status 500 and fails to get the content length. This should
    # recover after a few retries.
    retries = Retry(backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session
