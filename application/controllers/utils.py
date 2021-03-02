#!/usr/bin/env python3
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import concurrent.futures
import time
from urllib.parse import urljoin

def mispGetRequest(server, url, data={}):
    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    full_url = urljoin(server.url, url)
    try:
        response = requests.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        error = handleStatusCode(response)
        if error is not None:
            return error
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
        response = requests.post(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        error = handleStatusCode(response)
        if error is not None:
            return error
        return response.json()
    except requests.exceptions.SSLError:
        return { "error": "SSL Error" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }

def handleStatusCode(response):
    if response.status_code == 403:
        return { "error": "Authentication error" }
    if response.status_code == 405:
        return { "error": "Insufficent permission" }
    if response.status_code == 400:
        return { "error" : "Bad Request" }
    return None


def batchRequest(batch_request):
    result = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_serverid = {executor.submit(req['fn'], req['server'], req['path'], req.get('data', {})): req['server'].id for req in batch_request}
        for future in concurrent.futures.as_completed(future_to_serverid):
            server_id = future_to_serverid[future]
            try:
                data = future.result()
                data['timestamp'] = int(time.time())
                data['server_id'] = server_id
                result.append(data)
            except Exception as exc:
                print('%r generated an exception: %s' % (server_id, exc))
    return result
