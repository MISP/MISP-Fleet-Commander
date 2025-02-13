import json
import time
from typing import Union
from application import redisClient

KEY_SERVER_INFO = 'server-info'
SERVER_INFO_TTL = 60*60
KEY_SERVER_MONITORED = 'server-monitored'
KEY_SERVER_WATCHED = 'server-watched'
KEY_FLEET_MONITORED = 'fleet-monitored'
KEY_FLEET_WATCHED = 'fleet-watched'
KEY_SERVER_PICTURES_CACHED = "server-pic-cached"


def saveServerInfo(server_uuid: int, info: dict) -> bool:
    infoText = json.dumps(info)
    saved = redisClient.set(f"{KEY_SERVER_INFO}:{server_uuid}", infoText)
    redisClient.expire(f"{KEY_SERVER_INFO}:{server_uuid}", SERVER_INFO_TTL)
    return saved

def getServerInfo(server_uuid: str) -> Union[None, dict]:
    infoText = redisClient.get(f"{KEY_SERVER_INFO}:{server_uuid}")
    if infoText is None:
        return None
    else:
        return json.loads(infoText)

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
