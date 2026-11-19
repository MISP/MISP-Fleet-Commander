#!/usr/bin/env python3

import os
from pathlib import Path
import json
import concurrent.futures
from collections.abc import Mapping, MutableSequence
from flask import Blueprint, request, jsonify, abort
from marshmallow import ValidationError

from application.DBModels import db, User, Server
from application.controllers.utils import mispGetHTMLRequest, mispGetRequest, batchRequest
from application.marshmallowSchemas import ServerSchema, serverQuerySchema, serverSchema, taskSchema, serversSchema, serversListSchema
import application.models.servers as serverModel
import application.models.syncActivity as syncActivityModel
import application.models.metrics as metricModel
import application.models.metricSeries as metricSeriesModel
import application.models.benchmarks as benchmarkModel
import application.models.instancePicture as instancePictureModel
import application.models.queryCapability as queryCapabilityModel
from application.controllers.instance import token_required
from application.health.links import classify_link, latest_release_for
import application.health.versions as healthVersions

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
        serversDict = serversListSchema.dump(servers)
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
    queryCapabilityModel.forget(server.id)  # another URL or key: another answer
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
    """Edit a sync connection of the server, recorded as a one-server job. A change MISP refuses is a 502 whose
    message says why"""
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    payload = request.json or {}
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'error': 'Server does not exist'})
    remoteName = payload.get('name') if isinstance(payload, dict) else None
    title = f'Edit the sync connection to {remoteName or f"#{remote_server_id}"} on {server.name}'
    unit = jobRunner.runInline(user, 'edit_connection', server,
                               {'remote_server_id': remote_server_id, 'payload': payload}, title=title,
                               emitter=socketEmitter)
    if not unit.ok:
        return jsonify({'error': unit.summary, 'message': f'MISP did not save the change: {unit.summary}'}), 502
    serverConnectionList = serverModel.refreshServerConnectionList(server.id, remote_server_id)
    if serverConnectionList is None:
        return jsonify({'error': 'Something went wrong when getting updated connection lits'})
    return jsonify(unit.response)


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
                "status": "queued",
                "message": f"Queued Server({server_id}).queryInfo",
            }
        )
    else:
        return jsonify({'error': 'Unkown server'})

@BPserver.route('/servers/getUsers/<int:server_id>', methods=['GET'])
@token_required
def getUsers(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'message': 'Unknown server'}), 404
    users = fetchServerUsers(server)
    if not isinstance(users, list):
        reason = users.get('error') or users.get('message') if isinstance(users, dict) else None
        return jsonify({'message': f'Could not list the users of {server.name}: {reason or "unexpected answer"}'}), 502
    return jsonify(users)

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


@BPserver.route("/servers/getInstancePicture/<int:server_id>", methods=["GET"])
@token_required
def getInstancePicture(user, server_id):
    """The logo of the server's login page as a data URI, '' when there is none"""
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify('')
    # Read anonymously: without an authkey, MISP serves the login page
    anonymousServer = DictToObject(id=server.id, name=server.name, url=server.url, skip_ssl=server.skip_ssl, authkey=None)
    return jsonify(instancePictureModel.getPicture(server, anonymousServer))


@BPserver.route('/servers/syncOvertime/<int:server_id>', methods=['GET'])
@token_required
def syncOvertime(user, server_id):
    """Pulls and pushes of the last 7 days per sync server, from the server's MISP logs. Cached 10 minutes;
    `?refresh=1` reads the logs again"""
    server = serverModel.getForUser(user, server_id)
    if server is None:
        abort(404)
    refresh = request.args.get('refresh', '0') not in ('', '0', 'false')
    return jsonify(syncActivityModel.getSyncActivity(server, refresh=refresh))

@BPserver.route('/servers/metrics/<int:server_id>', methods=['GET'])
@token_required
def serverMetrics(user, server_id):
    """Stored usage metrics of the server over `range` (24h, 7d, 30d, 90d, 1y), optionally from another `tier`
    (raw, hour, day) and only the `metrics` given (comma-separated keys), with the collection's state"""
    server = serverModel.getForUser(user, server_id)
    if server is None:
        abort(404)
    try:
        rangeName, tier, keys = metricSeriesModel.parseRequest(request.args.get('range'), request.args.get('tier'),
                                                               request.args.get('metrics'))
    except metricSeriesModel.SeriesRequestError as e:
        return jsonify({'message': str(e)}), 400
    return jsonify(metricSeriesModel.series(server, rangeName, tier, keys, metricModel.monitoringSettings()))

@BPserver.route('/servers/queryCapability/<int:server_id>', methods=['GET'])
@token_required
def serverQueryCapability(user, server_id):
    """Whether the server runs complex queries, from its answer to `GET /attributes/queryDescribe` with its key.
    Cached an hour (a minute when it did not answer clearly); `?refresh=1` asks it again"""
    server = serverModel.getForUser(user, server_id)
    if server is None:
        abort(404)
    refresh = request.args.get('refresh', '0') not in ('', '0', 'false')
    return jsonify(queryCapabilityModel.get(server, refresh=refresh))

@BPserver.route('/servers/benchmarks/<int:server_id>', methods=['GET'])
@token_required
def serverBenchmarks(user, server_id):
    """Today's most expensive endpoints of the server, from MISP's benchmarking. Cached 5 minutes; `?refresh=1`
    asks MISP again"""
    server = serverModel.getForUser(user, server_id)
    if server is None:
        abort(404)
    refresh = request.args.get('refresh', '0') not in ('', '0', 'false')
    return jsonify(benchmarkModel.getBenchmarks(server, refresh=refresh))

@BPserver.route('/servers/restQuery/<int:server_id>', methods=['POST'])
@token_required
def restQuery(user, server_id):
    """A raw query to one server. POST queries can change the server, so they are recorded as one-server jobs"""
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    from application.models.jobUnits import restQuery as sendRestQuery
    body = request.json or {}
    queryURL, queryData, queryMethod = body.get('url'), body.get('data'), (body.get('method') or 'GET').upper()
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({})
    if queryMethod != 'POST':
        return jsonify(sendRestQuery(server, queryMethod, queryURL, queryData))
    unit = jobRunner.runInline(user, 'rest_query', server, {'method': queryMethod, 'url': queryURL, 'data': queryData},
                               title=f'POST {queryURL} on {server.name}', emitter=socketEmitter)
    return jsonify(unit.response)


def fetchServerUsers(server):
    """The users of the MISP instance, or MISP's error. Not cached: the list must reflect user administration
    actions immediately"""
    return mispGetRequest(server, 'admin/users/index', nocache=True)

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
