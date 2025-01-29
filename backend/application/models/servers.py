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
from application.workers.tasks import fetchServerInfoTask

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

def testConnection(server_id: int, use_cache=True) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        testConnection = mispGetRequest(server, '/servers/getVersion', nocache=not use_cache)
        testConnection['timestamp'] = int(time.time())
        return testConnection
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
        testConnection = results[0]
        testConnection['timestamp'] = int(time.time())
        return testConnection
    else:
        return None

def testAllConnectionAsync(servers: list, clientSocketEmitterUpdateFun):
    url = '/servers/getVersion'
    allResults = asyncio.run(asyncFetcherManyServer(servers, url, clientSocketEmitterUpdateFun))
    return allResults


def testConnectionForUser(user, server_id: int) -> Union[dict, None]:
    server = getForUser(user, server_id)
    if server is not None:
        testConnection = mispGetRequest(server, '/servers/getVersion')
        testConnection['timestamp'] = int(time.time())
        return testConnection
    else:
        return None


def refreshServerConnectionList(server_id: int, remote_server_id=None) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        connectedServers = mispGetRequest(server, '/servers/index', nocache=True)
        if connectedServers is not None:
            if remote_server_id is None:
                connectedServers = attachConnectedServerStatus(server, connectedServers)
            else:
                connectedServers = attachConnectedServerStatusFor(server, connectedServers, remote_server_id)
            savePartialInfo(server, 'connectedServers', connectedServers)
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
    connectedServers = mispGetRequest(server, '/servers/index', nocache=not use_cache)
    connectedServers = attachConnectedServerStatus(server, connectedServers)
    serverContent = None
    server_query = {
        'serverSettings': serverSettings,
        'serverUsage': serverUsage,
        'serverUser': serverUser,
        'connectedServers': connectedServers,
        'serverContent': serverContent
    }
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)
    return fullQuery


def doFleetInfoTask(servers: list, clientSocketEmitterUpdateFun):
    allResults = asyncio.run(doFleetInfoTaskAsync(servers, clientSocketEmitterUpdateFun))
    if len(servers) > 0:
        redisModel.setFleetWatchedTimestamp(servers[0].fleet_id)
    return allResults

def dofetchServerInfoAsync(servers: list, clientSocketEmitterUpdateFun):
    return asyncio.run(fetchServerInfoAsync(servers, clientSocketEmitterUpdateFun))

async def doFleetInfoTaskAsync(servers: list, clientSocketEmitterUpdateFun):
    tasks = []
    for server in servers:
        tasks.append(fetchServerInfoAsync(server, clientSocketEmitterUpdateFun))
    return await asyncio.gather(*tasks)


async def fetchServerInfoAsync(server, clientSocketEmitterUpdateFun):
    urls = [
        '/servers/serverSettings/diagnostics/light:1',
        '/users/statistics',
        '/users/view/me',
        '/servers/index',
    ]
    results = await asyncFetcher(server, urls)
    serverSettings = results[0]
    serverUsage = results[1]
    serverUser = results[2]
    connectedServers = results[3]
    connectedServers = await attachConnectedServerStatusAsync(server, connectedServers)
    serverContent = None
    server_query = {
        'serverSettings': serverSettings,
        'serverUsage': serverUsage,
        'serverUser': serverUser,
        'connectedServers': connectedServers,
        'serverContent': serverContent
    }
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    fullQueryWithServer = dict(fullQuery)
    fullQueryWithServer['server'] = server
    clientSocketEmitterUpdateFun(server.id, fullQueryWithServer)
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)
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
    from_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
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
        savePartialInfo(server, "_monitoringGraphLastRefresh", {'timestamp': timestamp})
    return result


async def cacheMonitoringImageAsync(server, panel, from_time, force, callbacks = {}):
    monitoringImage = MonitoringImages(server.id, panel, from_time)
    monitoringImage.refreshImage(force)
    flaskApp.logger.debug(f"[server:{server.id}] Cached monitoring image for panel `{panel}`")
    if "server_graphs_resfresh_status" in callbacks:
        callbacks["server_graphs_resfresh_status"](server.id, panel['panel_id'])


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
        f'/servers/getRemoteUser/{connectedServer["Server"]["id"]}',
    ]
    results = await asyncFetcher(server, urls)
    connectionTest = results[0]
    connectionUser = results[1]
    connectionTest['timestamp'] = int(time.time())
    connectedServer['connectionTest'] = parseMISPConnectionOutput(connectionTest)
    connectedServer['connectionUser'] = parseMISPUserConnectionOutput(connectionUser)
    connectedServer['vid'] = f"{server.id}-{connectedServer['Server']['id']}"
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

def parseMISPConnectionOutput(connection):
    parsed = {
        'status': { 'message': "", 'color': "danger"},
        'compatibility': {'message': "", 'color': ""},
        'post': { 'result': "", 'color': "danger", 'success': False },
        'localVersion': "",
        'remoteVersion': "",
        'uuid': "?",
    }
    if connection['status'] == 1:
        parsed['status']['color'] = "success"
        parsed['status']['message'] = "OK"
        parsed['compatibility']['color'] = "success"
        parsed['compatibility']['message'] = "Compatible"
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

    elif connection['status'] == 2:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Server unreachable"
    elif connection['status'] == 3:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Unexpected error"
    elif connection['status'] == 4:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Authentication failed"
    elif connection['status'] == 5:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Password change required"
    elif connection['status'] == 6:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Terms not accepted"
    elif connection['status'] == 7:
        parsed['message'] = "Remote user is not a sync user"
    elif connection['status'] == 8:
        parsed['status']['color'] = "warning"
        parsed['status']['message'] = "Syncing sightings only"
    else:
        parsed['status']['color'] = "danger"
        parsed['status']['message'] = "Unkown response status"
    return parsed
