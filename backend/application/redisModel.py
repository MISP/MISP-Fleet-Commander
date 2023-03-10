
import json
from typing import Union
from application import redisClient

KEY_SERVER_INFO = 'server-info'


def saveServerInfo(server_id: int, info: dict) -> bool:
    infoText = json.dumps(info)
    return redisClient.set(f"{KEY_SERVER_INFO}:{server_id}", infoText)

def getServerInfo(server_id: int) -> Union[None, dict]:
    infoText = redisClient.get(f"{KEY_SERVER_INFO}:{server_id}")
    if infoText is None:
        return None
    else:
        return json.loads(infoText)