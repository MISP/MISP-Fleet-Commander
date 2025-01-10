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



class SocketioEmitter:

    def __init__(self):
        self.socketio = SocketIO(message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', f'redis://localhost:{str(os.environ.get('REDIS_PORT', 6380))}/3'))

    def udpate_server(self, data):
        self.socketio.emit('UPDATE_SERVER', data)

    def udpate_server_connection(self, data):
        self.socketio.emit('UPDATE_SERVER_CONNECTION', data)

    def udpate_fleet(self, fleet):
        self.socketio.emit('UPDATE_FLEET', fleet)

    def server_updating(self, serverID):
        self.socketio.emit('SERVER_UPDATING', serverID)

    def server_status_updating(self, serverID):
        self.socketio.emit('SERVER_STATUS_UPDATING', serverID)

