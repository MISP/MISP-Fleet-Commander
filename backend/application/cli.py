#!/usr/bin/env python3

import time
import click
from pprint import pprint

from flask.cli import AppGroup
from application.marshmallowSchemas import serverSchema, userSchema
import application.models.servers as serverModel
import application.models.fleets as fleetModel
import application.models.users as userModel

server_cli = AppGroup('server')
user_cli = AppGroup('user')


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

def doQueryFleet(fleet_id: int, delay_second: int = 10):
    fleet = fleetModel.get(fleet_id)
    if fleet is not None:
        print(f'Querying all {len(fleet.servers)} servers from fleet {fleet.name} ({fleet.id})')
        for server in fleet.servers:
            print(f'Querying server {server.name} ({server.id})')
            timer1 = time.time()
            serverModel.queryInfo(server.id, False)
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
            fetchServerInfoTask.delay(serverSchema.dump(server))
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