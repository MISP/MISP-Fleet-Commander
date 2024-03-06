#!/usr/bin/env python3

from typing import List, Union
from application.DBModels import Server
from application.controllers.utils import mispPostRequest


def addUser(server: Server, payload: dict) -> Union[dict, None]:
    return


def setPassword(server: Server, user_id: int, payload: dict) -> Union[dict, None]:
    url = f"/admin/users/edit/{user_id}"
    data = {
        'enable_password': True,
        'password': payload.get('password', None),
        'confirm_password': payload.get('confirm_password', None),
        'change_pw': 0,
    }
    response = mispPostRequest(server, url, data, rawResponse=True)
    if response.status_code == 403:
        return response.json()
    return response.json()


def resetPassword(server: Server, user_id: int) -> Union[dict, None]:
    url = f"/users/initiatePasswordReset/{user_id}"
    payload = {
        'user_id': user_id,
        'firstTime': 0,
    }
    response = mispPostRequest(server, url, payload)
    return response


def genAuthkey(server: Server, user_id: int) -> Union[dict, None]:
    url = f"/auth_keys/add/{user_id}"
    payload = {
        'user_id': user_id,
    }
    response = mispPostRequest(server, url, payload)
    return response


def disable(server: Server, user_id: int) -> Union[dict, None]:
    url = f"/admin/users/edit/{user_id}"
    payload = {
        'disabled': True,
    }
    response = mispPostRequest(server, url, payload)
    return response


def enable(server: Server, user_id: int) -> Union[dict, None]:
    url = f"/admin/users/edit/{user_id}"
    payload = {
        'disabled': False,
    }
    response = mispPostRequest(server, url, payload)
    return response
