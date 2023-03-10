#!/usr/bin/env python3

import time
from typing import List, Union
import concurrent.futures

from application import redisClient, redisModel
from application.DBModels import db, User, Server
from application.controllers.utils import mispGetRequest
from application.marshmallowSchemas import serverQuerySchema


def index(group_id=None):
    q = Server.query
    if group_id is not None:
        q = q.filter_by(server_group_id=group_id)
    servers = q.all()
    return servers

def searchAll(text: str) -> List:
    search = "%{}%".format(text)
    query = Server.query.filter(
        (Server.name.ilike(search)) |
        (Server.url.ilike(search)) |
        (Server.comment.ilike(search))
    )
    servers = query.limit(10).all()
    return servers

def testConnection(server_id: int) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        testConnection = mispGetRequest(server, '/servers/getVersion')
        testConnection['timestamp'] = int(time.time())
        return testConnection
    else:
        return None


def getServerInfo(server_id, cache=True) -> Union[dict, None]:
    server = Server.query.get(server_id)
    if server is not None:
        if not cache:
            server_query_db = fetchServerInfo(server)
        else:
            server_query_db = redisModel.getServerInfo(server_id)
            if server_query_db is None: # No query associated to the server
                server_query_db = fetchServerInfo(server)
        return serverQuerySchema.load(server_query_db)
    else:
        return None


def fetchServerInfo(server):
    serverSettings = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1')
    serverUsage = mispGetRequest(server, '/users/statistics')
    serverUser = mispGetRequest(server, '/users/view/me')
    connectedServers = mispGetRequest(server, '/servers/index')
    connectedServers = attachConnectedServerStatus(server, connectedServers)
    serverContent = []
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


def saveInfo(server, fullQuery: dict) -> bool:
    return redisModel.saveServerInfo(server.id, fullQuery)


def getConnectedServerStatus(server, connectedServer):
    connectionTest = mispGetRequest(server, f'/servers/testConnection/{connectedServer["Server"]["id"]}')
    connectionUser = mispGetRequest(server, f'/servers/getRemoteUser/{connectedServer["Server"]["id"]}')
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
    }
    if connection['status'] == 1:
        parsed['status']['color'] = "success"
        parsed['status']['message'] = "OK"
        parsed['compatibility']['color'] = "success"
        parsed['compatibility']['message'] = "Compatible"
        parsed['localVersion'] = connection['local_version']
        parsed['remoteVersion'] = connection['version']
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