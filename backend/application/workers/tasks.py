#!/usr/bin/env python3

import asyncio
from functools import wraps
import time
import uuid
from huey import crontab

from application import create_app

flaskApp = create_app()
huey_app = flaskApp.extensions["huey"]

from application.controllers.websocket import SocketioEmitter
from application.marshmallowSchemas import serverSchemaWithoutInfo
import application.models.servers as serverModel
import application.models.fleets as fleetModel
import application.models.setting as settingModel
import application.models.jobs as jobModel
import application.models.jobRunner as jobRunner
import application.models.metrics as metricModel
import application.models.metricRollups as metricRollups
from application import redisModel

from application import MONITORING_SYSTEM_AVAILABLE, MONITORING_SYSTEM as monitor

fleet_watching_interval_min = settingModel.getRefreshValue("fleet_watching_interval")
monitoring_interval_min = settingModel.getRefreshValue("monitoring_interval")

socketioEmitter = SocketioEmitter()


@huey_app.task(priority=1)
def ping(sid=None):
    """Health check: the reply only goes to the socket that asked (`sid`)"""
    if sid is not None:
        socketioEmitter.pong(True, sid)
    return 'pong'


def loadServers(server_ids):
    """Tasks receive server IDs, never serialized servers, so that authkeys stay out of the task queue"""
    servers = [serverModel.get(server_id) for server_id in server_ids]
    return [server for server in servers if server is not None]


@huey_app.task(priority=2)
def fetchServerInfoTask(server_id):
    server = serverModel.get(server_id)
    if server is None:
        return
    socketioEmitter.server_updating(server)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaWithoutInfo.dump(server)
        socketioEmitter.udpate_server(server, testResult)

    clientSocketEmitterUpdateFuns = {
        "udpate_server": clientSocketEmitterUpdateFun,
        "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
        "udpate_server_usage": socketioEmitter.udpate_server_usage,
    }
    serverModel.dofetchServerInfoAsync(server, clientSocketEmitterUpdateFuns)


@huey_app.task(priority=2)
def doFleetInfoTask(server_ids):
    serversDict = []
    serverByID = {}
    for server in loadServers(server_ids):
        serversDict.append(server)
        serverByID[server.id] = server
        socketioEmitter.server_updating(server)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaWithoutInfo.dump(serverByID[server_id])
        socketioEmitter.udpate_server(serverByID[server_id], testResult)

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


@huey_app.task(priority=5)
def doServerConnectionTestTask(server_id):
    server = serverModel.get(server_id)
    if server is None:
        return
    socketioEmitter.server_status_updating(server)
    connectionInfo = serverModel.testConnectionAsync(server.id)
    if connectionInfo is not None:
        connectionInfo['server'] = serverSchemaWithoutInfo.dump(server)
    socketioEmitter.udpate_server_connection(server, connectionInfo)


@huey_app.task(priority=5)
def doFleetConnectionTestTask(server_ids):
    serversDict = []
    serverByID = {}
    for server in loadServers(server_ids):
        serversDict.append(server)
        serverByID[server.id] = server
        socketioEmitter.server_status_updating(server)

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult['server'] = serverSchemaWithoutInfo.dump(serverByID[server_id])
        socketioEmitter.udpate_server_connection(serverByID[server_id], testResult)
    serverModel.testAllConnectionAsync(serversDict, clientSocketEmitterUpdateFun)


LINK_TEST_LOCK_TIMEOUT = 10 * 60  # Released by then even if a worker died while holding it


@huey_app.task(priority=4)
def doLinkTestTask(server_ids, remote_server_id=None):
    """Re-test the sync links of these servers (only the link to `remote_server_id` when given). A server whose links
    are already being tested is skipped, so repeated clicks do not pile tests up on its MISP"""
    servers, tokens = [], {}
    for server in loadServers(server_ids):
        token = uuid.uuid4().hex
        if redisModel.redisClient.set(f"link-test-lock:{server.id}", token, nx=True, ex=LINK_TEST_LOCK_TIMEOUT):
            tokens[server.id] = token
            servers.append(server)
            socketioEmitter.server_link_test(server, testing=True)
    if not servers:
        return

    done = set()

    def linkTestDone(server, result):
        done.add(server.id)
        lockName = f"link-test-lock:{server.id}"
        if redisModel.redisClient.get(lockName) == tokens.get(server.id):
            redisModel.redisClient.delete(lockName)
        socketioEmitter.server_link_test(server, testing=False, error=(result or {}).get("error"))

    def clientSocketEmitterUpdateFun(server_id, testResult):  # Only for a server refreshed in full (no data yet)
        server = next(s for s in servers if s.id == server_id)
        testResult["server"] = serverSchemaWithoutInfo.dump(server)
        socketioEmitter.udpate_server(server, testResult)

    callbacks = {
        "link_test_done": linkTestDone,
        "udpate_server": clientSocketEmitterUpdateFun,
        "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
        "udpate_server_usage": socketioEmitter.udpate_server_usage,
    }
    try:
        serverModel.testLinks(servers, callbacks, remote_server_id=remote_server_id,
                              max_concurrency=int(settingModel.getValue("health_max_concurrency")))
    finally:
        for server in servers:
            if server.id not in done:
                linkTestDone(server, {"error": "The link test failed unexpectedly"})


@huey_app.task()
def doCacheMonitoringImages(server_id):
    server = serverModel.get(server_id)
    if server is None:
        return
    socketioEmitter.server_graphs_updating(server)

    callbacks = {
        "server_graphs_resfresh_status": socketioEmitter.server_graphs_resfresh_status,
        "server_graphs_update_done": socketioEmitter.server_graphs_update_done,
    }
    serverModel.cacheMonitoringImages([server], force=True, callbacks=callbacks)


@huey_app.task(priority=3)
def runJob(job_id):
    """Run a queued job; its parameters are read from the job (encrypted), never passed through the queue"""
    max_concurrency = int(settingModel.getRefreshValue("job_max_concurrency"))
    jobRunner.run(job_id, socketioEmitter, max_concurrency=max_concurrency)


@huey_app.task(priority=3)
def checkBaselineTask(server_ids):
    """List again the taxonomies, galaxies and object templates the servers' baseline rules need"""
    from application.models import baselineDrift
    baselineDrift.checkServers(loadServers(server_ids), backgroundRefreshSettings()["max_concurrency"])


###
### SCHEDULER
###


@huey_app.periodic_task(crontab(minute=f"*/{fleet_watching_interval_min}"))
def watchMonitoredFleets():
    if settingModel.getRefreshValue("fleet_watching_enabled"):
        fleets = fleetModel.indexWatched()
        for fleet in fleets:
            serversDict = []
            serverByID = {}
            serverDumpByID = {}
            for server in fleet.servers:
                serversDict.append(server)
                serverByID[server.id] = server
                serverDumpByID[server.id] = serverSchemaWithoutInfo.dump(server)
                socketioEmitter.server_updating(server)

            def clientSocketEmitterUpdateFun(server_id, testResult):
                testResult["server"] = serverDumpByID[server_id]
                socketioEmitter.udpate_server(serverByID[server_id], testResult)

            clientSocketEmitterUpdateFuns = {
                "udpate_server": clientSocketEmitterUpdateFun,
                "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
                "udpate_server_usage": socketioEmitter.udpate_server_usage,
            }

            serverModel.doFleetInfoTask(serversDict, clientSocketEmitterUpdateFuns)
            watched_timestamp = redisModel.getFleetWatchedTimestamp(fleet.id)
            socketioEmitter.fleet_update_timestamps(fleet, watched_timestamp = watched_timestamp)


@huey_app.periodic_task(crontab(minute=f"*/{monitoring_interval_min}"))
@huey_app.lock_task("monitor-lock")
def monitorMonitoredFleets():
    if MONITORING_SYSTEM_AVAILABLE and settingModel.getRefreshValue("monitoring_enabled"):
        fleets = fleetModel.indexMonitored()
        asyncio.run(monitor(fleets))
        for fleet in fleets:
            monitored_timestamp = redisModel.setFleetMonitoredTimestamp(fleet.id)
            if monitored_timestamp is not None:
                socketioEmitter.fleet_update_timestamps(fleet, monitored_timestamp = monitored_timestamp)


def backgroundRefreshSettings():
    """Read on every run, so that changes made in the settings take effect without restarting the workers"""
    return {
        "enabled": settingModel.getRefreshValue("health_background_refresh_enabled"),
        "connection_test_interval": int(settingModel.getValue("health_connection_test_interval")) * 60,
        "full_refresh_interval": int(settingModel.getValue("health_full_refresh_interval")) * 60,
        "max_concurrency": int(settingModel.getValue("health_max_concurrency")),
    }


BACKGROUND_CONNECTION_TEST_TIMEOUT = serverModel.CONNECTION_TEST_TIMEOUT
BACKGROUND_LOCK_TIMEOUT = 60 * 60  # Released by then even if a worker died while holding it


def skipIfRunning(lock_name):
    """Run the task only if the previous run is over. Unlike huey's lock_task, a skipped run is not an error:
    these tasks fire every minute and a full refresh can take longer than that"""
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            token = uuid.uuid4().hex
            if not redisModel.redisClient.set(lock_name, token, nx=True, ex=BACKGROUND_LOCK_TIMEOUT):
                return None
            try:
                return fn(*args, **kwargs)
            finally:
                if redisModel.redisClient.get(lock_name) == token:
                    redisModel.redisClient.delete(lock_name)
        return wrapped
    return decorator


@huey_app.periodic_task(crontab(minute="*"))
@skipIfRunning("background-connection-test-lock")
def backgroundConnectionTest():
    """Connection test of every server whose last test is older than the configured interval. Runs every minute
    so that new servers, restarts and interval changes are picked up quickly; servers not due are skipped"""
    config = backgroundRefreshSettings()
    if not config["enabled"]:
        return
    servers = serverModel.serversDueForConnectionTest(serverModel.index(), config["connection_test_interval"], int(time.time()))
    if len(servers) == 0:
        return
    serverByID = {server.id: server for server in servers}

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult["server"] = serverSchemaWithoutInfo.dump(serverByID[server_id])
        socketioEmitter.udpate_server_connection(serverByID[server_id], testResult)
    serverModel.testAllConnectionAsync(
        servers, clientSocketEmitterUpdateFun,
        max_concurrency=config["max_concurrency"], timeout=BACKGROUND_CONNECTION_TEST_TIMEOUT
    )


@huey_app.periodic_task(crontab(minute="*"))
@skipIfRunning("background-full-refresh-lock")
def backgroundFullRefresh():
    """Full refresh of every server whose snapshot is older than the configured interval. Servers kept fresh by
    fleet watching are therefore skipped. Servers without an API key cannot be queried and are left out"""
    config = backgroundRefreshSettings()
    if not config["enabled"]:
        return
    candidates = [server for server in serverModel.index() if server.authkey]
    servers = serverModel.serversDueForRefresh(candidates, config["full_refresh_interval"], int(time.time()))
    if len(servers) == 0:
        return
    serverByID = {server.id: server for server in servers}

    def clientSocketEmitterUpdateFun(server_id, testResult):
        testResult["server"] = serverSchemaWithoutInfo.dump(serverByID[server_id])
        socketioEmitter.udpate_server(serverByID[server_id], testResult)

    clientSocketEmitterUpdateFuns = {
        "udpate_server": clientSocketEmitterUpdateFun,
        "udpate_server_connection_list": socketioEmitter.udpate_server_connection_list,
        "udpate_server_usage": socketioEmitter.udpate_server_usage,
    }
    serverModel.refreshServersInBackground(servers, clientSocketEmitterUpdateFuns, config["max_concurrency"])


@huey_app.periodic_task(crontab(minute="*"))
@skipIfRunning("metrics-collect-lock")
def collectMetrics():
    """Usage metrics of every server of a monitored fleet whose last collection is older than the configured
    interval. Runs every minute, like the background refresh, so that interval changes apply without a restart"""
    config = metricModel.monitoringSettings()
    if not config["enabled"]:
        return None
    candidates = metricModel.monitoredServers(fleetModel.indexMonitored())
    servers = metricModel.serversDueForCollection(candidates, config["interval"], int(time.time()))
    return len(metricModel.collectAndAnnounce(servers, config["interval"], config["max_concurrency"], socketioEmitter))


@huey_app.periodic_task(crontab(minute="7"))
@skipIfRunning("metrics-rollup-lock")
def rollupMetrics():
    """Hourly and daily roll-ups of the metrics, then retention. Runs even when monitoring is off, so that old
    samples still go away"""
    return metricRollups.run()


@huey_app.periodic_task(crontab(hour="3", minute="17"))
@skipIfRunning("job-purge-lock")
def purgeOldJobs():
    """Jobs are kept for the configured number of days, then deleted with their results"""
    retention_days = int(settingModel.getRefreshValue("job_retention_days"))
    return jobModel.purge(retention_days)


@huey_app.periodic_task(crontab(hour="*/12"))
@huey_app.lock_task("monitor-image-lock")
def cacheMonitoringImages():
    if MONITORING_SYSTEM_AVAILABLE and settingModel.getRefreshValue("monitoring_enabled"):
        fleets = fleetModel.indexMonitored()
        for fleet in fleets:
            asyncio.run(serverModel.doCacheMonitoringImages(fleet.servers))
