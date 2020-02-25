#!/usr/bin/env python3
import requests
from urllib.parse import urljoin

def mispGetRequest(server, url, data={}):
    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    full_url = urljoin(server.url, url)
    try:
        response = requests.get(full_url, data=data, headers=headers, verify=(not server.skip_ssl))
        print(response.status_code)
        print(response.text)
        if response.status_code == 403:
            return { "error": "Authentication error" }
        if response.status_code == 405:
            return { "error": "Unsufficent permission" }
        return response.json()
    except requests.exceptions.SSLError:
        return { "error": "SSL error" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }


def mispPostRequest(server, url, data={}):
    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    full_url = urljoin(server.url, url)
    try:
        response = requests.post(full_url, data=data, headers=headers, verify=(not server.skip_ssl))
        if response.status_code == 403:
            return { "error": "Authentication error" }
        if response.status_code == 405:
            return { "error": "Unsufficent permission" }
        return response.json()
    except requests.exceptions.SSLError:
        return { "error": "SSL Error" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }