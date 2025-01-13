#!/usr/bin/env python3

import time
import json
import re
import concurrent.futures
from datetime import datetime as dt, timedelta
from collections.abc import Mapping, MutableSequence
from collections import defaultdict
from flask import Blueprint, request, jsonify, abort, Response
from marshmallow import ValidationError

from application.DBModels import db, User, Server
from application.controllers.utils import mispGetRequest, mispPostRequest, batchRequest
from application.marshmallowSchemas import ServerSchema, serverSchemaLighter, fleetSchema, serverQuerySchema, serverSchema, serversSchemaLighter, taskSchema, serverSchema, serversSchema
import application.models.servers as serverModel
from application.workers.tasks import fetchServerInfoTask
from application.controllers.instance import token_required


BPserver = Blueprint('server', __name__)

class DictToObject:
    def __init__(self, **entries):
        self.__dict__.update(entries)


@BPserver.route('/servers/index/<int:fleet_id>', methods=['GET'])
@token_required
def index(user, fleet_id=None):
    servers = serverModel.indexForUser(user, fleet_id)
    if servers:
        serversDict = serversSchema.dump(servers)
        return jsonify(serversDict)
    else:
        return jsonify([])


@BPserver.route('/servers/get/<int:server_id>', methods=['GET'])
@token_required
def get(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        return serverSchema.dump(server)
    else:
        return jsonify({})


@BPserver.route('/servers/add/<int:fleet_id>', methods=['POST'])
@token_required
def add(user, fleet_id):
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
                        fleet_id=fleet_id,
                        user_id=user.id)
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
                        fleet_id=fleet_id,
                        user_id=user.id)
        db.session.add(server)
        if request.json.get('recursive_add', False):
            # recursively add servers
            pass
        db.session.commit()
        return serverSchema.dump(server)


@BPserver.route('/servers/edit', methods=['POST'])
@token_required
def edit(user):
    saveFields = ['name', 'comment', 'url', 'skip_ssl', 'authkey']
    server = serverModel.getForUser(user, request.json['id'])
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
@token_required
def delete(user):
    if isinstance(request.json, list):
        deletedServers = []
        for server in request.json:
            server = serverModel.getForUser(user, server['id'])
            if server is not None:
                db.session.delete(server)
                deletedServers.append(server.id)
        db.session.commit()
        return serversSchema.dump(deletedServers)
    else:
        server = serverModel.getForUser(user, request.json['id'])
        if server is not None:
            server_id = server.id
            db.session.delete(server)
            db.session.commit()
            return jsonify([server_id])
        else:
            return jsonify([])


@BPserver.route('/servers/editConnection/<int:server_id>/<int:remote_server_id>', methods=['POST'])
@token_required
def editConnection(user, server_id, remote_server_id):
    payload = request.json
    updatedConnection = serverModel.editConnection(user, server_id, remote_server_id, payload)
    if updatedConnection:
        server = serverModel.getForUser(user, server_id)
        if server is not None:
            serverConnectionList = serverModel.refreshServerConnectionList(server.id, remote_server_id)
            if serverConnectionList is not None:
                return jsonify(updatedConnection)
            else:
                return jsonify({'error': 'Something went wrong when getting updated connection lits'})
        else:
            return jsonify({'error': 'Server does not exist'})
    else:
        return jsonify({'error': 'Something went wrong when trying to update connection'})


@BPserver.route('/servers/testConnection/<int:server_id>', methods=['GET'])
@token_required
def ping_server(user, server_id):
    result = serverModel.testConnectionForUser(user, server_id)
    if result is not None:
        return jsonify(result)
    else:
        return jsonify({})

@BPserver.route('/servers/batchTestConnection/<int:fleet_id>', methods=['GET'])
@token_required
def batch_ping_server(user, fleet_id=None):
    servers = serverModel.indexForUser(user, fleet_id)
    allRequests = []
    if servers:
        for server in servers:
            allRequests.append({
                'fn': mispGetRequest,
                'server': server,
                'path': '/servers/getVersion',
                'nocache': True,
            })
        allTestConnections = batchRequest(allRequests)
        return jsonify(allTestConnections)
    else:
        return jsonify([])

@BPserver.route('/servers/queryInfo/<int:server_id>', defaults={'no_cache': False}, methods=['GET'])
@BPserver.route('/servers/queryInfo/<int:server_id>/<int:no_cache>', methods=['GET'])
@token_required
def queryInfo(user, server_id, no_cache):
    info = serverModel.getServerInfoForUser(user, server_id, not no_cache)
    if info:
        return serverQuerySchema.dump(info)
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/queryInfoWS/<int:server_id>', methods=['GET'])
@token_required
def queryInfoWS(user, server_id,):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        server_query_task = fetchServerInfoTask.delay(serverSchemaLighter.dump(server))
        return taskSchema.dump(
            {
                "id": server_query_task.id,
                "status": server_query_task.status,
                "message": f"Queued Server({server_id}).queryInfo",
            }
        )
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/getUsers/<int:server_id>', methods=['GET'])
@token_required
def getUsers(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        server_query_users = fetchServerUsers(server)
        return jsonify(server_query_users)
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/batchTest', methods=['POST'])
@token_required
def batchTest(user):
    test_result = []
    allVersionRequests = []
    allUserRequests = []
    server_to_test = request.json
    for index, server in enumerate(server_to_test):
        serverObject = DictToObject(**server)
        if 'id' not in server:
            serverObject.id = index

        server = serverModel.getForUser(user, serverObject.id) # Make sure user has access to this server
        if server is None:
            continue

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
@token_required
def discoverConnected(user):
    rootServer = request.json
    test_result = []
    if rootServer:
        rootServerObject = DictToObject(**rootServer)

        server = serverModel.getForUser(user, rootServerObject.id) # Make sure user has access to this server
        if server is None:
            return jsonify({'error': 'Unkown server'})

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

@BPserver.route('/servers/network/<int:fleet_id>')
@token_required
def network(user, fleet_id=None):
    servers = serverModel.indexForUser(user, fleet_id)
    network = buildNetwork(servers)
    return jsonify(network)

@BPserver.route('/servers/getConnection/<int:server_id>/<int:connection_id>')
@token_required
def getConnection(user, server_id, connection_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        destinations = server.server_info['query_result']['connectedServers']
        connection = [ d for d in destinations if int(d['Server']['id']) == connection_id]
        if len(connection) > 0:
            connection = connection[0]
            connection = updateConnectionForNetwork(server, connection)
            return jsonify(connection)
        else:
            return jsonify({})
    else:
        return jsonify({})

@BPserver.route('/servers/syncOvertime/<int:server_id>', methods=['GET'])
@token_required
def syncOvertime(user, server_id):
    server = serverModel.getForUser(user, server_id)
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
@token_required
def loginOvertime(user, server_id):
    server = serverModel.getForUser(user, server_id)
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
@token_required
def restQuery(user, server_id):
    queryURL = request.json['url']
    queryData = request.json['data']
    queryMethod = request.json['method']
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        if queryMethod == 'POST':
            try:
                queryData = json.loads(queryData)
            except:
                pass
            response = mispPostRequest(server, queryURL, queryData, rawResponse=True, nocache=True)
        else:
            response = mispGetRequest(server, queryURL, rawResponse=True, nocache=True)
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
            'elapsed_time': str(response.elapsed),
            'url': response.url,
            'server_id': server_id,
        }
        return jsonify(result)
    else:
        return jsonify({})


def fetchServerUsers(server):
    users = mispGetRequest(server, 'admin/users/index')
    if 'error' in users:
        return []
    return users

def getConnectedServerStatus(server, connectedServer):
    connectedServerStatus = serverModel.getConnectedServerStatus(server, connectedServer)
    return connectedServerStatus

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
            destinations = server.server_info['query_result']['connectedServers']
            link = {}
            if isinstance(destinations, list):
                for connectedServer in destinations:
                    link = updateConnectionForNetwork(server, connectedServer)
                    network.append(link)
    return network

def updateConnectionForNetwork(server, connectedServer):
    link = {
        'source': ServerSchema(exclude=('server_info', )).dump(server),
        'last_refresh': server.server_info['timestamp'],
    }
    link['destination'] = connectedServer
    link['vid'] = f"{link['source']['id']}-{connectedServer['Server']['id']}"
    link['status'] = connectedServer['connectionTest']
    link['pull'] = connectedServer['Server']['pull']
    link['push'] = connectedServer['Server']['push']
    pull_rules = json.loads(connectedServer['Server']['pull_rules'])
    if pull_rules.get('url_params', '') != '':
        pull_rules['url_params'] = json.loads(pull_rules['url_params'])
    push_rules = json.loads(connectedServer['Server']['push_rules'])
    link['filtering_rules'] = {
        'pull_rules': pull_rules,
        'pull_rule_number': countJsonLeaves(pull_rules),
        'push_rules': push_rules,
        'push_rule_number': countJsonLeaves(push_rules)
    }
    return link


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
