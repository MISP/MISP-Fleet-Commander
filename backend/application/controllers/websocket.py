import os
from application import socketioApp
from application.DBModels import Server
from application.marshmallowSchemas import serverSchema
import application.models.servers as serverModel
from flask_socketio import SocketIO


def registerListeners():
    from application.workers.tasks import fetchServerInfoTask

    @socketioApp.on('refresh_server')
    def refresh_server(serverID):
        server = Server.query.get(serverID)
        fetchServerInfoTask.delay(serverSchema.dump(server))

    @socketioApp.on('refresh_fleet')
    def refresh_fleet(fleedID):
        servers = serverModel.index(fleedID)
        for server in servers:
            fetchServerInfoTask.delay(serverSchema.dump(server))

    @socketioApp.on('ping_server')
    def ping_server(serverID):
        pass

    @socketioApp.on('ping_fleet')
    def ping_fleet(fleedID):
        pass


class SocketioEmitter:

    def __init__(self):
        self.socketio = SocketIO(message_queue=os.environ.get('SOCKETIO_MESSAGE_QUEUE', 'redis://localhost:6379/3'))

    def udpate_server(self, data):
        self.socketio.emit('UPDATE_SERVER', data)

    def udpate_fleet(self, fleet):
        self.socketio.emit('UPDATE_FLEET', fleet)

    def server_updating(self, serverID):
        self.socketio.emit('SERVER_UPDATING', serverID)

