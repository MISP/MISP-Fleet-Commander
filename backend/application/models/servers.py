#!/usr/bin/env python3

import asyncio
from datetime import datetime, timedelta, timezone
import json
import time
from typing import List, Union
import concurrent.futures

from application import flaskApp
from application import redisClient, redisModel
from application.DBModels import db, User, Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.marshmallowSchemas import ServerSchema, serverQuerySchema

from application.models.utils import MonitoringImages, asyncFetcher, asyncFetcherManyServer

import nest_asyncio
nest_asyncio.apply()


MONITORING_PANELS = [
    { 'panel_id': 'panel-7', 'alt_title': '# Events (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-8', 'alt_title': '# Objects (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-23', 'alt_title': '# Attributes (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-30', 'alt_title': '# Event Reports  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-29', 'alt_title': '# Analyst Data  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-9', 'alt_title': '# Proposals  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-10', 'alt_title': '# Correlation  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-5', 'alt_title': '# Organisations  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-17', 'alt_title': '# Users  (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-16', 'alt_title': 'Users / Org Ratio', 'width': 200, 'height': 150, 'relative_time_days': 1 },
    { 'panel_id': 'panel-15', 'alt_title': '# Users with PGP', 'width': 200, 'height': 150, 'relative_time_days': 1 },
    { 'panel_id': 'panel-13', 'alt_title': '# Local / Global Org ratio', 'width': 200, 'height': 150, 'relative_time_days': 1 },
    { 'panel_id': 'panel-18', 'alt_title': '# Open registration (Last 3 months)', 'width': 200, 'height': 150, 'relative_time_days': 3*31 },
    { 'panel_id': 'panel-14', 'alt_title': 'Contributing Org (Last year)', 'width': 200, 'height': 150, 'relative_time_days': 365} ,
    { 'panel_id': 'panel-2', 'alt_title': '# Data Amount over time (Last year)', 'width': 600, 'height': 300, 'relative_time_days': 365 },
    { 'panel_id': 'panel-1', 'alt_title': 'Login over time (Last year)', 'width': 600, 'height': 300, 'relative_time_days': 365 },
    { 'panel_id': 'panel-3', 'alt_title': 'Login Heatmap (Last 14 days)', 'width': 800, 'height': 600, 'relative_time_days': 14 },
    { 'panel_id': 'panel-32', 'alt_title': 'Load avg medium', 'width': 200, 'height': 150, 'relative_time_days': 365 },
    { 'panel_id': 'panel-33', 'alt_title': 'RAM Usage', 'width': 200, 'height': 150, 'relative_time_days': 365 },
    { 'panel_id': 'panel-34', 'alt_title': 'Disk Usage', 'width': 200, 'height': 150, 'relative_time_days': 365 },
    { 'panel_id': 'panel-20', 'alt_title': 'Redis Memory Usage (Last 7 days)', 'width': 600, 'height': 300, 'relative_time_days': 7 },
    { 'panel_id': 'panel-35', 'alt_title': 'MySQL Memory Usage (Last 7 days)', 'width': 200, 'height': 150, 'relative_time_days': 7 },
    { 'panel_id': 'panel-26', 'alt_title': 'Workers Queues (Last 7 days)', 'width': 600, 'height': 300, 'relative_time_days': 7 },
    { 'panel_id': 'panel-19', 'alt_title': 'Top 5 Endpoint Daily Time', 'width': 600, 'height': 300, 'relative_time_days': 1 },
    { 'panel_id': 'panel-21', 'alt_title': 'Top 5 Endpoint Daily SQL Time', 'width': 600, 'height': 300, 'relative_time_days': 1 },
    { 'panel_id': 'panel-22', 'alt_title': 'Top 5 Endpoint Daily Memory', 'width': 600, 'height': 300, 'relative_time_days': 1 },
]
MONITORING_PANEL_BY_ID = {}
for panel in MONITORING_PANELS:
    MONITORING_PANEL_BY_ID[panel['panel_id']] = panel


def index(fleet_id=None):
    q = Server.query
    if fleet_id is not None:
        q = q.filter_by(fleet_id=fleet_id)
    servers = q.all()
    return servers

def indexForUser(user, fleet_id=None):
    q = Server.query
    q = q.filter_by(user_id=user.id)
    if fleet_id is not None:
        q = q.filter_by(fleet_id=fleet_id)
    servers = q.all()
    return servers

def get(server_id: int):
    q = Server.query
    q = q.filter_by(id=server_id)
    server = q.first()
    return server

def getForUser(user, server_id: int):
    q = Server.query
    q = q.filter_by(user_id=user.id, id=server_id)
    server = q.first()
    return server

def searchAll(text: str, user) -> List:
    search = "%{}%".format(text)
    q = Server.query
    q = q.filter_by(user_id=user.id)
    q = q.filter(
        (Server.name.ilike(search)) |
        (Server.url.ilike(search)) |
        (Server.comment.ilike(search))
    )
    servers = q.limit(10).all()
    return servers

def recordConnectionTest(server, testConnection):
    """Timestamp a connection test result and persist it, so that the last known state outlives the request"""
    if isinstance(testConnection, dict):
        testConnection['timestamp'] = int(time.time())
    redisModel.saveServerStatus(server.uuid, testConnection)
    publishHealth(server)
    return testConnection


def publishHealth(server):
    """Send the server's re-evaluated health to its owner, once its new data is saved"""
    from application.models.health import publishServerHealth
    publishServerHealth(server)

def testConnection(server_id: int, use_cache=True) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        return recordConnectionTest(server, mispGetRequest(server, '/servers/getVersion', nocache=not use_cache))
    else:
        return None

def testConnectionAsync(server_id: int) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        urls = [
            '/servers/getVersion',
        ]
        results = asyncio.run(asyncFetcher(server, urls))
        if results is None:
            return None
        return recordConnectionTest(server, results[0])
    else:
        return None

def testAllConnectionAsync(servers: list, clientSocketEmitterUpdateFun, max_concurrency=None, timeout=300):
    url = '/servers/getVersion'
    serverByID = {server.id: server for server in servers}

    def recordAndForward(server_id, testResult):
        if not isinstance(testResult, dict):
            testResult = {'error': str(testResult)[:200] if testResult else 'Empty response'}
        recordConnectionTest(serverByID[server_id], testResult)
        clientSocketEmitterUpdateFun(server_id, testResult)

    reachableServers = []
    for server in servers:
        if server.authkey:
            reachableServers.append(server)
        else:
            recordAndForward(server.id, {'error': 'No API key configured'})
    allResults = asyncio.run(asyncFetcherManyServer(reachableServers, url, recordAndForward, timeout=timeout, max_concurrency=max_concurrency))
    return allResults


def testConnectionForUser(user, server_id: int) -> Union[dict, None]:
    server = getForUser(user, server_id)
    if server is not None:
        return recordConnectionTest(server, mispGetRequest(server, '/servers/getVersion'))
    else:
        return None


def stripRemoteAuthkeys(connectedServers):
    """Remove remote server authkeys from a MISP /servers/index result. Current MISP versions never include
    them, but they must not be stored or sent to clients if a MISP instance ever does."""
    if isinstance(connectedServers, list):
        for connectedServer in connectedServers:
            if isinstance(connectedServer, dict) and isinstance(connectedServer.get('Server'), dict):
                connectedServer['Server'].pop('authkey', None)
    return connectedServers


def summarizeRegistrations(registrations):
    """Pending account requests (`/users/registrations`), reduced to what identifies them: the requester's IP
    address and user agent are not kept. Errors (e.g. an API user not allowed to see registrations) pass through"""
    if not isinstance(registrations, list):
        return registrations if isinstance(registrations, dict) else {'error': 'Unexpected answer'}
    summary = []
    for entry in registrations:
        inbox = entry.get('Inbox') if isinstance(entry, dict) else None
        if not isinstance(inbox, dict):
            continue
        data = inbox.get('data') if isinstance(inbox.get('data'), dict) else {}
        summary.append({
            'id': inbox.get('id'),
            'uuid': inbox.get('uuid'),
            'timestamp': inbox.get('timestamp'),
            'email': data.get('email'),
            'org_name': data.get('org_name'),
        })
    return summary


def refreshServerConnectionList(server_id: int, remote_server_id=None) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        connectedServers = stripRemoteAuthkeys(mispGetRequest(server, '/servers/index', nocache=True))
        if connectedServers is not None:
            if remote_server_id is None:
                connectedServers = attachConnectedServerStatus(server, connectedServers)
            else:
                connectedServers = attachConnectedServerStatusFor(server, connectedServers, remote_server_id)
            savePartialInfo(server, 'connectedServers', connectedServers)
            publishHealth(server)
            return connectedServers
    return None

def getServerInfoForUser(user, server_id, cache=True) -> Union[dict, None]:
    server = getForUser(user, server_id)
    if server is not None:
        server_uuid = server.uuid
        if not cache:
            server_query_db = fetchServerInfo(server)
        else:
            server_query_db = redisModel.getServerInfo(server_uuid)
            if server_query_db is None: # No query associated to the server
                return None
        return serverQuerySchema.load(server_query_db)
    else:
        return None

def getServerInfo(server_id, cache=True) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        server_uuid = server.uuid
        if not cache:
            server_query_db = fetchServerInfo(server)
        else:
            server_query_db = redisModel.getServerInfo(server_uuid)
            if server_query_db is None: # No query associated to the server
                return None
        return serverQuerySchema.load(server_query_db)
    else:
        return None

def editConnection(user, server_id, remote_server_id, payload):
    url = f'/servers/edit/{remote_server_id}'
    server = getForUser(user, server_id)
    if server is not None:
        response = mispPostRequest(server, url, data=payload, rawResponse=True, nocache=True)
        responseData = ""
        try:
            responseData = response.json()
        except json.decoder.JSONDecodeError as e:
            responseData = response.text

        return {
            'timestamp': int(time.time()),
            'data': responseData,
            'headers': dict(response.headers),
            'status_code': response.status_code,
            'reason': response.reason,
            'elapsed_time': str(response.elapsed),
            'url': response.url,
            'server_id': server_id,
        }
    else:
        return None


def fetchServerInfo(server, use_cache=True):
    serverSettings = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1', nocache=not use_cache)
    serverUsage = mispGetRequest(server, '/users/statistics', nocache=not use_cache)
    serverUser = mispGetRequest(server, '/users/view/me', nocache=not use_cache)
    connectedServers = stripRemoteAuthkeys(mispGetRequest(server, '/servers/index', nocache=not use_cache))
    connectedServers = attachConnectedServerStatus(server, connectedServers)
    userRegistrations = summarizeRegistrations(mispGetRequest(server, '/users/registrations', nocache=not use_cache))
    serverContent = None
    server_query = {
        'serverSettings': serverSettings,
        'serverUsage': serverUsage,
        'serverUser': serverUser,
        'connectedServers': connectedServers,
        'userRegistrations': userRegistrations,
        'serverContent': serverContent
    }
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)
    publishHealth(server)
    return fullQuery


def doFleetInfoTask(servers: list, clientSocketEmitterUpdateFuns):
    allResults = asyncio.run(doFleetInfoTaskAsync(servers, clientSocketEmitterUpdateFuns))
    if len(servers) > 0:
        redisModel.setFleetWatchedTimestamp(servers[0].fleet_id)
    return allResults

def dofetchServerInfoAsync(servers: list, clientSocketEmitterUpdateFuns):
    return asyncio.run(fetchServerInfoAsync(servers, clientSocketEmitterUpdateFuns))

async def doFleetInfoTaskAsync(servers: list, clientSocketEmitterUpdateFuns):
    tasks = []
    for server in servers:
        tasks.append(fetchServerInfoAsync(server, clientSocketEmitterUpdateFuns))
    return await asyncio.gather(*tasks)


def refreshServersInBackground(servers: list, clientSocketEmitterUpdateFuns, max_concurrency: int):
    """Full refresh of servers that may belong to different users and fleets, at most `max_concurrency` at a time.
    A failing server does not stop the others."""
    return asyncio.run(refreshServersInBackgroundAsync(servers, clientSocketEmitterUpdateFuns, max_concurrency))

async def refreshServersInBackgroundAsync(servers: list, clientSocketEmitterUpdateFuns, max_concurrency: int):
    semaphore = asyncio.Semaphore(max(int(max_concurrency), 1))

    async def refresh(server):
        async with semaphore:
            try:
                return await fetchServerInfoAsync(server, clientSocketEmitterUpdateFuns)
            except Exception as e:
                print(f'Background refresh of server {server.id} failed: {e}')
                return None
    return await asyncio.gather(*[refresh(server) for server in servers])


def isDue(timestamp: Union[int, None], interval_seconds: int, now: int, slack_seconds: int = 30) -> bool:
    """True when something last done at `timestamp` should be done again. The slack lets a task that runs every
    `interval` minutes catch items refreshed a few seconds after the previous run"""
    return timestamp is None or now - int(timestamp) >= interval_seconds - slack_seconds

def serversDueForConnectionTest(servers: list, interval_seconds: int, now: int) -> list:
    due = []
    for server in servers:
        status = redisModel.getServerStatus(server.uuid)
        if isDue(status.get('timestamp') if status else None, interval_seconds, now):
            due.append(server)
    return due

def serversDueForRefresh(servers: list, interval_seconds: int, now: int) -> list:
    due = []
    for server in servers:
        snapshot = redisModel.getServerInfo(server.uuid)
        if isDue(snapshot.get('timestamp') if snapshot else None, interval_seconds, now):
            due.append(server)
    return due


async def fetchServerInfoAsync(server, clientSocketEmitterUpdateFuns):
    urls = [
        '/servers/serverSettings/diagnostics/light:1',
        '/users/view/me',
        '/servers/index',
        '/users/registrations',
    ]
    results = await asyncFetcher(server, urls)
    serverSettings = results[0]
    serverUser = results[1]
    connectedServers = stripRemoteAuthkeys(results[2])
    userRegistrations = summarizeRegistrations(results[3])
    serverUsage = {}
    serverContent = None
    server_query = {
        'serverSettings': serverSettings,
        'serverUsage': serverUsage,
        'serverUser': serverUser,
        'connectedServers': connectedServers,
        'userRegistrations': userRegistrations,
        'serverContent': serverContent
    }
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    fullQueryWithServer = dict(fullQuery)
    fullQueryWithServer['server'] = server
    if "udpate_server" in clientSocketEmitterUpdateFuns:
        clientSocketEmitterUpdateFuns["udpate_server"](server.id, fullQueryWithServer)
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)

    connectedServers = await attachConnectedServerStatusAsync(server, connectedServers)
    savePartialInfo(server, "connectedServers", connectedServers)
    if "udpate_server_connection_list" in clientSocketEmitterUpdateFuns:
        clientSocketEmitterUpdateFuns['udpate_server_connection_list'](server, connectedServers)

    serverUsageResult = await asyncFetcher(server, ["/users/statistics"])
    serverUsage = serverUsageResult[0]
    savePartialInfo(server, "serverUsage", serverUsage)
    if "udpate_server_usage" in clientSocketEmitterUpdateFuns:
        clientSocketEmitterUpdateFuns["udpate_server_usage"](server, serverUsage)
    publishHealth(server)
    return fullQuery


def attachConnectedServerStatus(server, connectedServers):
    if type(connectedServers) is list:
        with concurrent.futures.ThreadPoolExecutor(max(len(connectedServers), 1)) as executor:
            future_to_serverid = {executor.submit(getConnectedServerStatus, server, connectedServer): i for i, connectedServer in enumerate(connectedServers)}
            for future in concurrent.futures.as_completed(future_to_serverid):
                j = future_to_serverid[future]
                try:
                    data = future.result()
                    connectedServers[j] = data
                except Exception as exc:
                    print('%r generated an exception: %s' % (connectedServers[j], exc))
    return connectedServers

async def attachConnectedServerStatusAsync(server, connectedServers):
    if type(connectedServers) is list:
        for i, connectedServer in enumerate(connectedServers):
            serverStatus = await getConnectedServerStatusAsync(server, connectedServer)
            connectedServers[i] = serverStatus
    return connectedServers

def attachConnectedServerStatusFor(server, connectedServers, remote_server_id):
    '''Recover old connection states for all other remote servers but refresh the one that has been requested'''
    if type(connectedServers) is list:
        fullQuery = redisModel.getServerInfo(server.uuid)
        if fullQuery is not None:
            oldConnectionStatus = fullQuery['query_result']['connectedServers']
            oldConnectionStatusByID = {oldServerStatus["Server"]["id"]: oldServerStatus for oldServerStatus in oldConnectionStatus}
            for i, connectedServer in enumerate(connectedServers):
                if int(connectedServer["Server"]["id"]) == int(remote_server_id):
                    connectedServers[i] = getConnectedServerStatus(server, connectedServer)
                else:
                    theOldConnectionStatus = oldConnectionStatusByID[connectedServer["Server"]["id"]]
                    connectedServers[i]['connectionTest'] = theOldConnectionStatus['connectionTest']
                    connectedServers[i]['connectionUser'] = theOldConnectionStatus['connectionUser']
                    connectedServers[i]['vid'] = theOldConnectionStatus['vid']
        else:
            connectedServers = attachConnectedServerStatus(server, connectedServers)
    return connectedServers


def cacheMonitoringImages(servers: list, force: bool = False, callbacks: dict = {}):
    allResults = asyncio.run(doCacheMonitoringImages(servers, force=force, callbacks=callbacks))
    return allResults


async def doCacheMonitoringImages(servers: list, force: bool = False, callbacks: dict = {}):
    global MONITORING_PANELS
    panels = MONITORING_PANELS
    # No explicit start: each panel uses its own relative_time_days window
    from_time = None

    # Wrap callbacks to keep track of the reload status per server
    wrappedCallbacks = {}
    if 'server_graphs_resfresh_status' in callbacks:
        panelRefreshedCount = 0
        def graphRefreshStatus(serverID, refresh_panel_id):
            nonlocal panelRefreshedCount
            panelRefreshedCount += 1
            status = {
                "total_panels": len(panels),
                "panel_refreshed_count": panelRefreshedCount,
                "last_panel_refreshed": refresh_panel_id,
            }
            callbacks['server_graphs_resfresh_status'](serverID, status)
        wrappedCallbacks['server_graphs_resfresh_status'] = graphRefreshStatus

    if 'server_graphs_update_done' in callbacks:
        wrappedCallbacks['server_graphs_update_done'] = callbacks['server_graphs_update_done']

    tasks = []
    for server in servers:
        for panel in panels:
            tasks.append(
                cacheMonitoringImageAsync(server, panel, from_time, force, wrappedCallbacks)
            )
    result = await asyncio.gather(*tasks)
    for server in servers:
        timestamp = int(time.time())
        if 'server_graphs_update_done' in wrappedCallbacks:
            wrappedCallbacks["server_graphs_update_done"](server.id, timestamp)
        redisModel.setServerCachedPicturedTimestamp(server.uuid)
    return result


async def cacheMonitoringImageAsync(server, panel, from_time, force, callbacks = {}):
    monitoringImage = MonitoringImages(server, panel, from_time)
    if "server_graphs_resfresh_status" in callbacks:
        def callback():
            nonlocal server, panel
            callbacks["server_graphs_resfresh_status"](server.id, panel["panel_id"])
        await monitoringImage.asyncRefreshImage(force, callback)
    else:
        await monitoringImage.asyncRefreshImage(force)


def saveInfo(server, fullQuery: dict) -> bool:
    return redisModel.saveServerInfo(server.uuid, fullQuery)

def savePartialInfo(server, key: str, partialQuery: dict) -> bool:
    fullQuery = redisModel.getServerInfo(server.uuid)
    if fullQuery is not None:
        fullQuery['query_result'][key] = partialQuery
        return redisModel.saveServerInfo(server.uuid, fullQuery)
    return False

def getConnectedServerStatus(server, connectedServer):
    connectionTest = mispGetRequest(server, f'/servers/testConnection/{connectedServer["Server"]["id"]}')
    connectionUser = mispGetRequest(server, f'/servers/getRemoteUser/{connectedServer["Server"]["id"]}')
    connectionTest['timestamp'] = int(time.time())
    connectedServer['connectionTest'] = parseMISPConnectionOutput(connectionTest)
    connectedServer['connectionUser'] = parseMISPUserConnectionOutput(connectionUser)
    connectedServer['vid'] = f"{server.id}-{connectedServer['Server']['id']}"
    return connectedServer


async def getConnectedServerStatusAsync(server, connectedServer):
    urls = [
        f'/servers/testConnection/{connectedServer["Server"]["id"]}',
    ]
    results = await asyncFetcher(server, urls, timeout=5)  #  Aggressive timeout
    connectionTest = results[0]
    connectionTest['timestamp'] = int(time.time())
    connectedServer['connectionTest'] = parseMISPConnectionOutput(connectionTest)
    connectedServer['vid'] = f"{server.id}-{connectedServer['Server']['id']}"
    if connectedServer["connectionTest"]["status"]["authorized"]:
        urls = [
            f'/servers/getRemoteUser/{connectedServer["Server"]["id"]}',
        ]
        results = await asyncFetcher(server, urls, timeout=15)  #  Aggressive timeout
        connectionUser = results[0]
        connectedServer['connectionUser'] = parseMISPUserConnectionOutput(connectionUser)
    else:
        connectedServer['connectionUser'] = parseMISPUserConnectionOutput({})
    return connectedServer

def parseMISPUserConnectionOutput(userConnection):
    parsed = {
        'email': "",
        'role_name': "",
        'role_color': "",
        'sync_flag': "",
        'message': ""
    }
    parsed['email'] = userConnection.get('User', "")
    parsed['role_name'] = userConnection.get('Role name', "")
    parsed['sync_flag'] = True if userConnection.get('Sync flag', False) == 'Yes' else False
    parsed['message'] = userConnection.get('message', "")
    if parsed['role_name'] == "admin":
        parsed['role_color'] = "danger"
    elif parsed['role_name'] == "User":
        parsed['role_color'] = "warning"
    elif parsed['role_name'] == "Sync user":
        parsed['role_color'] = "success"
    else:
        parsed['role_color'] = "warning"

    if parsed['sync_flag'] and parsed['role_color'] == 'warning':
        parsed['role_color'] = "success"
    return parsed

# `status` codes of MISP's /servers/testConnection other than 1 (OK)
CONNECTION_TEST_STATUSES = {
    2: ("danger", "Server unreachable"),
    3: ("danger", "Unexpected error"),
    4: ("danger", "Authentication failed"),
    5: ("danger", "Password change required"),
    6: ("danger", "Terms not accepted"),
    7: ("warning", "Remote user is not a sync user"),
    8: ("warning", "Syncing sightings only"),
}


def connectionTestError(connection):
    """Why asking MISP to test a connection gave no test result (request error, HTTP error answer), or None"""
    if 'error' in connection:
        return str(connection['error'])
    statusCode = connection.get('_status_code')
    if isinstance(statusCode, int) and statusCode >= 400:
        return str(connection.get('message') or connection.get('name') or f"HTTP {statusCode}")
    return None


def parseMISPConnectionOutput(connection):
    """Turn MISP's /servers/testConnection answer into what the UI shows. `status.code`, `compatibility.mismatch`/
    `newer` and `post.code` keep MISP's raw values for the link health classification; `timestamp` is when the test
    ran; `test_error` is set when the request to the local MISP failed, i.e. the link itself was not tested"""
    statusCode = connection.get('status', None)
    parsed = {
        'status': { 'message': "", 'color': "danger", "authorized": False,
                    'code': statusCode if isinstance(statusCode, int) else None},
        'compatibility': {'message': "", 'color': ""},
        'post': { 'result': "", 'color': "danger", 'success': False },
        'localVersion': "",
        'remoteVersion': "",
        'uuid': "?",
        'timestamp': connection.get('timestamp'),
    }
    if statusCode == 1:
        parsed['status']['color'] = "success"
        parsed['status']['message'] = "OK"
        parsed["status"]["authorized"] = True
        parsed['compatibility']['color'] = "success"
        parsed['compatibility']['message'] = "Compatible"
        parsed['compatibility']['mismatch'] = connection.get('mismatch')
        parsed['compatibility']['newer'] = connection.get('newer')
        parsed['localVersion'] = connection['local_version']
        parsed['remoteVersion'] = connection['version']
        if 'uuid' in connection:
            parsed['uuid'] = connection['uuid']
        if connection['mismatch'] == "hotfix":
            parsed['compatibility']['color'] = "warning"

        if connection['newer'] == "local":
            if connection['mismatch'] == "minor":
                parsed['compatibility']['message'] = "Pull only"
                parsed['compatibility']['color'] = "warning"
                parsed['status']['color'] = "warning"
            elif connection['mismatch'] == "major":
                parsed['compatibility']['message'] = "Incompatible"
                parsed['compatibility']['color'] = "danger"
        elif connection['newer'] == "remote":
            if connection['mismatch'] != "hotfix":
                parsed['compatibility']['message'] = "Incompatible"
                parsed['compatibility']['color'] = "danger"
        elif connection['mismatch'] == "proposal":
            parsed['compatibility']['message'] = "Proposal pull disabled (remote version < v2.4.111)"
            parsed['compatibility']['color'] = "warning"
            parsed['status']['color'] = "warning"

        if connection['mismatch'] != False and connection['mismatch'] != "proposal":
            if connection['newer'] == "remote":
                parsed['status']['message'] = "Local instance outdated, update!"
            else:
                parsed['status']['message'] = "Remote outdated, notify admin!"

        if connection['post'] != False:
            parsed['post']['color'] = "danger"
            parsed['post']['code'] = connection['post']
            if connection['post'] == 1:
                parsed['post']['result'] = "Received sent package"
                parsed['post']['color'] = "success"
                parsed['post']['success'] = True
            elif connection['post'] == 8:
                parsed['post']['result'] = "Could not POST message"
                parsed['post']['color'] = "danger"
                parsed['post']['success'] = False
            elif connection['post'] == 9:
                parsed['post']['result'] = "Invalid body"
                parsed['post']['color'] = "danger"
                parsed['post']['success'] = False
            elif connection['post'] == 10:
                parsed['post']['result'] = "Invalid headers"
                parsed['post']['color'] = "danger"
                parsed['post']['success'] = False
            else:
                parsed['post']['result'] = "Remote too old for this test"

    elif statusCode in CONNECTION_TEST_STATUSES:
        parsed['status']['color'], parsed['status']['message'] = CONNECTION_TEST_STATUSES[statusCode]
        parsed['status']['authorized'] = statusCode in (7, 8)
    else:
        parsed['status']['color'] = "danger"
        testError = connectionTestError(connection)
        if testError is not None:
            parsed['status']['message'] = testError
            parsed['test_error'] = testError
        else:
            parsed['status']['message'] = "Unkown response status"
    return parsed
