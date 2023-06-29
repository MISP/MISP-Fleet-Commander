
import json
from typing import Union
from application import redisClient

KEY_SERVER_INFO = 'server-info'


def saveServerInfo(server_uuid: int, info: dict) -> bool:
    infoText = json.dumps(info)
    return redisClient.set(f"{KEY_SERVER_INFO}:{server_uuid}", infoText)

def getServerInfo(server_uuid: str) -> Union[None, dict]:
    infoText = redisClient.get(f"{KEY_SERVER_INFO}:{server_uuid}")
    if infoText is None:
        return None
    else:
        return json.loads(infoText)