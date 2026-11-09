import os
from flask import request, session
from flask_socketio import SocketIO, ConnectionRefusedError, emit, join_room
from application import socketioApp
from application.DBModels import Server, ServerMinimal, Fleet, User
from application.marshmallowSchemas import serverSchema
import application.models.servers as serverModel
import application.models.fleets as fleetModel

from application.controllers.instance import AuthenticationError, resolve_user, workers_health_check as do_workers_health_check

socketEmitter = None


def userRoom(user_id: int) -> str:
    """Every socket of a user joins this room; events about a user's servers and fleets are only sent there"""
    return f"user:{user_id}"


def resolveSocketUser(auth):
    """The user behind the socket.io `auth` payload: `{"token": "<jwt>"}`, or an `Authorization`-style credential
    (`Bearer <jwt>` or `Apikey <key>`) in `token`"""
    token = (auth or {}).get('token') if isinstance(auth, dict) else None
    if not token:
        return None
    credential = token if ' ' in token.strip() else f"Bearer {token}"
    try:
        user = resolve_user(credential)
    except AuthenticationError:
        return None
    # Like the REST API, nothing is available before a well-known password is changed
    return None if user.must_change_password else user


def currentSocketUser():
    user_id = session.get('user_id')
    if user_id is None:
        return None
    return User.query.get(user_id)


def ownedServer(server_id):
    user = currentSocketUser()
    if user is None or server_id is None:
        return None
    return serverModel.getForUser(user, server_id)


def ownedFleet(fleet_id):
    user = currentSocketUser()
    if user is None or fleet_id is None:
        return None
    return fleetModel.getForUser(user, fleet_id)


def registerListeners():

    @socketioApp.on('connect')
    def connect(auth=None):
        user = resolveSocketUser(auth)
        if user is None:
            raise ConnectionRefusedError('unauthorized')
        session['user_id'] = user.id
        join_room(userRoom(user.id))

    # Requests for servers or fleets the user doesn't own are ignored

    @socketioApp.on('refresh_server')
    def refresh_server(serverID):
        from application.workers.tasks import fetchServerInfoTask
        server = ownedServer(serverID)
        if server is not None:
            fetchServerInfoTask(server.id)

    @socketioApp.on('refresh_fleet')
    def refresh_fleet(fleedID):
        from application.workers.tasks import doFleetInfoTask
        fleet = ownedFleet(fleedID)
        if fleet is not None:
            doFleetInfoTask([server.id for server in fleet.servers])

    @socketioApp.on('server_connection_test')
    def serverConnectionTest(serverID):
        from application.workers.tasks import doServerConnectionTestTask
        server = ownedServer(serverID)
        if server is not None:
            doServerConnectionTestTask(server.id)

    @socketioApp.on('fleet_connection_test')
    def fleetConnectionTest(fleedID):
        from application.workers.tasks import doFleetConnectionTestTask
        fleet = ownedFleet(fleedID)
        if fleet is not None:
            doFleetConnectionTestTask([server.id for server in fleet.servers])

    @socketioApp.on('fleet_link_test')
    def fleetLinkTest(fleedID):
        from application.workers.tasks import doLinkTestTask
        fleet = ownedFleet(fleedID)
        if fleet is not None:
            doLinkTestTask([server.id for server in fleet.servers])

    @socketioApp.on('server_link_test')
    def serverLinkTest(payload):
        """A server ID tests all its links; `{"server_id": .., "remote_server_id": ..}` tests one of them"""
        from application.workers.tasks import doLinkTestTask
        remoteServerID = None
        if isinstance(payload, dict):
            serverID, remoteServerID = payload.get('server_id'), payload.get('remote_server_id')
            if remoteServerID is not None and not str(remoteServerID).isdigit():
                return
        else:
            serverID = payload
        server = ownedServer(serverID)
        if server is not None:
            doLinkTestTask([server.id], remote_server_id=None if remoteServerID is None else int(remoteServerID))

    @socketioApp.on("refresh_server_graphs")
    def refresh_server_graphs(serverID):
        from application.workers.tasks import doCacheMonitoringImages
        server = ownedServer(serverID)
        if server is not None:
            doCacheMonitoringImages(server.id)

    @socketioApp.on("workers_health_check")
    def workers_health_check():
        ok = do_workers_health_check(sid=request.sid)
        if ok is not True:  # Pong has already been replied by the worker
            emit('PONG', {'ok': False})


class SocketioEmitter:
    """Emits events from any process (web or workers) through the message queue.
    Events about a server or fleet only go to the room of the user owning it; nothing is broadcast."""

    def __init__(self):
        self.socketio = SocketIO(message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', f"redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3"))

    @staticmethod
    def _serverOwner(server):
        """Owner of a server given as a model instance or an ID"""
        if hasattr(server, 'user_id'):
            return server.user_id
        return Server.query.with_entities(Server.user_id).filter_by(id=server).scalar()

    @staticmethod
    def _fleetOwner(fleet):
        """Owner of a fleet given as a model instance or an ID"""
        if hasattr(fleet, 'user_id'):
            return fleet.user_id
        return Fleet.query.with_entities(Fleet.user_id).filter_by(id=fleet).scalar()

    @staticmethod
    def _id(model):
        return model.id if hasattr(model, 'id') else model

    def _emitToServerOwner(self, event, server, data):
        user_id = self._serverOwner(server)
        if user_id is not None:
            self.socketio.emit(event, data, to=userRoom(user_id))

    def pong(self, ok, sid):
        self.socketio.emit('PONG', {'ok': ok}, to=sid)

    def udpate_server(self, server, data):
        self._emitToServerOwner('UPDATE_SERVER', server, data)

    def udpate_server_connection_list(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "connectedServers",
            "data": data,
        }
        self._emitToServerOwner('UPDATE_SERVER_PARTIAL_DATA', server, payload)

    def udpate_server_usage(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "serverUsage",
            "data": data,
        }
        self._emitToServerOwner('UPDATE_SERVER_PARTIAL_DATA', server, payload)

    def udpate_server_connection(self, server, data):
        self._emitToServerOwner('UPDATE_SERVER_CONNECTION', server, data)

    def health_updated(self, server, payload):
        """`{server_id, fleet_id, issues}`: the server's current issues, acknowledged ones included"""
        self._emitToServerOwner('HEALTH_UPDATED', server, payload)

    def server_updating(self, server):
        self._emitToServerOwner('SERVER_UPDATING', server, self._id(server))

    def server_status_updating(self, server):
        self._emitToServerOwner('SERVER_STATUS_UPDATING', server, self._id(server))

    def server_link_test(self, server, testing, error=None):
        """`{server_id, testing}`: a link test of the server started (`true`) or ended (`false`, with `error` if it
        could not be done; the links are then unchanged)"""
        payload = {"server_id": self._id(server), "testing": testing}
        if error:
            payload["error"] = error
        self._emitToServerOwner('SERVER_LINK_TEST', server, payload)

    def server_graphs_updating(self, server):
        self._emitToServerOwner("SERVER_GRAPHS_UPDATING", server, self._id(server))

    def server_graphs_update_done(self, serverID, timestamp):
        server = ServerMinimal.query.get(serverID)
        if server is None:
            return
        self._emitToServerOwner("SERVER_GRAPHS_UPDATE_DONE", server, serverID)
        payload = {
            "server_id": serverID,
            "partial_data_key": "_monitoringGraphLastRefresh",
            "data": {
                "monitoring_graph_last_refresh": timestamp,
            },
            "server": serverSchema.dump(server),
        }
        self._emitToServerOwner("UPDATE_SERVER_PARTIAL_DATA", server, payload)

    def server_graphs_resfresh_status(self, serverID, status):
        payload = {
            "server_id": serverID,
            "status": status,
        }
        self._emitToServerOwner("SERVER_GRAPH_REFRESH_STATUS", serverID, payload)

    def fleet_update_timestamps(self, fleet, watched_timestamp = None, monitored_timestamp = None):
        user_id = self._fleetOwner(fleet)
        if user_id is None:
            return
        payload = { 'fleet_id':  self._id(fleet) }
        if watched_timestamp is not None:
            payload["watched_timestamp"] = watched_timestamp
        if monitored_timestamp is not None:
            payload["monitored_timestamp"] = monitored_timestamp

        self.socketio.emit("FLEET_UPDATE_TIMESTAMPS", payload, to=userRoom(user_id))


socketEmitter = SocketioEmitter()
