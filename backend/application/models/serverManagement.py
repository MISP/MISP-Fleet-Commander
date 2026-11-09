#!/usr/bin/env python3

from typing import List, Union
from application.DBModels import Server
from application.controllers.utils import mispPostRequest


def addUser(server: Server, payload: dict) -> Union[dict, None]:
    url = "/admin/users/add"
    response = mispPostRequest(server, url, payload or {})
    return response


def setPassword(server: Server, user_id: int, payload: dict) -> Union[dict, None]:
    url = f"/admin/users/edit/{user_id}"
    data = {
        'enable_password': True,
        'password': payload.get('password', None),
        'confirm_password': payload.get('confirm_password', None),
        'change_pw': 0,
    }
    # Raw, because MISP explains a refused password (policy) in the body of its 403
    response = mispPostRequest(server, url, data, rawResponse=True)
    if isinstance(response, dict):  # The request itself failed
        return response
    try:
        result = response.json()
    except ValueError:
        return {'error': f'Unexpected answer (HTTP {response.status_code})', '_status_code': response.status_code}
    if isinstance(result, dict):
        result.setdefault('_status_code', response.status_code)
    return result


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
