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
    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaLighter.dump(server)
        socketioEmitter.udpate_server(testResult)
    serverModel.dofetchServerInfoAsync(server, clientSocketEmitterUpdateFun)


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


@celery_app.task(name="doCacheMonitoringImages")
def doCacheMonitoringImages(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_graphs_updating(server.id)

    callbacks = {
        "server_graphs_resfresh_status": socketioEmitter.server_graphs_resfresh_status,
        "server_graphs_update_done": socketioEmitter.server_graphs_update_done,
    }
    serverModel.cacheMonitoringImages([server], force=True, callbacks=callbacks)
    # socketioEmitter.server_graphs_update_done(server.id)
