#!/usr/bin/env python3


import asyncio
import time
from pprint import pprint
import click

from flask.cli import AppGroup
from application.marshmallowSchemas import serverSchema, userSchema
from application.controllers.websocket import SocketioEmitter
import application.models.servers as serverModel
import application.models.fleets as fleetModel
import application.models.users as userModel
import application.models.setting as settingModel
import application.models.metrics as metricModel

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
def monitorFleet():
    """Collect the metrics of every server of the monitored fleets once, whether they are due or not"""
    if not settingModel.getRefreshValue("monitoring_enabled"):
        print('Note: monitoring is not enabled in the settings, the workers do not collect metrics on their own')
    fleets = fleetModel.indexMonitored()
    servers = metricModel.monitoredServers(fleets)
    print(f'Collecting the metrics of {len(servers)} servers from {len(fleets)} monitored fleets:')

    def report(server, state):
        outcome = 'stored' if state.last_success == state.last_attempt else 'nothing stored'
        print(f'    - {server.name} ({server.id}): {outcome}' + (f'. {state.last_error}' if state.last_error else ''))
    metricModel.collectAndAnnounce(servers, int(settingModel.getValue("monitoring_interval")) * 60,
                                   int(settingModel.getValue("health_max_concurrency")), socketioEmitter,
                                   onCollected=report)

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
            fetchServerInfoTask(server.id)
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


security_cli = AppGroup("security", short_help="Encryption key utilities.")


@security_cli.command('generate-key')
def generateKey():
    """Print a new encryption key"""
    from application import crypto
    print(crypto.generateKey())


@security_cli.command('rotate-key')
def rotateKey():
    """Re-encrypt the stored MISP authkeys and job parameters with the first configured key.

    \b
    1. Generate a key with `flask security generate-key`
    2. Configure the new key first, followed by the current one: MFC_ENCRYPTION_KEY="NEW,CURRENT"
       (or one key per line in the key file)
    3. Run this command, then keep only the new key
    """
    from application import crypto, db
    from application.DBModels import Job, Server
    servers = Server.query.filter(Server.authkey_enc.isnot(None)).all()
    for server in servers:
        server.authkey_enc = crypto.rotate(server.authkey_enc)
    jobs = Job.query.filter(Job.params_enc.isnot(None)).all()
    for job in jobs:
        job.params_enc = crypto.rotate(job.params_enc)
    db.session.commit()
    print(f'Re-encrypted the authkeys of {len(servers)} servers and the parameters of {len(jobs)} jobs with the first configured key')
