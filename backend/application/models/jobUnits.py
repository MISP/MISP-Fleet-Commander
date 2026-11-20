#!/usr/bin/env python3
"""What a job does on one server, per kind. Each executor takes a server and the job's parameters and returns a
UnitResult; it never raises (`execute` turns an unexpected exception into an error result)"""

import json
import time
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit

import application
import application.models.plugins as pluginsModel
from application.DBModels import Server
from application.controllers.utils import errorText, misplabelledFailure, mispGetRequest, mispPostRequest
from application.models import organisations, serverManagement, sharingGroups
from application.models.jobs import UnitResult


def isRelativePath(url: Any) -> bool:
    """MISP paths only: an absolute URL (or `//host`) would send the server's authkey to another host"""
    if not isinstance(url, str) or url.strip() == '':
        return False
    parts = urlsplit(url.strip())
    return parts.scheme == '' and parts.netloc == '' and not url.strip().startswith('//')


def statusOf(response: Any) -> Optional[int]:
    if isinstance(response, dict):
        status = response.get('_status_code', response.get('status_code'))
        return status if isinstance(status, int) else None
    return None


def responseAsDict(response, server_id: Optional[int] = None) -> dict:
    """The request details the UI shows for raw queries, from a `requests.Response` or a request helper's error"""
    if isinstance(response, dict):
        return response
    try:
        data = response.json()
    except (json.decoder.JSONDecodeError, ValueError):
        data = response.text
    result = {
        'timestamp': int(time.time()),
        'data': data,
        'headers': dict(response.headers),
        'status_code': response.status_code,
        'reason': response.reason,
        'elapsed_time': str(response.elapsed),
        'url': response.url,
    }
    if server_id is not None:
        result['server_id'] = server_id
    return result


def requestUnit(response: dict) -> UnitResult:
    """A UnitResult from `responseAsDict`'s output"""
    if 'error' in response and 'status_code' not in response:
        return UnitResult(False, http_status=statusOf(response), summary=errorText(response['error']),
                          response=response)
    status = response.get('status_code')
    ok = isinstance(status, int) and 200 <= status < 300
    failure = misplabelledFailure(response.get('data'))
    summary = f"{status} {response.get('reason') or ''}".strip()
    if failure:
        ok = False
        summary = f'{summary}: {failure}'
    return UnitResult(ok, http_status=status, summary=summary, response=response)


# Plugins

def fromPluginResponse(response: dict) -> UnitResult:
    """A success that reports errors (e.g. 2 of 5 taxonomies could not be enabled) is an error: the server is not
    in the requested state, and retrying the failed servers should include it"""
    errors = errorText(response.get('error'))
    ok = response.get('status') == 'success' and not errors
    requestResponse = response.get('request_response') or {}
    data = response.get('data')
    summary = errors
    if isinstance(data, dict) and isinstance(data.get('message'), str):
        summary = f"{data['message']} ({errors})" if errors else data['message']
    if not summary:
        summary = 'Done' if ok else 'Failed'
    return UnitResult(ok, http_status=requestResponse.get('status_code'), summary=summary, response=response)


def pluginUnit(server: Server, params: dict, quick: bool = False) -> UnitResult:
    pluginID = params.get('plugin_id')
    plugin = pluginsModel.getPluginFromID(application.loadedPlugins or [], pluginID)
    feature = 'quickAction' if quick else 'action'
    if plugin is None:
        return UnitResult(False, summary=f'Unknown plugin `{pluginID}`')
    if not plugin.get('features', {}).get(feature):
        return UnitResult(False, summary=f'Plugin `{pluginID}` has no {"quick action" if quick else "action"}')
    doIt = pluginsModel.doQuickAction if quick else pluginsModel.doAction
    return fromPluginResponse(doIt(server, plugin, params.get('data')))


def pluginActionUnit(server: Server, params: dict) -> UnitResult:
    return pluginUnit(server, params, quick=False)


def pluginQuickActionUnit(server: Server, params: dict) -> UnitResult:
    return pluginUnit(server, params, quick=True)


# Raw REST queries

def restQuery(server: Server, method: str, url: str, data: Any = None) -> dict:
    """Send a raw query to the server: the request details, or `{"error": …}`"""
    if not isRelativePath(url):
        return {'error': 'The URL must be a path on the MISP server, such as /servers/getVersion'}
    method = (method or 'GET').upper()
    if method == 'POST':
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                pass
        response = mispPostRequest(server, url, data if data is not None else {}, rawResponse=True, nocache=True)
    elif method == 'GET':
        response = mispGetRequest(server, url, rawResponse=True, nocache=True)
    else:
        return {'error': f'Unsupported method `{method}`'}
    return responseAsDict(response, server.id)


def restQueryUnit(server: Server, params: dict) -> UnitResult:
    return requestUnit(restQuery(server, params.get('method'), params.get('url'), params.get('data')))


# Remote Admin (users, organisations and sharing groups of a MISP server)

SERVER_MANAGEMENT_OPERATIONS: Dict[str, Callable] = {
    'add_user': lambda server, params: serverManagement.addUser(server, params.get('payload') or {}),
    'set_password': lambda server, params: serverManagement.setPassword(server, params.get('user_id'),
                                                                        params.get('payload') or {}),
    'reset_password': lambda server, params: serverManagement.resetPassword(server, params.get('user_id')),
    'gen_authkey': lambda server, params: serverManagement.genAuthkey(server, params.get('user_id')),
    'disable': lambda server, params: serverManagement.disable(server, params.get('user_id')),
    'enable': lambda server, params: serverManagement.enable(server, params.get('user_id')),
    'add_organisation': organisations.addOperation,
    'edit_organisation': organisations.editOperation,
    'add_sharing_group': sharingGroups.addOperation,
    'edit_sharing_group': sharingGroups.editOperation,
    'delete_sharing_group': sharingGroups.deleteOperation,
}
# Operations on one user of the MISP server
USER_OPERATIONS = ('set_password', 'reset_password', 'gen_authkey', 'disable', 'enable')


def serverManagementUnit(server: Server, params: dict) -> UnitResult:
    operation = SERVER_MANAGEMENT_OPERATIONS.get(params.get('operation'))
    if operation is None:
        return UnitResult(False, summary=f"Unknown operation `{params.get('operation')}`")
    if params.get('operation') in USER_OPERATIONS and not isinstance(params.get('user_id'), int):
        return UnitResult(False, summary='A user ID is required')
    result = operation(server, params)
    if not isinstance(result, dict):
        return UnitResult(False, summary='Unexpected answer', response={'data': result})
    status = statusOf(result)
    if 'error' in result:
        return UnitResult(False, http_status=status, summary=errorText(result['error']), response=result)
    failure = misplabelledFailure(result)
    if failure or (status is not None and status >= 400):
        message = result.get('message') if isinstance(result.get('message'), str) else ''
        summary = ' - '.join(part for part in (message, failure) if part) or f'HTTP {status}'
        return UnitResult(False, http_status=status, summary=summary, response=result)
    return UnitResult(True, http_status=status, summary='Done', response=result)


# Sync connections

def editConnection(server: Server, remote_server_id: int, payload: dict) -> dict:
    response = mispPostRequest(server, f'/servers/edit/{remote_server_id}', data=payload or {}, rawResponse=True,
                               nocache=True)
    return responseAsDict(response, server.id)


def editConnectionUnit(server: Server, params: dict) -> UnitResult:
    remoteServerID = params.get('remote_server_id')
    if not isinstance(remoteServerID, int):
        return UnitResult(False, summary='A sync connection ID is required')
    return requestUnit(editConnection(server, remoteServerID, params.get('payload') or {}))


def organisationCopyUnit(server: Server, params: dict) -> UnitResult:
    return organisations.copyUnit(server, params)


def sharingGroupCopyUnit(server: Server, params: dict) -> UnitResult:
    return sharingGroups.copyUnit(server, params)


def baselineRemediationUnit(server: Server, params: dict) -> UnitResult:
    from application.models.baselineRemediation import remediationUnit
    return remediationUnit(server, params)


def mispqlQueryUnit(server: Server, params: dict, job_id: Optional[str] = None) -> UnitResult:
    from application.models import fleetQueries
    return fleetQueries.run(server, params, job_id)


EXECUTORS: Dict[str, Callable[[Server, dict], UnitResult]] = {
    'plugin_action': pluginActionUnit,
    'plugin_quick_action': pluginQuickActionUnit,
    'rest_query': restQueryUnit,
    'server_management': serverManagementUnit,
    'edit_connection': editConnectionUnit,
    'baseline_remediation': baselineRemediationUnit,
    'organisation_copy': organisationCopyUnit,
    'sharing_group_copy': sharingGroupCopyUnit,
    'mispql_query': mispqlQueryUnit,
}
# Executors that keep data under their job's ID (a query's rows), and so are given it
WITH_JOB_ID = ('mispql_query',)


def execute(kind: str, server: Server, params: dict, job_id: Optional[str] = None) -> UnitResult:
    executor = EXECUTORS.get(kind)
    if executor is None:
        return UnitResult(False, summary=f'Unknown job kind `{kind}`')
    try:
        if kind in WITH_JOB_ID:
            return executor(server, params or {}, job_id)
        return executor(server, params or {})
    except Exception as e:
        if application.flaskApp is not None:
            application.flaskApp.logger.exception(f'Job unit `{kind}` failed on server {server.id}')
        return UnitResult(False, summary=f'Unexpected error: {e}')
