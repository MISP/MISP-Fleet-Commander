#!/usr/bin/env python3
from datetime import timedelta
import requests
import requests.adapters
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from requests_cache import CachedSession
import concurrent.futures
import time
from urllib.parse import urljoin
import functools

# requestMISPSession = CachedSession(cache_name='misp_cache', expire_after=timedelta(minutes=1))
# adapterCache = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
# requestMISPSession.mount('https://', adapterCache)
# requestMISPSession.mount('http://', adapterCache)

# requestSession = requests.Session()
# adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
# requestSession.mount('https://', adapter)
# requestSession.mount('http://', adapter)

# requestMISPSession = requestSession

def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        stop = time.perf_counter()
        duration = stop-start
        if duration > 3:
            print('{}: {} Took {:.2f}sec'.format(args[0].name, args[1], duration))
        return result
    return wrapper_timer

def getMISPRequestSession():
    requestMISPSession = CachedSession(cache_name='misp_cache', expire_after=timedelta(minutes=1))
    adapterCache = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
    requestMISPSession.mount('https://', adapterCache)
    requestMISPSession.mount('http://', adapterCache)
    return requestMISPSession

def getRequestPSession():
    requestSession = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=50)
    requestSession.mount('https://', adapter)
    requestSession.mount('http://', adapter)
    return requestSession


@timer
def mispGetRequest(server, url, data={}, rawResponse=False, nocache=False):
    requestMISPSession = getMISPRequestSession()
    requestSession = getRequestPSession()

    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    full_url = urljoin(server.url, url)
    try:
        if nocache:
            response = requestSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        else:
            response = requestMISPSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        error = handleStatusCode(response)
        if error is not None:
            return error
        if rawResponse:
            return response
        else:
            jsonResponse = response.json()
            if type(jsonResponse) == dict:
                jsonResponse['_latency'] = response.elapsed.total_seconds()
            return jsonResponse
        return response.json() if not rawResponse else response
    except requests.exceptions.SSLError as e:
        return { "error": "SSL error" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }
    except Exception as e:
        return { "error": "Unknown Exception " }


@timer
def mispPostRequest(server, url, data={}, rawResponse=False, nocache=True):
    requestMISPSession = getMISPRequestSession()
    requestSession = getRequestPSession()

    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    full_url = urljoin(server.url, url)
    try:
        if nocache:
            response = requestSession.post(full_url, json=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        else:
            response = requestMISPSession.post(full_url, json=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)))
        error = handleStatusCode(response)
        if error is not None:
            return error
        if rawResponse:
            return response
        else:
            jsonResponse = response.json()
            if type(jsonResponse) is not dict:
                jsonResponse = { 'data': jsonResponse }
            jsonResponse['_latency'] = response.elapsed.total_seconds()
            return jsonResponse
    except requests.exceptions.SSLError:
        return { "error": "SSL Error" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }
    except Exception as e:
        return { "error": "Exception " + str(e) }

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
    with concurrent.futures.ThreadPoolExecutor(35) as executor:
        future_to_serverid = {executor.submit(req['fn'], req['server'], req['path'], req.get('data', {})): req['server'].id for req in batch_request}
        starttimer = time.time()
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
