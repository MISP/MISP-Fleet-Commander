import os
from application import socketioApp
from application.DBModels import Server, ServerMinimal
from application.marshmallowSchemas import serverSchema, serversSchema
import application.models.servers as serverModel
from flask_socketio import SocketIO


def registerListeners():
    from application.workers.tasks import fetchServerInfoTask
    from application.workers.tasks import doServerConnectionTestTask
    from application.workers.tasks import doFleetConnectionTestTask
    from application.workers.tasks import doFleetInfoTask
    from application.workers.tasks import doCacheMonitoringImages

    @socketioApp.on('refresh_server')
    def refresh_server(serverID):
        server = ServerMinimal.query.get(serverID)
        fetchServerInfoTask.delay(serverSchema.dump(server))

    @socketioApp.on('refresh_fleet')
    def refresh_fleet(fleedID):
        servers = serverModel.index(fleedID)
        doFleetInfoTask.delay(serversSchema.dump(servers))

    @socketioApp.on('server_connection_test')
    def serverConnectionTest(serverID):
        server = ServerMinimal.query.get(serverID)
        doServerConnectionTestTask.delay(serverSchema.dump(server))

    @socketioApp.on('fleet_connection_test')
    def fleetConnectionTest(fleedID):
        servers = serverModel.index(fleedID)
        doFleetConnectionTestTask.delay(serversSchema.dump(servers))

    @socketioApp.on("refresh_server_graphs")
    def refresh_server_graphs(serverID):
        server = ServerMinimal.query.get(serverID)
        doCacheMonitoringImages.delay(serverSchema.dump(server))


class SocketioEmitter:

    def __init__(self):
        self.socketio = SocketIO(message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', f'redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3'))

    def udpate_server(self, data):
        self.socketio.emit('UPDATE_SERVER', data)

    def udpate_server_connection_list(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "connectedServers",
            "data": data,
        }
        self.socketio.emit('UPDATE_SERVER_PARTIAL_DATA', payload)

    def udpate_server_usage(self, server, data):
        payload = {
            "server_id": server.id,
            "server": serverSchema.dump(server),
            "partial_data_key": "serverUsage",
            "data": data,
        }
        self.socketio.emit('UPDATE_SERVER_PARTIAL_DATA', payload)

    def udpate_server_connection(self, data):
        self.socketio.emit('UPDATE_SERVER_CONNECTION', data)

    def udpate_fleet(self, fleet):
        self.socketio.emit('UPDATE_FLEET', fleet)

    def server_updating(self, serverID):
        self.socketio.emit('SERVER_UPDATING', serverID)

    def server_status_updating(self, serverID):
        self.socketio.emit('SERVER_STATUS_UPDATING', serverID)

    def server_graphs_updating(self, serverID):
        self.socketio.emit("SERVER_GRAPHS_UPDATING", serverID)

    def server_graphs_update_done(self, serverID, timestamp):
        self.socketio.emit("SERVER_GRAPHS_UPDATE_DONE", serverID)
        server = ServerMinimal.query.get(serverID)
        payload = {
            "server_id": serverID,
            "partial_data_key": "_monitoringGraphLastRefresh",
            "data": {
                "monitoring_graph_last_refresh": timestamp,
            },
            "server": serverSchema.dump(server),
        }
        self.socketio.emit("UPDATE_SERVER_PARTIAL_DATA", payload)

    def server_graphs_resfresh_status(self, serverID, status):
        payload = {
            "server_id": serverID,
            "status": status,
        }
        self.socketio.emit("SERVER_GRAPH_REFRESH_STATUS", payload)

    def fleet_update_timestamps(self, fleet_id: int, watched_timestamp = None, monitored_timestamp = None):
        payload = { 'fleet_id':  fleet_id }
        if watched_timestamp is not None:
            payload["watched_timestamp"] = watched_timestamp
        if monitored_timestamp is not None:
            payload["monitored_timestamp"] = monitored_timestamp

        self.socketio.emit("FLEET_UPDATE_TIMESTAMPS", payload)
