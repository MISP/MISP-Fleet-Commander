from application import socketioApp
from application.DBModels import Server
from application.marshmallowSchemas import serverSchema
from flask_socketio import SocketIO



def registerListeners():
    from application.workers.tasks import fetchServerInfoTask

    @socketioApp.on('refresh_server')
    def refresh_server(serverID):
        server = Server.query.get(serverID)
        fetchServerInfoTask.delay(serverSchema.dump(server))

    @socketioApp.on('refresh_fleet')
    def refresh_fleet(fleedID):
        pass

    @socketioApp.on('ping_server')
    def ping_server(serverID):
        pass

    @socketioApp.on('ping_fleet')
    def ping_fleet(fleedID):
        pass


class SocketioEmitter:

    def __init__(self):
        self.socketio = SocketIO(message_queue='redis://localhost:6379/3')

    def udpate_server(self, data):
        self.socketio.emit('UPDATE_SERVER', data)

    def udpate_fleet(self, fleet):
        pass