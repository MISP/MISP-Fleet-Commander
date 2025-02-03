#!/usr/bin/env python3

import asyncio
import time
from application import celery_app
from application.controllers.websocket import SocketioEmitter
from application.marshmallowSchemas import serverSchemaLighter
import application.models.servers as serverModel
import application.models.fleets as fleetModel
import application.models.setting as settingModel

from application.monitoring.monitor import monitor
from application import redisModel


socketioEmitter = SocketioEmitter()


@celery_app.task(name="fetchServerInfoTask", ignore_result=True)
def fetchServerInfoTask(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_updating(server.id)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaLighter.dump(server)
        socketioEmitter.udpate_server(testResult)

    clientSocketEmitterUpdateFuns = {
        "udpate_server": clientSocketEmitterUpdateFun,
        "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
        "udpate_server_usage": socketioEmitter.udpate_server_usage,
    }
    serverModel.dofetchServerInfoAsync(server, clientSocketEmitterUpdateFuns)


@celery_app.task(name="doFleetInfoTask", ignore_result=True)
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

    clientSocketEmitterUpdateFuns = {
        "udpate_server": clientSocketEmitterUpdateFun,
        "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
        "udpate_server_usage": socketioEmitter.udpate_server_usage,
    }
    serverModel.doFleetInfoTask(serversDict, clientSocketEmitterUpdateFuns)

    if len(serversDict) > 0:
        watched_timestamp = redisModel.getFleetWatchedTimestamp(serversDict[0].fleet_id)
        if watched_timestamp is not None:
            socketioEmitter.fleet_update_timestamps(serversDict[0].fleet_id, watched_timestamp = watched_timestamp)


@celery_app.task(name="doServerConnectionTestTask", ignore_result=True)
def doServerConnectionTestTask(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_status_updating(server.id)
    connectionInfo = serverModel.testConnectionAsync(server.id)
    if connectionInfo is not None:
        connectionInfo['server'] = serverSchemaLighter.dump(server)
    socketioEmitter.udpate_server_connection(connectionInfo)


@celery_app.task(name="doFleetConnectionTestTask", ignore_result=True)
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


@celery_app.task(name="doCacheMonitoringImages", ignore_result=True)
def doCacheMonitoringImages(serverDict):
    server = serverSchemaLighter.load(serverDict)
    socketioEmitter.server_graphs_updating(server.id)

    callbacks = {
        "server_graphs_resfresh_status": socketioEmitter.server_graphs_resfresh_status,
        "server_graphs_update_done": socketioEmitter.server_graphs_update_done,
    }
    serverModel.cacheMonitoringImages([server], force=True, callbacks=callbacks)


###
### SCHEDULER
###

@celery_app.task(name="watchMonitoredFleets", ignore_result=True)
def watchMonitoredFleets():
    if settingModel.getRefreshValue("fleet_watching_enabled"):
        fleets = fleetModel.indexWatched()
        server_ids = []
        serversDict = []
        serverByID = {}
        for fleet in fleets:
            for server in fleet.servers:
                serversDict.append(server)
                serverByID[server.id] = serverSchemaLighter.dump(server)
                server_ids.append(server.id)
                socketioEmitter.server_updating(server.id)

            def clientSocketEmitterUpdateFun(server_id, testResult):
                testResult["server"] = serverByID[server_id]
                socketioEmitter.udpate_server(testResult)

            clientSocketEmitterUpdateFuns = {
                "udpate_server": clientSocketEmitterUpdateFun,
                "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
                "udpate_server_usage": socketioEmitter.udpate_server_usage,
            }

            serverModel.doFleetInfoTask(serversDict, clientSocketEmitterUpdateFuns)
            watched_timestamp = redisModel.getFleetWatchedTimestamp(fleet.id)
            socketioEmitter.fleet_update_timestamps(fleet.id, watched_timestamp = watched_timestamp)


@celery_app.task(name="monitorMonitoredFleets", ignore_result=True)
def monitorMonitoredFleets(cache_images: bool = False):
    if settingModel.getRefreshValue("monitoring_enabled"):
        fleets = fleetModel.indexMonitored()
        asyncio.run(monitor(fleets))
        for fleet in fleets:
            monitored_timestamp = redisModel.setFleetMonitoredTimestamp(fleet.id)
            if monitored_timestamp is not None:
                socketioEmitter.fleet_update_timestamps(fleet.id, monitored_timestamp = monitored_timestamp)

        if cache_images:
            for fleet in fleets:
                asyncio.run(serverModel.doCacheMonitoringImages(fleet.servers))
