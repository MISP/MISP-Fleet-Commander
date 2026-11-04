import os
from flask import current_app, request
from application import socketioApp
from application.DBModels import Fleet, Server, ServerMinimal, User
from application.marshmallowSchemas import serverSchema, serversSchema
import application.models.servers as serverModel
import application.models.users as userModel
from application.models.auth import get_email_from_token
import jwt
from flask_socketio import SocketIO, emit, join_room

from application.controllers.instance import workers_health_check as do_workers_health_check

socketEmitter = None

# Maps a connected socket session id to the id of the authenticated user
socketUserIDBySID = {}


def userRoom(user_id):
    return f'user_{user_id}'


def getUserFromAuth(auth):
    """Resolve the user owning the credentials sent by the client on connection.
    Mirrors the `token_required` decorator used by the HTTP controllers."""
    if type(auth) is not dict:
        return None
    token_value = auth.get('token')
    token_type = str(auth.get('token_type', 'bearer')).lower()
    if not token_value:
        return None
    if token_type == 'bearer':
        try:
            email = get_email_from_token(token_value, current_app)
        except jwt.InvalidTokenError:
            return None
        return userModel.getByEmail(email)
    elif token_type == 'apikey':
        return User.query.filter_by(apikey=token_value).first()
    return None


def getCurrentSocketUser():
    user_id = socketUserIDBySID.get(request.sid)
    if user_id is None:
        return None
    return User.query.get(user_id)


def registerListeners():

    @socketioApp.on('connect')
    def connect(auth):
        user = getUserFromAuth(auth)
        if user is None:
            # Unauthenticated sockets stay connected but join no room, so they
            # neither receive any data nor can trigger any listener.
            return
        socketUserIDBySID[request.sid] = user.id
        join_room(userRoom(user.id))

    @socketioApp.on('disconnect')
    def disconnect(reason=None):
        socketUserIDBySID.pop(request.sid, None)

    @socketioApp.on('refresh_server')
    def refresh_server(serverID):
        from application.workers.tasks import fetchServerInfoTask
        user = getCurrentSocketUser()
        if user is None:
            return
        server = ServerMinimal.query.filter_by(id=serverID, user_id=user.id).first()
        if server is None:
            return
        fetchServerInfoTask(serverSchema.dump(server))

    @socketioApp.on('refresh_fleet')
    def refresh_fleet(fleedID):
        from application.workers.tasks import doFleetInfoTask
        user = getCurrentSocketUser()
        if user is None:
            return
        servers = serverModel.indexForUser(user, fleedID)
        if not servers:
            return
        doFleetInfoTask(serversSchema.dump(servers))

    @socketioApp.on('server_connection_test')
    def serverConnectionTest(serverID):
        from application.workers.tasks import doServerConnectionTestTask
        user = getCurrentSocketUser()
        if user is None:
            return
        server = ServerMinimal.query.filter_by(id=serverID, user_id=user.id).first()
        if server is None:
            return
        doServerConnectionTestTask(serverSchema.dump(server))

    @socketioApp.on('fleet_connection_test')
    def fleetConnectionTest(fleedID):
        from application.workers.tasks import doFleetConnectionTestTask
        user = getCurrentSocketUser()
        if user is None:
            return
        servers = serverModel.indexForUser(user, fleedID)
        if not servers:
            return
        doFleetConnectionTestTask(serversSchema.dump(servers))

    @socketioApp.on("refresh_server_graphs")
    def refresh_server_graphs(serverID):
        from application.workers.tasks import doCacheMonitoringImages
        user = getCurrentSocketUser()
        if user is None:
            return
        server = ServerMinimal.query.filter_by(id=serverID, user_id=user.id).first()
        if server is None:
            return
        doCacheMonitoringImages(serverSchema.dump(server))

    @socketioApp.on("workers_health_check")
    def workers_health_check():
        if getCurrentSocketUser() is None:
            return
        ok = do_workers_health_check()
        if ok is not True:  # Pong has already been replied by the worker
            emit('PONG', {'ok': False})


class SocketioEmitter:

    def __init__(self):
        self.socketio = SocketIO(message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', f"redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3"))

    def emitToUser(self, event, payload, user_id):
        if user_id is None:  # Owner unknown: never broadcast to everybody
            return
        self.socketio.emit(event, payload, to=userRoom(user_id))

    def serverOwnerID(self, serverID):
        server = ServerMinimal.query.get(serverID)
        return server.user_id if server is not None else None

    def fleetOwnerID(self, fleetID):
        fleet = Fleet.query.get(fleetID)
        return fleet.user_id if fleet is not None else None

    def pong(self, ok):
        # Worker liveness only, carries no user data
        self.socketio.emit('PONG', {'ok': ok})

    def udpate_server(self, data):
        self.emitToUser('UPDATE_SERVER', data, self.serverOwnerID(data['server']['id']))

    def udpate_server_connection_list(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "connectedServers",
            "data": data,
        }
        self.emitToUser('UPDATE_SERVER_PARTIAL_DATA', payload, server.user_id)

    def udpate_server_usage(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "serverUsage",
            "data": data,
        }
        self.emitToUser('UPDATE_SERVER_PARTIAL_DATA', payload, server.user_id)

    def udpate_server_connection(self, data):
        if data is None or data.get('server') is None:
            return
        self.emitToUser('UPDATE_SERVER_CONNECTION', data, self.serverOwnerID(data['server']['id']))

    def udpate_fleet(self, fleet):
        self.emitToUser('UPDATE_FLEET', fleet, self.fleetOwnerID(fleet['id']))

    def server_updating(self, serverID):
        self.emitToUser('SERVER_UPDATING', serverID, self.serverOwnerID(serverID))

    def server_status_updating(self, serverID):
        self.emitToUser('SERVER_STATUS_UPDATING', serverID, self.serverOwnerID(serverID))

    def server_graphs_updating(self, serverID):
        self.emitToUser("SERVER_GRAPHS_UPDATING", serverID, self.serverOwnerID(serverID))

    def server_graphs_update_done(self, serverID, timestamp):
        server = ServerMinimal.query.get(serverID)
        if server is None:
            return
        self.emitToUser("SERVER_GRAPHS_UPDATE_DONE", serverID, server.user_id)
        payload = {
            "server_id": serverID,
            "partial_data_key": "_monitoringGraphLastRefresh",
            "data": {
                "monitoring_graph_last_refresh": timestamp,
            },
            "server": serverSchema.dump(server),
        }
        self.emitToUser("UPDATE_SERVER_PARTIAL_DATA", payload, server.user_id)

    def server_graphs_resfresh_status(self, serverID, status):
        payload = {
            "server_id": serverID,
            "status": status,
        }
        self.emitToUser("SERVER_GRAPH_REFRESH_STATUS", payload, self.serverOwnerID(serverID))

    def fleet_update_timestamps(self, fleet_id: int, watched_timestamp = None, monitored_timestamp = None):
        payload = { 'fleet_id':  fleet_id }
        if watched_timestamp is not None:
            payload["watched_timestamp"] = watched_timestamp
        if monitored_timestamp is not None:
            payload["monitored_timestamp"] = monitored_timestamp

        self.emitToUser("FLEET_UPDATE_TIMESTAMPS", payload, self.fleetOwnerID(fleet_id))


socketEmitter = SocketioEmitter()
