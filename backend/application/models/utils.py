#!/usr/bin/env python3

from datetime import datetime, timedelta, timezone
from math import floor
import shutil
from typing import Tuple, Union
from urllib.parse import urlencode
from PIL import Image
from random import randint
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import aiohttp
import asyncio

import nest_asyncio
import requests  # Make the asyncio's event loop re-entrant
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


class MonitoringImages:
    IMAGE_REFRESH_FREQUENCY_MIN = 5
    ROOT_PATH = Path(__file__).resolve().parent / ".." / ".." / "data" / "cached-monitoring-images"
    ROOT_PATH = ROOT_PATH.resolve()
    grafana_base_url = 'http://localhost:3000'
    grafana_dashboard_data = 'render/d-solo/ce6olif96756od'
    grafana_apikey = "glsa_k94PVSfhraGiK5roLyoniHu0xFyvByne_b1604732"

    def __init__(self, server_id, panel: Union[dict, str], from_time: Union[str, None]=None) -> None:
        self.server_id = str(server_id)
        if type(panel) is str:
            self.panel_id = panel
            from application.models.servers import MONITORING_PANEL_BY_ID
            self.panel = MONITORING_PANEL_BY_ID[self.panel_id]
        else:
            self.panel_id = panel['panel_id']
            self.panel = panel
        self.width = panel.get('width', 200)  if type(panel) is dict else 200
        self.height = panel.get('height', 150)  if type(panel) is dict else 150
        from_time = None
        if from_time is not None:
            self.parsed_time = datetime.strptime(from_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            self.parsed_time = datetime.now(timezone.utc) - timedelta(days=self.panel["relative_time_days"])
        self.from_time = self.parsed_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def generateGrafanaURL(self):
        url_params = {
            "timezone": "utc",
            "theme": "light",
            "var-bucket": "MISP-Fleet-Commander",
            "width": self.width,
            "height": self.height,
            "from": self.from_time,
            "to": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "var-instance": "Training Main",
            "panelId": str(self.panel_id),
        }
        return f"{self.grafana_base_url}/{self.grafana_dashboard_data}?" + urlencode(url_params)

    def canonizeTime(self):
        return self.parsed_time.strftime("%Y-%m-%dT%H_%M_%S")

    def shouldReloadImage(self):
        now = self.getExistingImageCreationTime()
        if now is None:
            return True
        one_hour_ago = now - timedelta(minutes=self.IMAGE_REFRESH_FREQUENCY_MIN)
        return one_hour_ago <= self.parsed_time <= now

    def canonizedName(self):
        return f"{self.server_id}_{self.panel_id}"

    def getImageBasePath(self):
        return f"{self.canonizedName()}.png"

    def getFolderBasePath(self):
        return Path(self.ROOT_PATH).resolve()

    def getImageFullPath(self):
        return (Path(self.ROOT_PATH) / self.getImageBasePath()).resolve()

    def cacheImage(self):
        r = requests.get(
            self.generateGrafanaURL(),
            stream=True,
            headers={
                "Authorization": f"Bearer {self.grafana_apikey}",
                "Accept": "image/png",
            },
        )
        path = self.getImageFullPath()
        if r.status_code == 200:
            with open(path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)

    def getExistingImageCreationTime(self):
        try:
            return datetime.fromtimestamp(os.stat(self.getImageFullPath()).st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            return None

    def getImagePaths(self) -> Tuple[str, str]:
        return (str(self.getFolderBasePath()), self.getImageBasePath())

    def refreshImage(self, force=False):
        if self.shouldReloadImage() or force:
            self.cacheImage()

    def deleteImage(self):
        os.unlink(self.getImageFullPath())


async def asyncFetcher(server, urls) -> list[dict]:
    headers = {
        "Authorization": server.authkey,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    async def fetch(session, url, headers) -> dict:
        timer = time.perf_counter()
        try:
            async with session.get(url, headers=headers, ssl=False) as response:
                try:
                    result =  await response.json()
                    if type(result) is dict:
                        result['_latency'] = time.perf_counter() - timer
                        result['_status_code'] = response.status
                except aiohttp.ContentTypeError:
                    result = await response.text()
                    result = {'text': result}
                return result
        except aiohttp.ClientConnectorError as e:
            result = {"error": "Connection Error: " + str(e)}
        except Exception as e:
            result = {"error": "Unhandled Exception: " + str(e)}
        return result

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, urljoin(server.url, url), headers) for url in urls]
        results = await asyncio.gather(*tasks)
        return results


async def asyncFetcherManyServer(servers, url, resultCallback):
    base_headers = {
        "Authorization": '---',
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    async def fetch(session, url, headers, server_id, resultCallback):
        timer = time.perf_counter()
        result = None
        try:
            async with session.get(url, headers=headers, ssl=False) as response:
                try:
                    result = await response.json()
                    if type(result) is dict:
                        result['_latency'] = time.perf_counter() - timer
                        result['_status_code'] = response.status
                except aiohttp.ContentTypeError:
                    result = await response.text()
        except aiohttp.ClientConnectorError as e:
            result = {"error": "Connection Error: " + str(e)}
        except Exception as e:
            result = { "error": "Unhandled Exception: " + str(e) }
        resultCallback(server_id, result)
        return result

    async with aiohttp.ClientSession() as session:
        tasks = []
        for server in servers:
            headers = dict(base_headers)
            headers['Authorization'] = server.authkey
            tasks.append(fetch(session, urljoin(server.url, url), headers, server.id, resultCallback))
        results = await asyncio.gather(*tasks)
        return results
