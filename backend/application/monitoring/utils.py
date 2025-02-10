#!/usr/bin/env python

import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class MeasurementFactory:

    def __init__(self, name, default_tags):
        self.name = name
        self.default_tags = default_tags

    def merge_tags(self, tags = {}):
        return self.default_tags | tags

    def create(self, tags, fields, time=None):
        full_tags = self.merge_tags(tags)
        return Measurement(self.name, full_tags, fields, time).toDict()


class Measurement:

    def __init__(self, name, tags, fields, time=None):
        self.name = name
        self.tags = tags
        self.fields = fields
        self.time = time

    def toDict(self):
        point = {
            'measurement': self.name,
            'tags': self.tags,
            'fields': self.fields,
        }
        if self.time is not None:
            point['time'] = self.time
        return point


class SensorBase:
    measurement_name = 'override-me'
    default_tags = {}
    def __init__(self):
        self.client_session = HTTPClient()
        self.measurement_factory = MeasurementFactory(self.measurement_name, self.default_tags)

    async def close_connection(self):
        await self.client_session.close_connection()

    def query(self, url, data=None, headers=None, ssl=True):
        return self.client_session.query(url, data=data, headers=headers, ssl=ssl)


class HTTPClient:

    def __init__(self):
        # For TCP connection to close and do the cleanup. asyncio internal need to change (see aiohttp/issues/1925)
        connector = aiohttp.TCPConnector(force_close=True, enable_cleanup_closed=True)
        self.client_session = aiohttp.ClientSession(connector=connector)

    async def close_connection(self):
        await self.client_session.close()

    def query(self, url, data=None, headers=None, ssl=True):
        if data is not None:
            return self.client_session.post(url, json=data, headers=headers, ssl=ssl)
        else:
            return self.client_session.get(url, headers=headers, ssl=ssl)
