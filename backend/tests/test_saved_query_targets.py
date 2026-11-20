"""Where a saved query runs: fleets it follows (their servers when a run starts) and servers listed on their own, each
server once; what is refused; what deleting a fleet leaves; health, Prometheus and the migration from one fleet."""
import json
import time

import pytest

from test_fleet_queries import FakeResponse, caps, fleet, misp, recorded, supportAnswer  # noqa: F401
from test_saved_queries import COUNT, save


def addFleet(db, user, name, serverNames):
    from application.DBModels import Fleet, Server
    row = Fleet(name=name, description='', user_id=user.id, timestamp=1)
    db.session.add(row)
    db.session.commit()
    servers = []
    for serverName in serverNames:
        server = Server(name=serverName, url=f'https://{serverName}.test/', user_id=user.id, fleet_id=row.id)
        server.authkey = f'key-{serverName}'
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    return row, servers


def names(servers):
    return [server.name for server in servers]


def test_fleets_followed_and_servers_listed_run_together_each_server_once(db, client, auth_headers, fleet):
    from application.models import savedQueries
    user, fleetRow, servers = fleet  # misp-b, misp-a, misp-c
    lab, (labOne, labTwo) = addFleet(db, user, 'Lab', ['lab-2', 'lab-1'])
    answer = client.post('/queries/saved', headers=auth_headers(user), json={
        'name': 'Mixed', 'statement': COUNT, 'fleet_ids': [fleetRow.id], 'server_ids': [labOne.id, servers[0].id]})
    assert answer.status_code == 201, answer.json
    body = answer.json
    assert (body['fleet_ids'], body['fleets'], body['server_ids']) == \
        ([fleetRow.id], [{'id': fleetRow.id, 'name': 'Query fleet'}], [labOne.id, servers[0].id])
    # misp-b is in the fleet: once
    assert (body['server_count'], body['other_server_count']) == (4, 1)
    saved = savedQueries.ownedSaved(user, body['id'])
    assert names(savedQueries.targetServers(saved)) == ['misp-a', 'misp-b', 'misp-c', 'lab-2']

    # Two fleets, in the order given, each by name
    savedQueries.update(user, saved.id, {'fleet_ids': [lab.id, fleetRow.id]})
    assert names(savedQueries.targetServers(saved)) == ['lab-1', 'lab-2', 'misp-a', 'misp-b', 'misp-c']
    assert savedQueries.serialize(saved)['other_server_count'] == 0

    # A server added to a followed fleet runs it from then on
    addFleet(db, user, 'Other', [])
    from application.DBModels import Server
    newcomer = Server(name='lab-0', url='https://lab-0.test/', user_id=user.id, fleet_id=lab.id)
    newcomer.authkey = 'key-lab-0'
    db.session.add(newcomer)
    db.session.commit()
    assert names(savedQueries.targetServers(saved))[:3] == ['lab-0', 'lab-1', 'lab-2']


def test_one_fleet_as_clients_built_before_fleet_lists_send_it(db, client, auth_headers, fleet):
    user, fleetRow, _ = fleet
    answer = client.post('/queries/saved', headers=auth_headers(user), json={
        'name': 'Old client', 'statement': COUNT, 'fleet_id': fleetRow.id})
    assert answer.status_code == 201, answer.json
    assert (answer.json['fleet_ids'], answer.json['server_ids'], answer.json['server_count']) == ([fleetRow.id], [], 3)
    assert 'fleet_id' not in answer.json and 'fleet_name' not in answer.json


def test_what_a_target_cannot_be(db, client, auth_headers, fleet, make_user):
    user, fleetRow, servers = fleet
    stranger = make_user(f'stranger-{time.time_ns()}@test.local')
    theirs, theirServers = addFleet(db, stranger, 'Theirs', ['their-misp'])

    def refused(**target):
        answer = client.post('/queries/saved', headers=auth_headers(user),
                             json=dict({'name': f'Q {time.time_ns()}', 'statement': COUNT}, **target))
        return answer.status_code, answer.json.get('field')

    assert refused() == (400, 'target')
    assert refused(fleet_ids=[], server_ids=[]) == (400, 'target')
    assert refused(fleet_ids=[], server_ids=None) == (400, 'target')
    assert refused(fleet_ids=fleetRow.id) == (400, 'target')
    assert refused(fleet_ids=[True]) == (400, 'target')
    assert refused(fleet_ids=[fleetRow.id], fleet_id=fleetRow.id) == (400, 'target')
    assert refused(fleet_ids=[theirs.id]) == (404, 'target')
    assert refused(fleet_ids=[999999]) == (404, 'target')
    assert refused(server_ids=[theirServers[0].id]) == (404, 'target')
    assert refused(server_ids='all') == (400, 'target')
    # The same fleet twice is followed once
    answer = client.post('/queries/saved', headers=auth_headers(user), json={
        'name': 'Twice', 'statement': COUNT, 'fleet_ids': [fleetRow.id, fleetRow.id]})
    assert answer.json['fleet_ids'] == [fleetRow.id]


def test_a_deleted_fleet_leaves_the_saved_queries_following_it(db, client, auth_headers, fleet):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    lab, labServers = addFleet(db, user, 'Lab', ['lab-1'])
    gone, goneServers = addFleet(db, user, 'Gone', ['gone-1'])
    both = save(user, name='Both', fleet_ids=[gone.id, lab.id])
    withServer = save(user, name='With a server', fleet_ids=[gone.id], server_ids=[servers[0].id])
    alone = save(user, name='Alone', fleet_ids=[gone.id])
    untouched = save(user, name='Untouched', fleet_ids=[lab.id])
    goneId = gone.id
    assert client.post(f'/fleets/delete/{goneId}', headers=auth_headers(user)).status_code == 200
    for row in (both, withServer, alone, untouched):
        db.session.refresh(row)
    assert (both.fleet_ids, withServer.fleet_ids, alone.fleet_ids, untouched.fleet_ids) == ([lab.id], [], [], [lab.id])
    assert names(savedQueries.targetServers(both)) == ['lab-1']
    assert names(savedQueries.targetServers(withServer)) == ['misp-b']
    # Left with nothing to run on: D44's state, said the same way
    assert savedQueries.targetServers(alone) == []
    assert savedQueries.serialize(alone)['last_error'] == 'Its fleet was deleted: choose where it runs'
    with pytest.raises(savedQueries.SavedQueryError) as refused:
        savedQueries.runNow(user, alone.id)
    assert refused.value.status == 409


@pytest.mark.parametrize('fleets, listed, message', [
    (1, 0, 'Its fleet has no servers'),
    (2, 0, 'Its fleets have no servers'),
    (0, 1, 'None of its servers exist anymore'),
    (1, 1, 'Its fleet has no servers, and none of its other servers exist anymore'),
])
def test_why_it_has_no_server_to_run_on(db, fleet, fleets, listed, message):
    from application.DBModels import SavedQuery
    from application.models import savedQueries
    user, _, _ = fleet
    empties = [addFleet(db, user, f'Empty {index}', [])[0].id for index in range(fleets)]
    saved = SavedQuery(user_id=user.id, name=f'Q {time.time_ns()}', statement=COUNT, fleet_ids=empties,
                       server_ids=[999999] if listed else [], created=1, updated=1)
    db.session.add(saved)
    db.session.commit()
    assert savedQueries.targetServers(saved) == []
    assert savedQueries.noServersMessage(saved) == message


def test_health_and_prometheus_read_the_whole_target(db, fleet):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    lab, (labOne, labTwo) = addFleet(db, user, 'Lab', ['lab-1', 'lab-2'])
    saved = save(user, fleet_ids=[fleetRow.id], server_ids=[labOne.id], schedule_minutes=60,
                 expectation={'comparator': 'eq', 'value': 0})
    check = {'fleet_ids': saved.fleet_ids, 'server_ids': saved.server_ids}
    assert all(savedQueries.aims(check, server) for server in servers)
    assert savedQueries.aims(check, labOne) and not savedQueries.aims(check, labTwo)
    from application.DBModels import SavedQueryResult
    for server in servers + [labOne, labTwo]:
        db.session.add(SavedQueryResult(saved_query_id=saved.id, server_id=server.id, outcome='count', value=1,
                                        checked_at=1))
    db.session.commit()
    from application.models import prometheus
    answered = [server.name for (row, _, server, _, _) in prometheus.savedQueryAnswers(user) if row.id == saved.id]
    assert sorted(answered) == ['lab-1', 'misp-a', 'misp-b', 'misp-c']


def test_the_migration_turns_one_fleet_into_a_list_and_back(flask_cli):
    run = flask_cli.python
    flask_cli.upgrade('f2c8d1a4b6e9')
    sql = """
import os, sqlite3
c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI'])
c.execute("insert into fleets (id, name, description, user_id, timestamp) values (1, 'A', '', 1, 1), (2, 'B', '', 1, 1)")
for id, name, fleet in ((11, 'a1', 1), (12, 'a2', 1), (21, 'b1', 2)):
    c.execute("insert into servers (id, name, uuid, comment, url, skip_ssl, user_id, fleet_id) values (?, ?, ?, '', ?, 0, 1, ?)",
              (id, name, f'uuid-{id}', f'https://{name}.test', fleet))
c.execute("insert into saved_queries (id, user_id, name, statement, fleet_id, server_ids, created, updated) values "
          "(1, 1, 'fleet', 'S', 1, null, 1, 1), (2, 1, 'list', 'S', null, '[21]', 1, 1)")
c.commit()
"""
    assert run(sql).returncode == 0, run(sql).stderr
    flask_cli.upgrade()
    read = ("import os, sqlite3, json; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
            "print(json.dumps(c.execute('select id, fleet_ids, server_ids from saved_queries order by id').fetchall()))")
    assert json.loads(run(read).stdout) == [[1, '[1]', None], [2, None, '[21]']]
    # A list of fleets and servers: the downgrade keeps the servers it runs on now
    mixed = ("import os, sqlite3; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
             "c.execute(\"insert into saved_queries (id, user_id, name, statement, fleet_ids, server_ids, created, updated)"
             " values (3, 1, 'mixed', 'S', '[1]', '[21, 11]', 1, 1)\"); c.commit()")
    assert run(mixed).returncode == 0
    downgraded = flask_cli.run('db', 'downgrade', 'f2c8d1a4b6e9')
    assert downgraded.returncode == 0, downgraded.stderr
    read = ("import os, sqlite3, json; c = sqlite3.connect(os.environ['SQLALCHEMY_DATABASE_URI']);"
            "print(json.dumps(c.execute('select id, fleet_id, server_ids from saved_queries order by id').fetchall()))")
    assert json.loads(run(read).stdout) == [[1, 1, None], [2, None, '[21]'], [3, None, '[11, 12, 21]']]
