
import json
from typing import Union
from application import redisClient

KEY_SERVER_INFO = 'server-info'
SERVER_INFO_TTL = 60*60


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