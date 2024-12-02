#!/usr/bin/env python3

import time
from application import celery_app
from application.controllers.websocket import SocketioEmitter
from application.marshmallowSchemas import serverSchemaLighter
import application.models.servers as serverModel


socketioEmitter = SocketioEmitter()


@celery_app.task(name="fetchServerInfoTask")
def fetchServerInfoTask(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_updating(server.id)
    # serverInfo = serverModel.fetchServerInfo(server)
    serverInfo = serverModel.fetchServerInfoAsync(server)
    if serverInfo is not None:
        serverInfo['server'] = serverDict
    socketioEmitter.udpate_server(serverInfo)


@celery_app.task(name="doServerConnectionTestTask")
def doServerConnectionTestTask(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_status_updating(server.id)
    # connectionInfo = serverModel.testConnection(server.id)
    connectionInfo = serverModel.testConnectionAsync(server.id)
    if connectionInfo is not None:
        # connectionInfo['server'] = {'uuid': server.uuid, 'id': server.id}
        connectionInfo['server'] = serverSchemaLighter.dump(server)
    socketioEmitter.udpate_server_connection(connectionInfo)

