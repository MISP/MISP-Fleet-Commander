#!/usr/bin/env python3

import time
import click
from pprint import pprint

from flask.cli import AppGroup
import application.models.servers as serverModel
import application.models.serverGroups as serverGroupModel

server_cli = AppGroup('server')


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


@server_cli.command('query-group')
@click.argument('group_id')
@click.option('--delay_second', required=False, default=10)
def queryGroup(group_id: int, delay_second: int):
    doQueryGroup(group_id, delay_second)

@server_cli.command('watch-group')
@click.argument('group_id')
@click.option('--minute', required=False, default=5)
@click.option('--delay_second', required=False, default=10)
def watchGroup(group_id: int, minute: int = 5, delay_second: int = 10):
    while True:
        doQueryGroup(group_id, delay_second)
        print(f'Sleeping {minute*60}')
        time.sleep(minute*60)

def doQueryGroup(group_id: int, delay_second: int = 10):
    server_group = serverGroupModel.get(group_id)
    if server_group is not None:
        print(f'Querying all {len(server_group.servers)} servers from group {server_group.name} ({server_group.id})')
        for server in server_group.servers:
            print(f'Querying server {server.name} ({server.id})')
            timer1 = time.time()
            serverModel.queryInfo(server.id, False)
            time.sleep(delay_second)
            print(f'\t Took {time.time() - timer1:.2f}')
    else:
        print('No server group with that ID')