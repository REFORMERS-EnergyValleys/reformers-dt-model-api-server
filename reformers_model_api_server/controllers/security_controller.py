import os
from datetime import datetime, timezone
# from typing import List

DEFAULT_PASSWORD = 'REFORMERS'
PASSWORD = os.environ.get('PASSWORD', DEFAULT_PASSWORD)

def info_from_bearer_auth(token):
    """
    Check and retrieve authentication information from custom bearer token.
    Returned value will be passed in 'token_info' parameter of your operation function, if there is one.
    'sub' or 'uid' will be set in 'user' parameter of your operation function, if there is one.

    :param token Token provided by Authorization header
    :type token: str
    :return: Decoded token information or None if token is invalid
    :rtype: dict | None
    """
    return {'authorized': True, 'auth_time': datetime.now(timezone.utc)} if token == PASSWORD else None
