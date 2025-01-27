#!/usr/bin/env python

import asyncio
from collections import defaultdict
from application.monitoring.config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

from influxdb_client import InfluxDBClient, WriteOptions
# from influxdb_client.client.influxdb_client_async import InfluxDBClient
# import influxdb_client, os, time
# from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from application.monitoring.utils import logger
from application.monitoring.misp import MISP


async def main():
    sensors = getSensorsFromMISPFleetCommander()
    await monitor(sensors)


async def monitor(fleets=[]):
    try:
        influxReady = pingInfluxDB()
        if not influxReady:
            return

        all_sensors = {}
        for fleet in fleets:
            all_sensors[fleet.name] = []
            for server in fleet.servers:
                all_sensors[fleet.name].append(
                    MISP(
                        **{
                            "name": server.name,
                            "url": server.url,
                            "authkey": server.authkey,
                            "skip_ssl": server.skip_ssl,
                        }
                    )
                )

        # Collect all coroutines for all sensors then execute them all
        logger.info('Collecting all coroutines')
        taskAmount = 0
        all_coroutines = defaultdict(lambda: defaultdict(list))
        async with asyncio.TaskGroup() as tg:
            for fleet_name, sensors in all_sensors.items():
                for sensor in sensors:
                    measurements_coroutines = sensor.get_measurements_coroutines()
                    for measurements_coroutine in measurements_coroutines:
                        task = tg.create_task(measurements_coroutine)
                        all_coroutines[fleet_name][sensor.name].append(task)
                        taskAmount += 1
        print(f"Collected {taskAmount} tasks")

        # Process the result of all coroutines
        logger.info('Processing all coroutines results')
        measurements_to_write = []
        for fleet_name, sensors in all_sensors.items():
            print(f"Processing fleet: {fleet_name}")
            for sensor in sensors:
                task_results = all_coroutines[fleet_name][sensor.name]
                measurement_results = []
                print(f"    - Processing server: {sensor.name}. Tasks: {len(task_results)}")
                for task_result in task_results:
                    try:
                        measurement_results.append(await task_result.result().json())
                    except Exception as e:
                        logger.warning('Error while performing query: ' + str(e))
                measurements = sensor.process_measurements(measurement_results)
                measurements_to_write.extend(measurements)
        print(f"{len(measurements_to_write)} measurements to write")

    finally:
        await closeSensorsConnection(all_sensors)

    with InfluxDBClient(
        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
    ) as write_client:
        write_api = write_client.write_api(write_options=SYNCHRONOUS)
        logger.info('Writing new points to InfluxDB')
        successfully = write_api.write(
            bucket=INFLUXDB_BUCKET, record=measurements_to_write
        )
        logger.info(f" > successfully: {successfully}")


def pingInfluxDB() -> bool:
    with InfluxDBClient(
        url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG
    ) as write_client:
        ready = write_client.ping()
        if not ready:
            logger.error(f"InfluxDB is not replying to ping")
        return ready


def getSensorsFromMISPFleetCommander() -> dict:
    return {}


async def closeSensorsConnection(all_sensors):
    for _, sensors in all_sensors.items():
        for sensor in sensors:
            await sensor.close_connection()


if __name__ == '__main__':
    asyncio.run(main())
