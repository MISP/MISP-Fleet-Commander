#!/usr/bin/env python3

import os
from pathlib import Path
import time
import json
import re
import concurrent.futures
from datetime import datetime as dt, timedelta, timezone
from collections.abc import Mapping, MutableSequence
from collections import defaultdict
from flask import Blueprint, request, jsonify, abort, send_from_directory
from marshmallow import ValidationError

from application import flaskApp
from application.DBModels import db, User, Server
from application.controllers.utils import mispGetHTMLRequest, mispGetRequest, mispPostRequest, batchRequest
from application.marshmallowSchemas import ServerSchema, serverQuerySchema, serverSchema, taskSchema, serversSchema
import application.models.servers as serverModel
from application.models.servers import MONITORING_PANELS, MONITORING_PANEL_BY_ID
from application.controllers.instance import token_required
from application.health.links import classify_link, latest_release_for
import application.health.versions as healthVersions
from application.models.utils import MonitoringImages

DEFAULT_PULL_RULE = {
    "tags": {"OR": [], "NOT": []},
    "orgs": {"OR": [], "NOT": []},
    "type_attributes": {"NOT": []},
    "type_objects": {"NOT": []},
    "url_params": "",
}
DEFAULT_PUSH_RULE = {
    "tags": {"OR": [], "NOT": []},
    "orgs": {"OR": [], "NOT": []},
}


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
    import application.models.fleets as fleetModel
    if fleetModel.getForUser(user, fleet_id) is None:
        abort(404, 'Unknown fleet')
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
    if server is None:
        abort(404)
    for field, value in request.json.items():
        if field == 'authkey' and not value:
            continue  # Clients never get the authkey back: an empty one means "keep the current key"
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
        from application.workers.tasks import fetchServerInfoTask
        server_query_task = fetchServerInfoTask(server.id)
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
    """Test a list of servers. Each item is either a saved server (`{"id": ...}`, tested with its stored
    authkey) or a server that is not saved yet (`{"url", "authkey", "skip_ssl"}`).
    Results come back in the request order and never contain authkeys."""
    serversToTest = {}
    for index, item in enumerate(request.json or []):
        if item.get('id') is not None:
            server = serverModel.getForUser(user, item['id'])
            if server is None:
                continue
            serversToTest[index] = DictToObject(id=index, name=server.name, url=server.url, skip_ssl=server.skip_ssl, authkey=server.authkey)
        elif item.get('url'):
            serversToTest[index] = DictToObject(id=index, name=item.get('name') or item['url'], url=item['url'],
                                                skip_ssl=bool(item.get('skip_ssl', False)), authkey=item.get('authkey') or None)

    allVersionRequests = []
    allUserRequests = []
    for serverObject in serversToTest.values():
        allVersionRequests.append({'fn': mispGetRequest, 'server': serverObject, 'path': '/servers/getVersion', 'nocache': True})
        allUserRequests.append({'fn': mispGetRequest, 'server': serverObject, 'path': '/users/view/me', 'nocache': True})
    versionByIndex = {r['server_id']: r for r in batchRequest(allVersionRequests)}
    userByIndex = {r['server_id']: r for r in batchRequest(allUserRequests)}

    test_result = []
    for index in serversToTest:
        version = versionByIndex.get(index, {'error': 'Test failed'})
        test_result.append({
            'index': index,
            'testResult': parseGetVersion(version),
            'userResult': userByIndex.get(index, {}),
        })
    return jsonify(test_result)

@BPserver.route('/servers/discoverConnected', methods=['POST'])
@token_required
def discoverConnected(user):
    """List the servers the root server syncs with. MISP never exposes the authkeys of its remote servers,
    so discovered servers come back without one; reachability is probed without authentication."""
    rootServerId = (request.json or {}).get('root_server_id')
    rootServer = serverModel.getForUser(user, rootServerId) if rootServerId is not None else None
    if rootServer is None:
        abort(404, 'Unknown server')

    rootIndex = mispGetRequest(rootServer, '/servers/index', nocache=True)
    if type(rootIndex) != list:
        abort(502, 'Could not fetch a valid server index from the root server')
    rootIndex = serverModel.stripRemoteAuthkeys(rootIndex)

    probes = []
    for index, connectedServer in enumerate(rootIndex):
        remoteServer = connectedServer['Server']
        probes.append({
            'fn': mispGetRequest,
            'server': DictToObject(id=index, name=remoteServer.get('name', ''), url=remoteServer.get('url', ''),
                                   skip_ssl=bool(remoteServer.get('self_signed', False)), authkey=None),
            'path': '/servers/getVersion',
            'nocache': True,
        })
    probeByIndex = {r['server_id']: r for r in batchRequest(probes)}

    discovered = []
    for index, connectedServer in enumerate(rootIndex):
        connectedServer['skip_ssl'] = bool(connectedServer['Server'].get('self_signed', False))
        connectedServer['testResult'] = parseReachabilityProbe(probeByIndex.get(index, {'error': 'Test failed'}))
        discovered.append(connectedServer)
    return jsonify(discovered)

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


@BPserver.route('/servers/getUsageDashboardConfig', methods=['GET'])
@token_required
def getUsageDashboardConfig(user):
    GRAFANA_BASE_URL = flaskApp.config['GRAFANA_BASE_URL']
    GRAFANA_DASHBOARD = flaskApp.config['GRAFANA_DASHBOARD']
    dashboardConfig = {
        "panels": MONITORING_PANELS,
        "grafana_base_url": GRAFANA_BASE_URL,
        "grafana_dashboard": GRAFANA_DASHBOARD,
    }
    return jsonify(dashboardConfig)


@BPserver.route("/servers/getInstancePicture/<int:server_id>", methods=["GET"])
@token_required
def getInstancePicture(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is not None:
        # Fetch the login page anonymously: without an authkey, MISP serves the login page
        anonymousServer = DictToObject(id=server.id, name=server.name, url=server.url, skip_ssl=server.skip_ssl, authkey=None)
        searchStringB64 = '<img src="data:image/png;base64,'
        searchStringURI = '<img src="'
        try:
            loginPageHtml = mispGetHTMLRequest(anonymousServer, "/users/login")
            start = loginPageHtml.find(searchStringB64)
            if start != -1:
                start += len(searchStringB64)
                end = loginPageHtml.find('"', start)
                if end != -1:
                    b64Img = loginPageHtml[start:end]
                    return jsonify(b64Img)
            start = loginPageHtml.find(searchStringURI)
            if start != -1:
                start += len(searchStringURI)
                end = loginPageHtml.find('"', start)
                if end != -1:
                    imgURI = loginPageHtml[start:end]
                    return jsonify(imgURI)
        except:
            return jsonify('')
    return jsonify('')


@BPserver.route('/servers/monitoringImage/<int:server_id>/<panel_id>', methods=['GET'])
@token_required
def monitoringImage(user, server_id, panel_id):
    server = serverModel.getForUser(user, server_id)
    if server is None or panel_id not in MONITORING_PANEL_BY_ID:
        abort(404)
    panelImage = MonitoringImages(server_id, panel_id)
    (directoryPath, imagePath) = panelImage.getImagePaths()
    return send_from_directory(directoryPath, imagePath, max_age=0)


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
        if isinstance(response, dict):
            # Request helpers return an error dict instead of a Response on failure
            return jsonify(response)
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
    # Not cached: the list must reflect user administration actions immediately
    users = mispGetRequest(server, 'admin/users/index', nocache=True)
    if 'error' in users:
        return []
    return users

def getConnectedServerStatus(server, connectedServer):
    connectedServerStatus = serverModel.getConnectedServerStatus(server, connectedServer)
    return connectedServerStatus

def readableRequestError(error):
    # Request helpers report unparsable (non-JSON) answers as raw exceptions
    if str(error).startswith('Exception'):
        return 'Unexpected answer, not a MISP API?'
    return error

def parseGetVersion(connection):
    parsed = {
        'color': '',
        'message': ''
    }
    if 'error' in connection:
        parsed['color'] = 'danger'
        parsed['message'] = readableRequestError(connection['error'])
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

def parseReachabilityProbe(probe):
    """Interpret an unauthenticated /servers/getVersion request: MISP answers 403 when it is reachable"""
    if probe.get('_status_code') == 403:
        return {'color': 'warning', 'message': 'Reachable, authkey needed'}
    if 'error' in probe:
        return {'color': 'danger', 'message': readableRequestError(probe['error'])}
    return {'color': 'warning', 'message': 'Reachable, authkey needed', 'version': probe.get('version')}

def buildNetwork(servers):
    network = []
    latest = healthVersions.latest_release()
    for server in servers:
        if server.server_info is not None:
            destinations = server.server_info['query_result']['connectedServers']
            link = {}
            if isinstance(destinations, list):
                for connectedServer in destinations:
                    link = updateConnectionForNetwork(server, connectedServer, latest)
                    network.append(link)
    return network

def updateConnectionForNetwork(server, connectedServer, latest=None):
    '''A sync link as the UI shows it. `latest` is GitHub's latest MISP release, looked up (cached) when not given'''
    link = {
        'source': ServerSchema(exclude=('server_info', )).dump(server),
        'last_refresh': server.server_info['timestamp'],
    }
    link['destination'] = connectedServer
    link['vid'] = f"{link['source']['id']}-{connectedServer['Server']['id']}"
    link['status'] = connectedServer.get('connectionTest', {})
    link['tested_at'] = link['status'].get('timestamp')
    if latest is None:
        latest = healthVersions.latest_release()
    link['health'] = classify_link(connectedServer, latest_release_for(server.server_info, latest))
    link['pull'] = connectedServer['Server']['pull']
    link['push'] = connectedServer['Server']['push']
    pull_rules = json.loads(connectedServer['Server']['pull_rules'])
    if len(pull_rules) == 0:
        pull_rules = DEFAULT_PULL_RULE
    if pull_rules.get('url_params', '') != '':
        pull_rules['url_params'] = json.loads(pull_rules['url_params'])
    push_rules = json.loads(connectedServer['Server']['push_rules'])
    if len(push_rules) == 0:
        push_rules = DEFAULT_PUSH_RULE
    link['filtering_rules'] = {
        'pull_rules': pull_rules,
        'pull_rule_number': countJsonLeaves(pull_rules),
        'push_rules': push_rules,
        'push_rule_number': countJsonLeaves(push_rules)
    }
    return link


def _toAwareUTC(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parseGetSyncOvertime(syncLogs, afterTime=None):
    if afterTime is None:
        afterTime = dt.now(timezone.utc) - timedelta(days=7)
    afterTime = _toAwareUTC(afterTime)
    servers = defaultdict(dict)
    for logEntry in syncLogs:
        title = logEntry['Log']['title']
        if title.startswith('Pull from'):
            created = dt.fromisoformat(logEntry['Log']['created'])
            if _toAwareUTC(created) > afterTime:
                urlMatch = re.search(r'Pull from (?P<url>[\S]+) .*', title)
                change = logEntry['Log']['change']
                parsedChange = re.search(r'(?P<events>[\d]+) events, (?P<proposals>[\d]+) proposals and (?P<sightings>[\d]+) sightings pulled or updated. (?P<events_failed>[\d]+) events failed or didn\'t need an update.', change)
                if urlMatch is None or parsedChange is None:
                    continue
                url = urlMatch.group('url')
                syncMetrics = {
                    'events': parsedChange.group('events'),
                    'events_failed': parsedChange.group('events_failed'),
                    'proposals': parsedChange.group('proposals'),
                    'sightings': parsedChange.group('sightings')
                }
                servers[url][created.isoformat()] = syncMetrics
    return servers

def parseGetLoginLogs(loginLogs, afterTime=None):
    if afterTime is None:
        afterTime = dt.now(timezone.utc) - timedelta(days=7)
    afterTime = _toAwareUTC(afterTime)
    logins = {
        'login': [],
        'auth_fail': []
    }
    for logEntry in loginLogs:
        created = dt.fromisoformat(logEntry['Log']['created'])
        if _toAwareUTC(created) > afterTime:
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
