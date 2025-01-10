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
    serverInfo = serverModel.fetchServerInfoAsync(server)
    if serverInfo is not None:
        serverInfo['server'] = serverDict
    socketioEmitter.udpate_server(serverInfo)


@celery_app.task(name="doFleetInfoTask")
def doFleetInfoTask(servers):
    server_ids = []
    serversDict = []
    serverByID = {}
    for serverDict in servers:
        server = serverSchemaLighter.load(serverDict)
        serversDict.append(server)
        serverByID[server.id] = server
        server_ids.append(server.id)
        socketioEmitter.server_updating(server.id)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaLighter.dump(serverByID[server_id])
        socketioEmitter.udpate_server(testResult)
    serverModel.doFleetInfoTask(serversDict, clientSocketEmitterUpdateFun)


@celery_app.task(name="doServerConnectionTestTask")
def doServerConnectionTestTask(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_status_updating(server.id)
    connectionInfo = serverModel.testConnectionAsync(server.id)
    if connectionInfo is not None:
        connectionInfo['server'] = serverSchemaLighter.dump(server)
    socketioEmitter.udpate_server_connection(connectionInfo)


@celery_app.task(name="doFleetConnectionTestTask")
def doFleetConnectionTestTask(servers):
    server_ids = []
    serversDict = []
    serverByID = {}
    for serverDict in servers:
        server = serverSchemaLighter.load(serverDict)
        serversDict.append(server)
        serverByID[server.id] = server
        server_ids.append(server.id)
        socketioEmitter.server_status_updating(server.id)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaLighter.dump(serverByID[server_id])
        socketioEmitter.udpate_server_connection(testResult)
    serverModel.testAllConnectionAsync(serversDict, clientSocketEmitterUpdateFun)

