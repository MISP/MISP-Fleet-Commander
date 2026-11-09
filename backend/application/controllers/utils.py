#!/usr/bin/env python3
import json
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

MISP_CONNECT_TIMEOUT = 5  # Seconds to establish the connection
DEFAULT_MISP_READ_TIMEOUT = 60
READ_TIMEOUT_CACHE_SECONDS = 30
_readTimeoutCache = {'value': None, 'read_at': 0}


def mispReadTimeout() -> int:
    """`misp_request_timeout`, re-read from the settings file at most every 30 s so that every process (web and
    workers) follows a change without a restart"""
    now = time.monotonic()
    if _readTimeoutCache['value'] is None or now - _readTimeoutCache['read_at'] > READ_TIMEOUT_CACHE_SECONDS:
        import application.models.setting as settingModel
        try:
            value = int(settingModel.getRefreshValue('misp_request_timeout'))
        except (TypeError, ValueError, AttributeError):
            value = DEFAULT_MISP_READ_TIMEOUT
        _readTimeoutCache.update(value=value, read_at=now)
    return _readTimeoutCache['value']


def mispTimeout(timeout=None):
    """(connect, read) timeout of a MISP request: `timeout` when given (a number or a tuple), else the default"""
    if timeout is not None:
        return timeout
    return (MISP_CONNECT_TIMEOUT, mispReadTimeout())


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
def mispGetHTMLRequest(server, url, data={}, rawResponse=False, nocache=False, timeout=None):
    requestMISPSession = getMISPRequestSession()
    requestSession = getRequestPSession()

    headers = {
        "Authorization": server.authkey,
        "Accept": "text/html",
    }
    full_url = urljoin(server.url, url)
    try:
        if nocache:
            response = requestSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        else:
            response = requestMISPSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        error = handleStatusCode(response)
        if error is not None:
            return error
        if rawResponse:
            return response
        else:
            return response.text
    except requests.exceptions.SSLError as e:
        return { "error": "SSL error" }
    except requests.exceptions.ConnectTimeout:
        return { "error": "Server unreachable" }
    except requests.exceptions.Timeout:
        return { "error": "Request timed out" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }
    except Exception as e:
        return { "error": "Exception " + str(e) }


@timer
def mispGetRequest(server, url, data={}, rawResponse=False, nocache=False, timeout=None):
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
            response = requestSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        else:
            response = requestMISPSession.get(full_url, data=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        error = handleStatusCode(response)
        if error is not None:
            return error
        if rawResponse:
            return response
        else:
            jsonResponse = response.json()
            if type(jsonResponse) == dict:
                jsonResponse['_latency'] = response.elapsed.total_seconds()
                jsonResponse['_status_code'] = response.status_code
            return jsonResponse
    except requests.exceptions.SSLError as e:
        return { "error": "SSL error" }
    except requests.exceptions.ConnectTimeout:
        return { "error": "Server unreachable" }
    except requests.exceptions.Timeout:
        return { "error": "Request timed out" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }
    except Exception as e:
        return { "error": "Exception " + str(e) }


@timer
def mispPostRequest(server, url, data={}, rawResponse=False, nocache=True, timeout=None):
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
            response = requestSession.post(full_url, json=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        else:
            response = requestMISPSession.post(full_url, json=data, headers=headers, verify=(not getattr(server, 'skip_ssl', True)), timeout=mispTimeout(timeout))
        error = handleStatusCode(response)
        if error is not None:
            if rawResponse:
                return response
            else:
                return error
        if rawResponse:
            return response
        else:
            jsonResponse = response.json()
            if type(jsonResponse) is not dict:
                jsonResponse = { 'data': jsonResponse }
            jsonResponse['_latency'] = response.elapsed.total_seconds()
            jsonResponse['_status_code'] = response.status_code
            return jsonResponse
    except requests.exceptions.SSLError:
        return { "error": "SSL Error" }
    except requests.exceptions.ConnectTimeout:
        return { "error": "Server unreachable" }
    except requests.exceptions.Timeout:
        return { "error": "Request timed out" }
    except requests.exceptions.ConnectionError:
        return { "error": "Server unreachable" }
    except Exception as e:
        return { "error": "Exception " + str(e) }

def errorText(errors) -> str:
    """MISP and the plugins report errors as a string, a list, or a dict of field → messages"""
    if errors is None:
        return ''
    if isinstance(errors, str):
        return errors
    if isinstance(errors, dict):
        return '; '.join(f'{field}: {errorText(messages)}' for field, messages in errors.items())
    if isinstance(errors, (list, tuple)):
        return '; '.join(errorText(error) for error in errors if error not in (None, ''))
    return str(errors)


def misplabelledFailure(data) -> str:
    """MISP answers some refused writes with HTTP 200: `{"saved": false, "errors": …}`. The reason, or ''"""
    if isinstance(data, dict):
        if data.get('saved') is False or data.get('success') is False:
            return errorText(data.get('errors')) or data.get('message') or data.get('name') or 'Not saved'
        if data.get('errors'):
            return errorText(data.get('errors'))
    return ''


def responseJson(response):
    """The JSON body of a `requests.Response`, or None"""
    try:
        return response.json()
    except ValueError:
        return None


def mispRequestError(result):
    """Why the result of a request helper is a failure, or None when it is not. Covers the error dict returned when
    the request failed, an HTTP error status (raw responses), and a refusal MISP answered with HTTP 200"""
    if result is None:
        return 'No answer'
    if isinstance(result, dict):
        if 'error' in result:
            return errorText(result['error']) or 'Request failed'
        return misplabelledFailure(result) or None
    body = responseJson(result)
    if not result.ok:
        reason = ''
        if isinstance(body, dict):
            message = body.get('message') if isinstance(body.get('message'), str) else body.get('name')
            reason = ' - '.join(part for part in (message, errorText(body.get('errors'))) if part)
        status = f'HTTP {result.status_code} {result.reason or ""}'.strip()
        return f'{status}: {reason}' if reason else status
    return misplabelledFailure(body) or None


def handleStatusCode(response):
    if response.status_code == 403:
        return { "error": "Authentication error", "_status_code": response.status_code }
    if response.status_code == 405:
        return { "error": "Insufficent permission", "_status_code": response.status_code }
    if response.status_code == 400:
        return { "error" : "Bad Request", "_status_code": response.status_code }
    return None


def batchRequest(batch_request):
    result = []
    with concurrent.futures.ThreadPoolExecutor(35) as executor:
        future_to_serverid = {
            executor.submit(
                req['fn'], req['server'], req['path'], req.get('data', {}), rawResponse=req.get('rawResponse', False), nocache=req.get('nocache', False)
            ): (
                req['server'].id, req.get('passAlong', None),
            ) for req in batch_request
        }
        for future in concurrent.futures.as_completed(future_to_serverid):
            server_id, passAlong = future_to_serverid[future]
            try:
                data = future.result()
                data['timestamp'] = int(time.time())
                data['server_id'] = server_id
                if passAlong is not None:
                    data['_passAlong'] = passAlong
                result.append(data)
            except Exception as exc:
                print('%r generated an exception: %s' % (server_id, exc))
    return result
