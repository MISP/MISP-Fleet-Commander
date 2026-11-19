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

from application.models.utils import asyncFetcher, asyncFetcherManyServer
from application.models import baselineDrift
import application.models.organisations as organisationModel
import application.models.queryCapability as queryCapabilityModel

import nest_asyncio
nest_asyncio.apply()


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

# A connection test (`/servers/getVersion`) taking longer than this counts as unreachable. Without it, a server that
# drops packets keeps a worker busy for minutes, and a few clicks on "Quick refresh" can block every worker
CONNECTION_TEST_TIMEOUT = 30

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
        results = asyncio.run(asyncFetcher(server, urls, timeout=CONNECTION_TEST_TIMEOUT))
        if results is None:
            return None
        return recordConnectionTest(server, results[0])
    else:
        return None

def testAllConnectionAsync(servers: list, clientSocketEmitterUpdateFun, max_concurrency=None, timeout=None):
    timeout = CONNECTION_TEST_TIMEOUT if timeout is None else timeout
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

def fetchServerInfo(server, use_cache=True):
    serverSettings = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1', nocache=not use_cache)
    serverUsage = mispGetRequest(server, '/users/statistics', nocache=not use_cache)
    serverUser = mispGetRequest(server, '/users/view/me', nocache=not use_cache)
    connectedServers = stripRemoteAuthkeys(mispGetRequest(server, '/servers/index', nocache=not use_cache))
    connectedServers = attachConnectedServerStatus(server, connectedServers)
    userRegistrations = summarizeRegistrations(mispGetRequest(server, '/users/registrations', nocache=not use_cache))
    contentPlan = baselineDrift.contentPlanOfFleet(server.fleet_id)
    contentUrls, organisationIndex = contentRequests(server, contentPlan)
    answers = {url: mispGetRequest(server, url, nocache=not use_cache) for url in contentUrls}
    serverContent = None
    server_query = {
        'serverSettings': serverSettings,
        'serverUsage': serverUsage,
        'serverUser': serverUser,
        'connectedServers': connectedServers,
        'userRegistrations': userRegistrations,
        'serverContent': serverContent
    }
    if contentPlan:
        server_query['baselineState'] = contentPlan.state([answers[url] for url in contentPlan.urls])
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)
    baselineDrift.afterContentFetched(server, server_query.get('baselineState'))
    if organisationIndex is not None:
        organisationModel.listedByRefresh(server, answers[organisationIndex])
    publishHealth(server)
    return fullQuery


def contentRequests(server, contentPlan):
    """The listings a full refresh asks for besides the snapshot: the content the fleet's baseline rules need, and
    the organisations when the fleet has other servers to compare them with (asked once if the baseline needs them
    too). `(urls, organisation index URL or None)`"""
    urls = list(contentPlan.urls)
    organisationIndex = organisationModel.listedByRefreshUrl(server)
    if organisationIndex is not None and organisationIndex not in urls:
        urls.append(organisationIndex)
    return urls, organisationIndex


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
    # Taxonomies, galaxies, object templates, organisations or sharing groups, when the fleet's baseline has rules
    # about them
    contentPlan = baselineDrift.contentPlanOfFleet(server.fleet_id)
    contentUrls, organisationIndex = contentRequests(server, contentPlan)
    results = await asyncFetcher(server, urls + contentUrls)
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
    if contentPlan:
        server_query['baselineState'] = contentPlan.state(results[len(urls):len(urls) + len(contentPlan.urls)])
    fullQuery = {
        'timestamp': int(time.time()),
        'query_result': server_query,
    }
    baselineDrift.afterContentFetched(server, server_query.get('baselineState'))
    fullQueryWithServer = dict(fullQuery)
    fullQueryWithServer['server'] = server
    if "udpate_server" in clientSocketEmitterUpdateFuns:
        clientSocketEmitterUpdateFuns["udpate_server"](server.id, fullQueryWithServer)
    saveInfo(server, fullQuery)
    redisModel.setServerWatchedTimestamp(server.uuid)
    if organisationIndex is not None:
        organisationModel.listedByRefresh(server, results[len(urls) + contentUrls.index(organisationIndex)])

    connectedServers = await attachConnectedServerStatusAsync(server, connectedServers)
    savePartialInfo(server, "connectedServers", connectedServers)
    if "udpate_server_connection_list" in clientSocketEmitterUpdateFuns:
        clientSocketEmitterUpdateFuns['udpate_server_connection_list'](server, connectedServers)

    # A server none of these requests reached would only make the usage statistics wait for the timeout again
    if not all(isUnanswered(result) for result in results):
        serverUsageResult = await asyncFetcher(server, ["/users/statistics"])
        serverUsage = serverUsageResult[0]
        savePartialInfo(server, "serverUsage", serverUsage)
        if "udpate_server_usage" in clientSocketEmitterUpdateFuns:
            clientSocketEmitterUpdateFuns["udpate_server_usage"](server, serverUsage)
    publishHealth(server)
    return fullQuery


def isUnanswered(result) -> bool:
    """A request that got no HTTP answer at all: connection refused or reset, timeout"""
    return isinstance(result, dict) and 'error' in result and '_status_code' not in result


# Sync links of one server tested at the same time, during a full refresh or a link test
LINK_TEST_CONCURRENCY = 4
# Listing a server's sync connections before testing them
LINK_TEST_INDEX_TIMEOUT = 30


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

async def attachConnectedServerStatusAsync(server, connectedServers, max_concurrency=LINK_TEST_CONCURRENCY):
    """Test a server's sync links, a few at a time: each test makes that MISP contact the remote. A test that
    fails unexpectedly is recorded as not completed instead of stopping the others"""
    if type(connectedServers) is list:
        semaphore = asyncio.Semaphore(max(int(max_concurrency), 1))

        async def test(connectedServer):
            async with semaphore:
                try:
                    return await getConnectedServerStatusAsync(server, connectedServer)
                except Exception as e:
                    connectedServer['connectionTest'] = parseMISPConnectionOutput(
                        {'error': f'Unhandled Exception: {e}', 'timestamp': int(time.time())})
                    connectedServer['connectionUser'] = parseMISPUserConnectionOutput({})
                    return connectedServer
        connectedServers[:] = await asyncio.gather(*[test(connectedServer) for connectedServer in connectedServers])
    return connectedServers


def testLinks(servers: list, callbacks: dict, remote_server_id=None, max_concurrency: int = 10):
    """Re-test the sync links of servers without the rest of a full refresh (diagnostics, users, usage).
    `remote_server_id` restricts the test to that link (the other links keep their last result). Callbacks:
    `link_test_done(server, result)` once per server, whatever happens, and `udpate_server_connection_list`"""
    return asyncio.run(testLinksAsync(servers, callbacks, remote_server_id, max_concurrency))


async def testLinksAsync(servers: list, callbacks: dict, remote_server_id=None, max_concurrency: int = 10):
    semaphore = asyncio.Semaphore(max(int(max_concurrency), 1))

    async def test(server):
        async with semaphore:
            result = {}
            try:
                result = await testServerLinksAsync(server, callbacks, remote_server_id)
            except Exception as e:
                print(f'Link test of server {server.id} failed: {e}')
                result = {'error': 'The link test failed unexpectedly'}
            finally:
                if 'link_test_done' in callbacks:
                    callbacks['link_test_done'](server, result)
            return result
    return await asyncio.gather(*[test(server) for server in servers])


async def testServerLinksAsync(server, callbacks: dict, remote_server_id=None) -> dict:
    """`{"tested": n}`, `{"full_refresh": True}` for a server with no data yet (there is nothing to update, so it
    gets a full refresh instead), or `{"error": ...}`, in which case the last known links are kept"""
    if not server.authkey:
        return {'error': 'No API key configured'}
    previous = redisModel.getServerInfo(server.uuid)
    if previous is None:
        await fetchServerInfoAsync(server, callbacks)
        return {'full_refresh': True}

    results = await asyncFetcher(server, ['/servers/index'], timeout=LINK_TEST_INDEX_TIMEOUT)
    connectedServers = stripRemoteAuthkeys(results[0])
    if not isinstance(connectedServers, list):
        answer = connectedServers if isinstance(connectedServers, dict) else {}
        error = answer.get('error') or answer.get('message') or answer.get('name') or 'Unexpected answer'
        return {'error': f'Could not list the sync connections: {error}'}

    if remote_server_id is None:
        toTest = connectedServers
    else:
        toTest = [c for c in connectedServers if str(c.get('Server', {}).get('id')) == str(remote_server_id)]
        if not toTest:
            return {'error': f'No sync connection with ID {remote_server_id}'}
        previousLinks = previous.get('query_result', {}).get('connectedServers')
        previousByID = {str(link['Server']['id']): link for link in previousLinks
                        if isinstance(link, dict) and isinstance(link.get('Server'), dict)} \
            if isinstance(previousLinks, list) else {}
        for connectedServer in connectedServers:
            remoteID = str(connectedServer.get('Server', {}).get('id'))
            old = previousByID.get(remoteID)
            if remoteID != str(remote_server_id) and old is not None:
                for key in ('connectionTest', 'connectionUser', 'vid'):
                    if key in old:
                        connectedServer[key] = old[key]

    await attachConnectedServerStatusAsync(server, toTest)
    savePartialInfo(server, 'connectedServers', connectedServers)
    if 'udpate_server_connection_list' in callbacks:
        callbacks['udpate_server_connection_list'](server, connectedServers)
    publishHealth(server)
    return {'tested': len(toTest)}

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


def saveInfo(server, fullQuery: dict) -> bool:
    # A refreshed server may have been upgraded, or its key's role changed: ask again when next needed
    queryCapabilityModel.forget(server.id)
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
