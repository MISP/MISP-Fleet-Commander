#!/usr/bin/env python3

from typing import List, Union
from application.DBModels import Server
from application.controllers.utils import mispPostRequest


def addUser(server: Server, payload: dict) -> Union[dict, None]:
    return


def setPassword(server: Server, user_id: int, payload: dict) -> Union[dict, None]:
    return


def resetPassword(server: Server, user_id: int) -> Union[dict, None]:
    return


def resetAuthkey(server: Server, user_id: int) -> Union[dict, None]:
    return


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
