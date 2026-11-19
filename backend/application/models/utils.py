#!/usr/bin/env python3

from math import floor
from PIL import Image
from random import randint
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import aiohttp
import asyncio

import nest_asyncio  # Make the asyncio's event loop re-entrant
nest_asyncio.apply()


class AvatarGenerator:

    PAD = 10
    BLOCK_SIZE = 30
    totalArea = 2*PAD + 5*BLOCK_SIZE
    WHITE = (255, 255, 255,)
    ROOT_PATH = Path(os.path.dirname(__file__)) / '..' / '..' / 'data' / 'pin-avatars'

    def __init__(self, uuid=None) -> None:
        self.uuid = uuid
        self.img = Image.new('RGB', [self.totalArea, self.totalArea], 255)
        self.data = self.img.load()
        self.workingXArea = range(self.PAD, self.img.size[0]-self.PAD)
        self.workingYArea = range(self.PAD, self.img.size[1]-self.PAD)
        filename = (uuid + '.png') if uuid is not None else (str(int(time.time())) + '.png')
        self.path = str(self.ROOT_PATH / filename)

        try:
            os.mkdir(self.ROOT_PATH)
        except (FileExistsError, FileNotFoundError) as e:
            pass

    def generate(self) -> None:
        pattern = self.__genPattern()
        color = self.__genColor()

        for x in range(self.img.size[0]):
            for y in range(self.img.size[1]):
                if x not in self.workingXArea or y not in self.workingYArea:
                    self.data[x,y] = self.WHITE
                else:
                    patternY =  floor((y-self.PAD) / self.BLOCK_SIZE)
                    patternX =  floor((x-self.PAD) / self.BLOCK_SIZE)
                    if pattern[patternX][patternY] == 0:
                        self.data[x,y] = self.WHITE
                    else:
                        self.data[x,y] = color

        self.img.save(self.path)

    def delete(self) -> None:
        if os.path.isfile(self.path):
            os.remove(self.path)

    def getPath(self) -> str:
        return self.path

    def __genPattern(self):
        pattern = []
        if self.uuid is None:
            pattern = [
                [randint(0, 1), randint(0, 1), randint(0, 1)],
                [randint(0, 1), randint(0, 1), randint(0, 1)],
                [randint(0, 1), randint(0, 1), randint(0, 1)],
                [randint(0, 1), randint(0, 1), randint(0, 1)],
                [randint(0, 1), randint(0, 1), randint(0, 1)],
            ]
        else:
            uuidPortion = ''.join(self.uuid.split('-')[3:5])[:-1]
            seed = [0 if int(c, 16) <= 7 else 1 for c in uuidPortion]
            pattern = [
                [seed[0], seed[1], seed[2]],
                [seed[3], seed[4], seed[5]],
                [seed[6], seed[7], seed[8]],
                [seed[9], seed[10], seed[11]],
                [seed[12], seed[13], seed[14]],
            ]
        pattern = self.mirrorPattern(pattern)
        return pattern

    @classmethod
    def mirrorPattern(cls, pattern):
        fullPattern = pattern
        for x, l in enumerate(pattern):
            for v in l[::-1][1:]:  # [::-1][1:] Flip then remove first one
                fullPattern[x].append(v)
        tranposed = [[fullPattern[j][i] for j in range(len(fullPattern))] for i in range(len(fullPattern[0]))]
        return tranposed
    
    def __genColor(self):
        if self.uuid is None:
            colorR = randint(0, 255)
            colorG = randint(0, 255)
            colorB = randint(0, 255)
        else:
            uuidPortion = self.uuid[0:6]
            colorR = int(uuidPortion[0:2], 16)
            colorG = int(uuidPortion[2:4], 16)
            colorB = int(uuidPortion[4:6], 16)
        return (colorR, colorG, colorB,)


def defaultMispTimeout() -> int:
    """Seconds a request may take in total when its caller sets no limit: the configured `misp_request_timeout`
    plus the time to connect, like synchronous requests. Without it, a server that drops packets held a worker for
    5 minutes per request"""
    from application.controllers.utils import MISP_CONNECT_TIMEOUT, mispReadTimeout
    return MISP_CONNECT_TIMEOUT + mispReadTimeout()


async def asyncFetcher(server, urls, timeout=None) -> list[dict]:
    timeout = defaultMispTimeout() if timeout is None else timeout
    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async def fetch(session, url, skip_ssl, headers, timeout_sec) -> dict:
        timer = time.perf_counter()
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        try:
            async with session.get(
                url, headers=headers, ssl=not skip_ssl, timeout=timeout
            ) as response:
                try:
                    result = await response.json()
                    if type(result) is dict:
                        result["_latency"] = time.perf_counter() - timer
                        result["_status_code"] = response.status
                except aiohttp.ContentTypeError:
                    result = await response.text()
                    result = {"text": result}
                return result
        except aiohttp.ClientConnectorError as e:
            result = {"error": "Connection Error: " + str(e)}
        except asyncio.TimeoutError as e:
            result = {"error": f"Timeout Exception ({timeout_sec}s)"}
        except Exception as e:
            result = {"error": f"Unhandled Exception: `{str(type(e))}` {str(e)}"}
        return result

    # For TCP connection to close and do the cleanup. asyncio internal need to change (see aiohttp/issues/1925)
    connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, urljoin(server.url, url), server.skip_ssl, headers, timeout) for url in urls]
        results = await asyncio.gather(*tasks)
        return results


async def asyncFetcherManyServer(servers, url, resultCallback, timeout=None, max_concurrency=None):
    timeout = defaultMispTimeout() if timeout is None else timeout
    base_headers = {
        "Authorization": '---',
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    async def fetch(session, url, headers, server_id, skip_ssl, timeout_sec, resultCallback):
        timer = time.perf_counter()
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        result = None
        try:
            async with session.get(url, headers=headers, ssl=not skip_ssl, timeout=timeout) as response:
                try:
                    result = await response.json()
                    if type(result) is dict:
                        result['_latency'] = time.perf_counter() - timer
                        result['_status_code'] = response.status
                except aiohttp.ContentTypeError:
                    result = await response.text()
        except aiohttp.ClientConnectorError as e:
            result = {"error": "Connection Error: " + str(e)}
        except (aiohttp.ServerTimeoutError, asyncio.TimeoutError):
            result = {"error": f"Timeout Exception ({timeout_sec}s)"}
        except Exception as e:
            result = { "error": f"Unhandled Exception: `{type(e)}` {str(e)}" }
        resultCallback(server_id, result)
        return result

    semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None

    async def limitedFetch(*args):
        if semaphore is None:
            return await fetch(*args)
        async with semaphore:
            return await fetch(*args)

    # For TCP connection to close and do the cleanup. asyncio internal need to change (see aiohttp/issues/1925)
    connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for server in servers:
            headers = dict(base_headers)
            headers['Authorization'] = server.authkey
            tasks.append(limitedFetch(session, urljoin(server.url, url), headers, server.id, server.skip_ssl, timeout, resultCallback))
        results = await asyncio.gather(*tasks)
        return results
