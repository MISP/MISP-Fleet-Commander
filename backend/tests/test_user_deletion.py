"""Deleting a user deletes what they own: their fleets and servers with what is kept about the servers, their pin
lists, saved queries, settings and acknowledgements. Their jobs stay, without user, as the record of what was done.
Another user's things are left alone."""
import time

import pytest


@pytest.fixture()
def owners(db, make_user):
    """An admin, and two users each owning a fleet of two servers and something kept about the first server"""
    from application.DBModels import (Fleet, HealthAck, MetricSample, PinList, PinListEntry, SavedQuery,
                                      SavedQueryResult, SavedQuerySample, Server)
    import application.models.jobs as jobModel
    stamp = time.time_ns()
    admin = make_user(f'root-{stamp}@test.local', is_admin=True)
    world = {'admin': admin}
    for role in ('gone', 'kept'):
        owner = make_user(f'{role}-{stamp}@test.local')
        fleet = Fleet(name=f'{role} fleet', description='', user_id=owner.id, timestamp=1)
        db.session.add(fleet)
        db.session.commit()
        servers = [Server(name=f'{role}-{index}', url=f'https://{role}-{index}-{stamp}.test/', user_id=owner.id,
                          fleet_id=fleet.id) for index in range(2)]
        db.session.add_all(servers)
        db.session.commit()
        first = servers[0].id
        saved = SavedQuery(user_id=owner.id, name='q', statement='SELECT COUNT(*) FROM events WHERE id < 5',
                           fleet_id=fleet.id, created=1, updated=1)
        pinlist = PinList(model='events', uuid=f'{role}-{stamp}', user_id=owner.id,
                          pinlist_entries=[PinListEntry(server_id=first, data={})])
        db.session.add_all([saved, pinlist,
                            MetricSample(server_id=first, tier='raw', ts=1, values={'events': 1}),
                            HealthAck(user_id=owner.id, server_id=first, issue_id='connection:x', issue_first_seen=1,
                                      created=1)])
        db.session.commit()
        db.session.add_all([SavedQueryResult(saved_query_id=saved.id, server_id=first, outcome='count', value=1,
                                             checked_at=1),
                            SavedQuerySample(saved_query_id=saved.id, server_id=first, tier='raw', ts=1, value=1)])
        db.session.commit()
        job = jobModel.create(owner, 'mispql_query', servers, params={'statement': saved.statement}, title='t',
                              fleet=fleet)
        world[role] = {'user': owner.id, 'fleet': fleet.id, 'servers': [s.id for s in servers], 'saved': saved.id,
                       'pinlist': pinlist.id, 'job': job.id}
    return world


def remaining(db, world):
    """How many of the user's rows are left, table by table"""
    from application.DBModels import (Fleet, HealthAck, Job, MetricSample, PinList, PinListEntry, SavedQuery,
                                      SavedQueryResult, SavedQuerySample, Server, User)
    servers = world['servers']
    return {
        'user': User.query.filter_by(id=world['user']).count(),
        'fleet': Fleet.query.filter_by(id=world['fleet']).count(),
        'servers': Server.query.filter(Server.id.in_(servers)).count(),
        'pinlist': PinList.query.filter_by(id=world['pinlist']).count(),
        'pinlist entries': PinListEntry.query.filter_by(pinlist_id=world['pinlist']).count(),
        'saved query': SavedQuery.query.filter_by(id=world['saved']).count(),
        'saved query answers': SavedQueryResult.query.filter(SavedQueryResult.server_id.in_(servers)).count(),
        'saved query history': SavedQuerySample.query.filter(SavedQuerySample.server_id.in_(servers)).count(),
        'metrics': MetricSample.query.filter(MetricSample.server_id.in_(servers)).count(),
        'acknowledgements': HealthAck.query.filter(HealthAck.server_id.in_(servers)).count(),
        'job': Job.query.filter_by(id=world['job']).count(),
    }


def test_deleting_a_user_deletes_what_they_own(db, client, auth_headers, owners):
    from application.DBModels import Job, User
    admin = owners['admin']
    answer = client.post(f"/users/delete/{owners['gone']['user']}", headers=auth_headers(admin))
    assert answer.status_code == 200, answer.get_json()
    assert answer.get_json() == [owners['gone']['user']]
    db.session.expire_all()
    assert remaining(db, owners['gone']) == {
        'user': 0, 'fleet': 0, 'servers': 0, 'pinlist': 0, 'pinlist entries': 0, 'saved query': 0,
        'saved query answers': 0, 'saved query history': 0, 'metrics': 0, 'acknowledgements': 0,
        'job': 1,  # The record of what was done stays
    }
    job = db.session.get(Job, owners['gone']['job'])
    assert job.user_id is None and {result.server_id for result in job.results} == {None}
    # The other user keeps everything
    assert remaining(db, owners['kept']) == {
        'user': 1, 'fleet': 1, 'servers': 2, 'pinlist': 1, 'pinlist entries': 1, 'saved query': 1,
        'saved query answers': 1, 'saved query history': 1, 'metrics': 1, 'acknowledgements': 1, 'job': 1,
    }
    assert db.session.get(User, admin.id) is not None


def test_a_user_who_owns_nothing_is_deleted_too(db, client, auth_headers, make_user):
    from application.DBModels import User
    admin = make_user(f'root-{time.time_ns()}@test.local', is_admin=True)
    empty = make_user(f'empty-{time.time_ns()}@test.local')
    assert client.post(f'/users/delete/{empty.id}', headers=auth_headers(admin)).status_code == 200
    db.session.expire_all()
    assert db.session.get(User, empty.id) is None
