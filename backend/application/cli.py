#!/usr/bin/env python3


import asyncio
import time
import click

from flask.cli import AppGroup
from application.marshmallowSchemas import serverSchemaLighter, serverSchema, userSchema
from application.controllers.websocket import SocketioEmitter
import application.models.servers as serverModel
import application.models.fleets as fleetModel
import application.models.users as userModel
import application.models.setting as settingModel
from application import redisModel

from application import MONITORING_SYSTEM_AVAILABLE, MONITORING_SYSTEM as monitor

socketioEmitter = SocketioEmitter()


server_cli = AppGroup("server", short_help="Server utility to query servers or fleets.")
user_cli = AppGroup("user", short_help="User utility to reset user password.")
sensors = {}


@server_cli.command('test-connection')
@click.argument('server_id')
def testConnection(server_id):
    result = serverModel.testConnection(server_id)
    pprint(result)


@server_cli.command('query')
@click.argument('server_id')
@click.argument('cache', required=False, default=False)
def getServerInfo(server_id, cache=True):
    result = serverModel.getServerInfo(server_id, cache)
    pprint(result)


@server_cli.command('query-fleet')
@click.argument('fleet_id')
@click.option('--delay_second', required=False, default=10)
def queryFleet(fleet_id: int, delay_second: int):
    doQueryFleet(fleet_id, delay_second)

@server_cli.command('watch-fleet')
@click.argument('fleet_id')
@click.option('--minute', required=False, default=5)
@click.option('--delay_second', required=False, default=10)
def watchFleet(fleet_id: int, minute: int = 5, delay_second: int = 10):
    while True:
        doQueryFleet(fleet_id, delay_second)
        print(f'Sleeping {minute*60}')
        time.sleep(minute*60)

@server_cli.command('monitor-fleets')
@click.option('--minute', required=False, default=5)
@click.option("--cache_images", is_flag=True, default=False)
def monitorFleet(minute: int = 5, cache_images: bool = False):
    if not MONITORING_SYSTEM_AVAILABLE:
        print("The monitoring system is not avaible due to missing libraries.")
    elif not settingModel.getRefreshValue("monitoring_enabled"):
        print('Monitoring is not enabled')
    else:
        while True:
            fleets = fleetModel.indexMonitored()
            print('Starting monitoring fleets:')
            for fleet in fleets:
                print(f'    - {fleet.name} ({fleet.server_count} servers)')
            asyncio.run(monitor(fleets))
            for fleet in fleets:
                monitored_timestamp = redisModel.setFleetMonitoredTimestamp(fleet.id)
                if monitored_timestamp is not None:
                    socketioEmitter.fleet_update_timestamps(fleet.id, monitored_timestamp = monitored_timestamp)

            if cache_images:
                print("Caching images for fleets:")
                for fleet in fleets:
                    print(f"    - {fleet.name} ({fleet.server_count} servers)")
                    asyncio.run(serverModel.doCacheMonitoringImages(fleet.servers, force=True))

            print(f'Sleeping {minute*60}')
            time.sleep(minute*60)

@server_cli.command("cache-monitoring-images")
@click.option("--minute", required=False, default=5)
@click.option("--force", is_flag=True, default=False)
def cacheMonitoringImages(minute: int = 5, force: bool = False):
    while True:
        fleets = fleetModel.indexMonitored()
        print("Starting caching images:")
        for fleet in fleets:
            print(f"- {fleet.name} ({fleet.server_count} servers)")
            asyncio.run(serverModel.doCacheMonitoringImages(fleet.servers, force))

        print(f"Sleeping {minute*60}")
        time.sleep(minute * 60)


def doQueryFleet(fleet_id: int, delay_second: int = 10):
    fleet = fleetModel.get(fleet_id)
    if fleet is not None:
        print(f'Querying all {len(fleet.servers)} servers from fleet {fleet.name} ({fleet.id})')
        for server in fleet.servers:
            print(f'Querying server {server.name} ({server.id})')
            timer1 = time.time()
            serverModel.fetchServerInfo(server.id, False)
            print(f'\t Took {time.time() - timer1:.2f}')
            time.sleep(delay_second)
    else:
        print('No fleet with that ID')

@server_cli.command('watch-fleet-ws')
@click.argument('fleet_id')
@click.option('--minute', required=False, default=5)
@click.option('--delay_second', required=False, default=10)
def watchFleetWs(fleet_id: int, minute: int = 5, delay_second: int = 10):
    while True:
        doQueryFleetWs(fleet_id, delay_second)
        print(f'Sleeping {minute*60}')
        time.sleep(minute*60)

def doQueryFleetWs(fleet_id: int, delay_second: int = 10):
    from application.workers.tasks import fetchServerInfoTask
    fleet = fleetModel.get(fleet_id)
    if fleet is not None:
        print(f'Querying all {len(fleet.servers)} servers from fleet {fleet.name} ({fleet.id})')
        for server in fleet.servers:
            print(f'Querying server {server.name} ({server.id})')
            timer1 = time.time()
            fetchServerInfoTask(serverSchemaLighter.dump(server))
            print(f'\t Took {time.time() - timer1:.2f}')
            time.sleep(delay_second)
    else:
        print('No fleet with that ID')


@user_cli.command('change_pw')
@click.argument('user_email')
@click.argument('password')
def change_pw(user_email: str, password: str):
    user = userModel.getByEmail(user_email)
    user.password = password
    user = userModel.edit(userSchema.dump(user))
    if user is not None:
        print('Password updated')
        return
    print('Could not update password')
