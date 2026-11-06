import json
import time
from typing import Union
from application import redisClient

# Snapshots never expire: their freshness is judged by their `timestamp`
KEY_SERVER_INFO = 'server-info'
KEY_SERVER_STATUS = 'server-status'
KEY_SERVER_MONITORED = 'server-monitored'
KEY_SERVER_WATCHED = 'server-watched'
KEY_FLEET_MONITORED = 'fleet-monitored'
KEY_FLEET_WATCHED = 'fleet-watched'
KEY_SERVER_PICTURES_CACHED = "server-pic-cached"


def saveServerInfo(server_uuid: int, info: dict) -> bool:
    infoText = json.dumps(info)
    return redisClient.set(f"{KEY_SERVER_INFO}:{server_uuid}", infoText)

def getServerInfo(server_uuid: str) -> Union[None, dict]:
    infoText = redisClient.get(f"{KEY_SERVER_INFO}:{server_uuid}")
    if infoText is None:
        return None
    else:
        return json.loads(infoText)

# Fields of a connection test (`/servers/getVersion`) worth keeping
SERVER_STATUS_FIELDS = ('version', 'error', 'message', '_latency', '_status_code', 'timestamp')


def saveServerStatus(server_uuid: str, connectionTest) -> Union[dict, None]:
    """Persist the latest connection test of a server, so that it survives restarts and is shared by every client"""
    if isinstance(connectionTest, str):
        connectionTest = {'error': connectionTest[:200] or 'Empty response'}
    if not isinstance(connectionTest, dict):
        return None
    status = {field: connectionTest[field] for field in SERVER_STATUS_FIELDS if field in connectionTest}
    status.setdefault('timestamp', int(time.time()))
    redisClient.set(f"{KEY_SERVER_STATUS}:{server_uuid}", json.dumps(status))
    return status


def getServerStatus(server_uuid: str) -> Union[None, dict]:
    statusText = redisClient.get(f"{KEY_SERVER_STATUS}:{server_uuid}")
    if statusText is None:
        return None
    return json.loads(statusText)


def deleteServerData(server_uuid: str) -> None:
    """Forget everything cached about a server: needed now that snapshots no longer expire"""
    redisClient.delete(*[f"{key}:{server_uuid}" for key in (
        KEY_SERVER_INFO, KEY_SERVER_STATUS, KEY_SERVER_MONITORED, KEY_SERVER_WATCHED, KEY_SERVER_PICTURES_CACHED,
    )])


def getServerMonitoredTimestamp(server_uuid: str) -> Union[int, None]:
    lastMonitoredTS = redisClient.get(f"{KEY_SERVER_MONITORED}:{server_uuid}")
    if lastMonitoredTS is not None:
        return int(lastMonitoredTS)
    return None

def setServerMonitoredTimestamp(server_uuid: str) -> bool:
    now = int(time.time())
    return redisClient.set(f"{KEY_SERVER_MONITORED}:{server_uuid}", now)

def getServerWatchedTimestamp(server_uuid: str) -> Union[int, None]:
    lastMonitoredTS = redisClient.get(f"{KEY_SERVER_WATCHED}:{server_uuid}")
    if lastMonitoredTS is not None:
        return int(lastMonitoredTS)
    return None

def setServerWatchedTimestamp(server_uuid: str) -> bool:
    now = int(time.time())
    return redisClient.set(f"{KEY_SERVER_WATCHED}:{server_uuid}", now)

def getFleetMonitoredTimestamp(fleet_id: int) -> Union[int, None]:
    lastMonitoredTS = redisClient.get(f"{KEY_FLEET_MONITORED}:{fleet_id}")
    if lastMonitoredTS is not None:
        return int(lastMonitoredTS)
    return None

def setFleetMonitoredTimestamp(fleet_id: int) -> Union[int, None]:
    now = int(time.time())
    success = redisClient.set(f"{KEY_FLEET_MONITORED}:{fleet_id}", now)
    if success:
        return now
    return None


def getServerCachedPicturedTimestamp(server_uuid: str) -> Union[int, None]:
    lastMonitoredTS = redisClient.get(f"{KEY_SERVER_PICTURES_CACHED}:{server_uuid}")
    if lastMonitoredTS is not None:
        return int(lastMonitoredTS)
    return None


def setServerCachedPicturedTimestamp(server_uuid: str) -> Union[int, None]:
    now = int(time.time())
    success = redisClient.set(f"{KEY_SERVER_PICTURES_CACHED}:{server_uuid}", now)
    if success:
        return now
    return None


def getFleetWatchedTimestamp(fleet_id: int) -> Union[int, None]:
    lastMonitoredTS = redisClient.get(f"{KEY_FLEET_WATCHED}:{fleet_id}")
    if lastMonitoredTS is not None:
        return int(lastMonitoredTS)
    return None

def setFleetWatchedTimestamp(fleet_id: int) -> Union[int, None]:
    now = int(time.time())
    success = redisClient.set(f"{KEY_FLEET_WATCHED}:{fleet_id}", now)
    if success:
        return now
    return None
