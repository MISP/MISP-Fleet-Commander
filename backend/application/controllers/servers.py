#!/usr/bin/env python3

import time
import json
import re
import concurrent.futures
from datetime import datetime as dt, timedelta
from collections import Mapping, MutableSequence, defaultdict
from flask import Blueprint, request, jsonify, abort, Response

from application.DBModels import db, User, Server, ServerQuery
from application.controllers.utils import mispGetRequest, mispPostRequest, batchRequest
from application.marshmallowSchemas import ServerQuerySchema, serverSchema, serversSchema
import application.models.servers as serverModel


BPserver = Blueprint('server', __name__)

class DictToObject:
    def __init__(self, **entries):
        self.__dict__.update(entries)


@BPserver.route('/servers/index/<int:group_id>', methods=['GET'])
def index(group_id=None):
    servers = serverModel.index(group_id)
    if servers:
        return serversSchema.dump(servers)
    else:
        return jsonify([])


@BPserver.route('/servers/get/<int:server_id>', methods=['GET'])
def get(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        return serverSchema.dump(server)
    else:
        return jsonify({})


@BPserver.route('/servers/add/<int:group_id>', methods=['POST'])
def add(group_id):
    servers = []
    # TODO: If password provided, fetch the associated API key
    if isinstance(request.json, list):
        servers = []
        for server in request.json:
            server = Server(name=server.get('name'),
                        url=server.get('url'),
                        comment=server.get('comment'),
                        skip_ssl=server.get('skip_ssl', False),
                        authkey=server.get('authkey', None),
                        basicauth=server.get('basicauth', None),
                        server_group_id=group_id,
                        user_id=1)
            db.session.add(server)
            servers.append(server)
        db.session.commit()
        return serversSchema.dump(servers)
    else:
        server = Server(name=request.json.get('name'),
                        url=request.json.get('url'),
                        comment=request.json.get('comment'),
                        skip_ssl=request.json.get('skip_ssl', False),
                        authkey=request.json.get('authkey', None),
                        basicauth=request.json.get('basicauth', None),
                        server_group_id=group_id,
                        user_id=1)
        db.session.add(server)
        if request.json.get('recursive_add', False):
            # recursively add servers
            pass
        db.session.commit()
        return serversSchema.dump(server)


@BPserver.route('/servers/edit', methods=['POST'])
def edit():
    saveFields = ['name', 'comment', 'url', 'skip_ssl', 'authkey', 'basicauth']
    server = Server.query.get(request.json['id'])
    if server is not None:
        for field, value in request.json.items():
            if field in saveFields:
                setattr(server, field, value)
    if request.json.get('recursive_add', False):
        # recursively add servers
        pass
    db.session.commit()
    return serverSchema.dump(server)


@BPserver.route('/servers/delete', methods=['DELETE', 'POST'])
def delete():
    if isinstance(request.json, list):
        deletedServers = []
        for server in request.json:
            server = Server.query.get(server['id'])
            if server is not None:
                db.session.delete(server)
                deletedServers.append(server.id)
        db.session.commit()
        return serversSchema.dump(deletedServers)
    else:
        server = Server.query.get(request.json['id'])
        if server is not None:
            server_id = server.id
            db.session.delete(server)
            db.session.commit()
            return jsonify([server_id])
        else:
            return jsonify([])

@BPserver.route('/servers/testConnection/<int:server_id>', methods=['GET'])
def ping_server(server_id):
    result = serverModel.testConnection(server_id)
    if result is not None:
        return jsonify(result)
    else:
        return jsonify({})

@BPserver.route('/servers/batchTestConnection/<int:group_id>', methods=['GET'])
def batch_ping_server(group_id=None):
    servers = serverModel.index(group_id)
    allRequests = []
    if servers:
        for server in servers:
            allRequests.append({
                'fn': mispGetRequest,
                'server': server,
                'path': '/servers/getVersion'
            })
        allTestConnections = batchRequest(allRequests)
        return jsonify(allTestConnections)
    else:
        return jsonify([])

@BPserver.route('/servers/queryInfo/<int:server_id>', defaults={'no_cache': False}, methods=['GET'])
@BPserver.route('/servers/queryInfo/<int:server_id>/<int:no_cache>', methods=['GET'])
def queryInfo(server_id, no_cache):
    no_cache = True if no_cache == 1 else False
    server = Server.query.get(server_id)
    if server is not None:
        if no_cache:
            server_query_db = fetchServerInfo(server)
        else:
            server_query_db = ServerQuery.query.filter_by(server_id=server_id).first()
            if server_query_db is None: # No query associated to the server
                server_query_db = fetchServerInfo(server)
        return ServerQuerySchema.dump(server_query_db)
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/getUsers/<int:server_id>', methods=['GET'])
def getUsers(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        server_query_users = fetchServerUsers(server)
        return jsonify(server_query_users)
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/batchTest', methods=['POST'])
def batchTest():
    test_result = []
    allVersionRequests = []
    allUserRequests = []
    server_to_test = request.json
    for index, server in enumerate(server_to_test):
        serverObject = DictToObject(**server)
        if 'id' not in server:
            serverObject.id = index
        allVersionRequests.append({
            'fn': mispGetRequest,
            'server': serverObject,
            'path': '/servers/getVersion'
        })
        allUserRequests.append({
            'fn': mispGetRequest,
            'server': serverObject,
            'path': '/users/view/me'
        })
    allTestConnections = batchRequest(allVersionRequests)
    allTestUsers = batchRequest(allUserRequests)
    for index, server in enumerate(server_to_test):
        server_id = server['id'] if 'id' in server else index
        version = next(filter(lambda x: x['server_id'] == server_id, allTestConnections))
        user = next(filter(lambda x: x['server_id'] == server_id, allTestUsers))
        server['testResult'] = parseGetVersion(version)
        server['userResult'] = user
        test_result.append(server)
    return jsonify(test_result)

@BPserver.route('/servers/discoverConnected', methods=['POST'])
def discoverConnected():
    rootServer = request.json
    test_result = []
    if rootServer:
        rootServerObject = DictToObject(**rootServer)
        rootIndex = mispGetRequest(rootServerObject, '/servers/index')
        if type(rootIndex) != list:
            abort(404, Response('Could not fetch valid server index'))
        allVersionRequests = []
        allUserRequests = []
        for server in rootIndex:
            remoteServer = server['Server']
            remoteServerObject = DictToObject(**remoteServer)
            allVersionRequests.append({
                'fn': mispGetRequest,
                'server': remoteServerObject,
                'path': '/servers/getVersion'
            })
            allUserRequests.append({
                'fn': mispGetRequest,
                'server': remoteServerObject,
                'path': '/users/view/me'
            })
        allTestConnections = batchRequest(allVersionRequests)
        allTestUsers = batchRequest(allUserRequests)
        for server in rootIndex:
            version = next(filter(lambda x: x['server_id'] == server['Server']['id'], allTestConnections))
            user = next(filter(lambda x: x['server_id'] == server['Server']['id'], allTestUsers))
            server['testResult'] = parseGetVersion(version)
            server['userResult'] = user
            test_result.append(server)
    return jsonify(test_result)

@BPserver.route('/servers/network/<int:group_id>')
def network(group_id=None):
    servers = serverModel.index(group_id)
    network = buildNetwork(servers)
    return jsonify(network)

@BPserver.route('/servers/getConnection/<int:server_id>/<int:connection_id>')
def getConnection(server_id, connection_id):
    server = Server.query.get(server_id)
    if server is not None:
        destinations = server.server_info.query_result['connectedServers']
        connection = [ d for d in destinations if int(d['Server']['id']) == connection_id]
        if len(connection) > 0:
            connection = connection[0]
            if 'vid' not in connection:
                connection['vid'] = f"{server_id}-{connection['Server']['id']}"
            return jsonify(connection)
        else:
            return jsonify({})
    else:
        return jsonify({})

@BPserver.route('/servers/syncOvertime/<int:server_id>', methods=['GET'])
def syncOvertime(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        syncLogs = mispPostRequest(server, '/logs/admin_search/search', {"Log":{"model":"Server","action":"pull","email":"","org":"","model_id":"","title":"","change":"", "ip": ""}})
        if 'error' in syncLogs:
            return jsonify(syncLogs)
        syncOvertime = parseGetSyncOvertime(syncLogs)
        result = {
            'timestamp': int(time.time()),
            'data': syncOvertime
        }
        return jsonify(result)
    else:
        return jsonify({})

@BPserver.route('/servers/loginOvertime/<int:server_id>', methods=['GET'])
def loginOvertime(server_id):
    server = Server.query.get(server_id)
    if server is not None:
        loginLogs = mispPostRequest(server, '/logs/admin_search/search', {"Log":{"model":"User","action":["login", "auth_fail"],"email":"","org":"","model_id":"","title":"","change":"", "ip": ""}})
        if 'error' in loginLogs:
            return jsonify(loginLogs)
        loginLogs = parseGetLoginLogs(loginLogs)
        result = {
            'timestamp': int(time.time()),
            'data': loginLogs
        }
        return jsonify(result)
    else:
        return jsonify({})

@BPserver.route('/servers/restQuery/<int:server_id>', methods=['POST'])
def restQuery(server_id):
    queryURL = request.json['url']
    queryData = request.json['data']
    queryMethod = request.json['method']
    server = Server.query.get(server_id)
    if server is not None:
        if queryMethod == 'POST':
            response = mispPostRequest(server, queryURL, queryData, rawResponse=True)
        else:
            response = mispGetRequest(server, queryURL, rawResponse=True)
        responseData = ""
        try:
            responseData = response.json()
        except json.decoder.JSONDecodeError as e:
            responseData = response.text
        result = {
            'timestamp': int(time.time()),
            'data': responseData,
            'headers': dict(response.headers),
            'status_code': response.status_code,
            'reason': response.reason,
            'elapsed_time': response.elapsed,
            'url': response.url,
            'server_id': server_id,
        }
        return jsonify(result)
    else:
        return jsonify({})


# ===========
def saveInfo(server, queryResult):
    now = int(time.time())
    server_query = ServerQuery.query.filter_by(server_id=server.id).first()
    if server_query is not None:
        server_query.query_result = queryResult
        server_query.timestamp = now
    else:
        server_query = ServerQuery(server_id=server.id,
                        timestamp=now,
                        query_result=queryResult)
    server.server_info = server_query
    db.session.add(server)
    db.session.commit()
    return server_query

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
    server_query_db = saveInfo(server, server_query)
    return server_query_db

def fetchServerUsers(server):
    users = mispGetRequest(server, 'admin/users/index')
    if 'error' in users:
        return []
    return users

def getConnectedServerStatus(server, connectedServer):
    connectionTest = mispGetRequest(server, f'/servers/testConnection/{connectedServer["Server"]["id"]}')
    connectionUser = mispGetRequest(server, f'/servers/getRemoteUser/{connectedServer["Server"]["id"]}')
    connectionTest['timestamp'] = int(time.time())
    connectedServer['connectionTest'] = parseMISPConnectionOutput(connectionTest)
    connectedServer['connectionUser'] = parseMISPUserConnectionOutput(connectionUser)
    connectedServer['vid'] = f"{server.id}-{connectedServer['Server']['id']}"
    return connectedServer

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

def parseGetVersion(connection):
    parsed = {
        'color': '',
        'message': ''
    }
    if 'error' in connection:
        parsed['color'] = 'danger'
        parsed['message'] = connection['error']
    else:
        parsed['color'] = 'success'
        parsed['version'] = connection['version']
        if connection['perm_sync']:
            parsed['message'] = 'Perm Sync' 
        elif connection['perm_sighting']:
            parsed['message'] = 'Perm Sighting' 
        else:
            parsed['color'] = 'warning' 
            parsed['message'] = 'No perm' 
    return parsed

def buildNetwork(servers):
    network = []
    for server in servers:
        if server.server_info is not None:
            destinations = server.server_info.query_result['connectedServers']
            link = {}
            if isinstance(destinations, list):
                for connectedServer in destinations:
                    link = {
                        'source': {k: getattr(server, k) for k in server.to_dict() if k != 'server_info'},
                        'last_refresh': server.server_info.timestamp,
                    }
                    link['destination'] = connectedServer
                    link['vid'] = f"{link['source']['id']}-{connectedServer['Server']['id']}"
                    link['status'] = connectedServer['connectionTest']
                    link['pull'] = connectedServer['Server']['pull']
                    link['push'] = connectedServer['Server']['push']
                    pull_rules = json.loads(connectedServer['Server']['pull_rules'])
                    if not isinstance(destinations, list) and pull_rules.get('url_params', '') != '':
                        pull_rules['url_params'] = json.loads(pull_rules['url_params'])
                    push_rules = json.loads(connectedServer['Server']['push_rules'])
                    link['filtering_rules'] = {
                        'pull_rules': pull_rules,
                        'pull_rule_number': countJsonLeaves(pull_rules),
                        'push_rules': push_rules,
                        'push_rule_number': countJsonLeaves(push_rules)
                    }
                    network.append(link)
    return network

def parseGetSyncOvertime(syncLogs, afterTime=None):
    if afterTime is None:
        afterTime = dt.now() - timedelta(days=7)
    servers = defaultdict(dict)
    for logEntry in syncLogs:
        if title.startsWith('Pull from'):
            created = dt.fromisoformat(logEntry['Log']['created'])
            if created > afterTime:
                title = logEntry['Log']['title']
                url = re.search(r'Pull from (?P<url>[\S]+) .*', title).group('url')
                change = logEntry['Log']['change']
                parsedChange = re.search(r'(?P<events>[\d]+) events, (?P<proposals>[\d]+) proposals and (?P<sightings>[\d]+) sightings pulled or updated. (?P<event_failed>[\d]+) events failed or didn\'t need an update.', change)
                syncMetrics = {
                    'events': parsedChange.group('events'),
                    'events_failed': parsedChange.group('events_failed'),
                    'proposals': parsedChange.group('proposals'),
                    'sightings': parsedChange.group('sightings')
                }
                servers[url][created] = syncMetrics
    return servers

def parseGetLoginLogs(loginLogs, afterTime=None):
    if afterTime is None:
        afterTime = dt.now() - timedelta(days=7)
    logins = {
        'login': [],
        'auth_fail': []
    }
    for logEntry in loginLogs:
        created = dt.fromisoformat(logEntry['Log']['created'])
        if created > afterTime:
            action = logEntry['Log']['action']
            title = logEntry['Log']['title']
            ip = logEntry['Log'].get('ip', '')
            if action == 'login':
                parsedTitle = re.search(r'User \((?P<userid>[\d]+)\): (?P<email>[\S]+)', title)
                loginMetrics = {
                    'userid': int(parsedTitle.group('userid')),
                    'email': parsedTitle.group('email'),
                    'ip': ip,
                    'created': int(created.timestamp())
                }
            elif action == 'auth_fail':
                loginMetrics = {
                    'userid': None,
                    'email': None,
                    'ip': ip,
                    'created': int(created.timestamp())
                }
            logins[action].append(loginMetrics)
    return logins


def countJsonLeaves(json_obj, ignore_empty_string=True):
    def leaf_iterator(json_obj):
        if isinstance(json_obj, Mapping):
            for v in json_obj.values():
                for obj in leaf_iterator(v):
                    yield obj
        elif isinstance(json_obj, MutableSequence):
            for v in json_obj:
                for obj in leaf_iterator(v):
                    yield obj
        else:
            yield json_obj

    leafCount = 0
    for leaf in leaf_iterator(json_obj):
        if not ignore_empty_string or leaf:
            leafCount += 1
    return leafCount

# def getNumberOfRules(rules):
#     ruleNumber = 0
#     if 'orgs' in rules:
#         if 'NOT' in rules['orgs']:
#             ruleNumber += len(rules['orgs']['NOT'])
#         if 'OR' in rules['orgs']:
#             ruleNumber += len(rules['orgs']['OR'])
#     if 'tags' in rules:
#         if 'NOT' in rules['tags']:
#             ruleNumber += len(rules['tags']['NOT'])
#         if 'OR' in rules['tags']:
#             ruleNumber += len(rules['tags']['OR'])
    
#     {
#   "orgs": {
#     "NOT": [],
#     "OR": []
#   },
#   "tags": {
#     "NOT": [],
#     "OR": [
#       "tlp:red"
#     ]
#   },
#   "url_params": ""
# }
