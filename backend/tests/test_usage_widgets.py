"""Widgets of a fleet's Usage tab: the saved queries followed there, their order and display, and what they draw: the
fleet's servers only, and their answers summed."""
import time

import pytest

from test_fleet_queries import FakeResponse, caps, fleet, misp, recorded, supportAnswer  # noqa: F401
from test_saved_queries import COUNT, SELECT, save, watched

HOUR, DAY = 3600, 86400


def record(saved, server, ts, value, more=False):
    from application import db
    from application.models import savedQueryHistory
    savedQueryHistory.record(saved.id, server.id, ts, value, more)
    db.session.commit()


def otherFleet(db, user, names=('misp-x',)):
    from application.DBModels import Fleet, Server
    row = Fleet(name='Other fleet', description='', user_id=user.id, timestamp=1)
    db.session.add(row)
    db.session.commit()
    servers = []
    for name in names:
        server = Server(name=name, url=f'https://{name}.test/', user_id=user.id, fleet_id=row.id)
        server.authkey = f'key-{name}'
        db.session.add(server)
        servers.append(server)
    db.session.commit()
    return row, servers


@pytest.fixture()
def api(client, auth_headers):
    def call(user, method, path, body=None):
        return getattr(client, method)(path, json=body, headers=auth_headers(user))
    return call


def widgetRows(fleetId):
    from application.DBModels import UsageWidget
    return UsageWidget.query.filter_by(fleet_id=fleetId).order_by(UsageWidget.position).all()


# Choosing what to follow

def test_candidates_are_the_numbers_that_run_on_the_fleet(db, fleet, api):
    user, fleetRow, servers = fleet
    elsewhere, outside = otherFleet(db, user)
    onFleet = save(user, name='On the fleet', fleet_id=fleetRow.id, schedule_minutes=15)
    listed = save(user, name='Listed', statement=SELECT, server_ids=[servers[0].id, outside[0].id])
    save(user, name='Described', statement='DESCRIBE events', fleet_id=fleetRow.id)
    save(user, name='Other fleet', fleet_id=elsewhere.id)
    api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': listed.id, 'display': 'servers'})

    answer = api(user, 'get', f'/fleets/{fleetRow.id}/widgets/candidates').json
    assert answer['fleet_servers'] == 3
    assert [(c['id'], c['kind'], c['fleet_servers'], c['server_count'], c['aims_at_fleet'], c['added'])
            for c in answer['saved']] == [
        (listed.id, 'select', 1, 2, False, True),
        (onFleet.id, 'count', 3, 3, True, False),
    ]
    assert answer['saved'][1]['schedule_minutes'] == 15


def test_a_widget_is_added_shown_switched_moved_and_removed(db, fleet, api):
    user, fleetRow, servers = fleet
    first = watched(user, fleetRow, name='First')
    second = save(user, name='Second', statement=SELECT, server_ids=[servers[1].id],
                  expectation={'comparator': 'eq', 'value': 0})
    base = f'/fleets/{fleetRow.id}/widgets'

    added = api(user, 'post', base, {'saved_query_id': first.id})
    assert added.status_code == 201
    assert (added.json['display'], added.json['position'], added.json['problem']) == ('total', 0, None)
    other = api(user, 'post', base, {'saved_query_id': second.id, 'display': 'servers'}).json
    assert other['position'] == 1

    listed = api(user, 'get', base).json
    assert listed['max'] == 20
    assert [(w['saved_query']['name'], w['display']) for w in listed['widgets']] == \
        [('First', 'total'), ('Second', 'servers')]
    shown = listed['widgets'][1]
    assert shown['saved_query'] == {
        'id': second.id, 'name': 'Second', 'kind': 'select', 'schedule_minutes': None,
        'expectation': {'comparator': 'eq', 'value': 0}, 'expectation_text': 'no rows', 'severity': 'warning',
        'server_count': 1,
    }
    assert [(s['server_name'], s['state'], s['result']) for s in shown['servers']] == [('misp-a', 'not_run', None)]
    # The fleet's servers in the saved query's order: by name for a fleet
    assert [s['server_name'] for s in listed['widgets'][0]['servers']] == ['misp-a', 'misp-b', 'misp-c']

    switched = api(user, 'put', f"{base}/{added.json['id']}", {'display': 'servers'})
    assert switched.json['display'] == 'servers'
    assert api(user, 'put', f"{base}/{added.json['id']}", {'display': 'pie'}).json['field'] == 'display'

    moved = api(user, 'put', f'{base}/order', {'ids': [other['id'], added.json['id']]})
    assert [w['id'] for w in moved.json['widgets']] == [other['id'], added.json['id']]
    for ids in ([other['id']], [other['id'], other['id']], [other['id'], added.json['id'], 999], 'all',
                [other['id'], True]):
        refused = api(user, 'put', f'{base}/order', {'ids': ids})
        assert (refused.status_code, refused.json['field']) == (400, 'ids'), ids

    assert api(user, 'delete', f"{base}/{other['id']}").json == {'deleted': other['id']}
    assert [w.saved_query_id for w in widgetRows(fleetRow.id)] == [first.id]
    assert api(user, 'delete', f"{base}/{other['id']}").status_code == 404


def test_what_cannot_be_added(db, fleet, api, make_user):
    user, fleetRow, servers = fleet
    elsewhere, outside = otherFleet(db, user)
    base = f'/fleets/{fleetRow.id}/widgets'
    stranger = make_user(f'stranger-{time.time_ns()}@test.local')
    strangerFleet, _ = otherFleet(db, stranger, names=('misp-s',))
    theirs = save(stranger, statement=COUNT, fleet_id=strangerFleet.id)
    described = save(user, statement='DESCRIBE events', fleet_id=fleetRow.id)
    away = save(user, server_ids=[outside[0].id])
    fine = save(user, fleet_id=fleetRow.id)

    def refused(body, who=user, path=base):
        answer = api(who, 'post', path, body)
        return answer.status_code, answer.json.get('field')

    assert refused({'saved_query_id': 999999}) == (404, 'saved_query_id')
    assert refused({'saved_query_id': 'x'}) == (404, 'saved_query_id')
    assert refused({'saved_query_id': described.id}) == (400, 'saved_query_id')
    assert refused({'saved_query_id': away.id}) == (400, 'saved_query_id')
    assert refused({'saved_query_id': fine.id, 'display': 'pie'}) == (400, 'display')
    # Someone else's fleet, or someone else's saved query, is unknown
    assert refused({'saved_query_id': fine.id}, who=stranger) == (404, None)
    assert refused({'saved_query_id': theirs.id}) == (404, 'saved_query_id')
    assert api(user, 'post', base, {'saved_query_id': fine.id}).status_code == 201
    assert refused({'saved_query_id': fine.id}) == (409, 'saved_query_id')
    assert api(stranger, 'get', base).status_code == 404
    assert api(stranger, 'get', f'{base}/candidates').status_code == 404


def test_a_fleet_holds_at_most_twenty_widgets(db, fleet, api):
    from application.models import usageWidgets
    user, fleetRow, _ = fleet
    for index in range(usageWidgets.MAX_WIDGETS):
        saved = save(user, name=f'Q{index}', fleet_id=fleetRow.id)
        assert api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': saved.id}).status_code == 201
    extra = save(user, name='One too many', fleet_id=fleetRow.id)
    answer = api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': extra.id})
    assert answer.status_code == 400 and 'at most 20' in answer.json['message']


# What a widget draws

def test_the_history_is_the_fleets_servers_and_their_total(db, fleet, api):
    user, fleetRow, servers = fleet
    elsewhere, outside = otherFleet(db, user)
    b, a, c = servers
    saved = save(user, server_ids=[b.id, outside[0].id, a.id, c.id], schedule_minutes=60,
                 expectation={'comparator': 'lte', 'value': 15})
    widget = api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': saved.id}).json
    now = int(time.time())
    hour = now - now % HOUR
    record(saved, a, hour - 8 * DAY, 10)          # Before the week: carried into it
    record(saved, a, hour - 3 * HOUR + 5, 12)
    record(saved, b, hour - 2 * HOUR + 10, 5)
    record(saved, b, hour - 2 * HOUR + 20, 7)     # The hour's last answer
    record(saved, outside[0], hour - HOUR, 1000)  # Not this fleet's

    week = api(user, 'get', f"/fleets/{fleetRow.id}/widgets/{widget['id']}/history").json
    assert week['widget_id'] == widget['id']
    assert (week['range'], week['tier'], week['expectation_text']) == ('7d', 'raw', 'at most 15')
    assert [entry['server_name'] for entry in week['servers']] == ['misp-b', 'misp-a', 'misp-c']
    total = week['total']
    assert (total['tier'], total['interval_s'], total['servers'], total['partial_since']) == ('hour', HOUR, 3, hour)
    start = week['from'] - week['from'] % HOUR
    assert total['points'][0] == [start, 10]
    assert len(total['points']) == (hour - start) // HOUR + 1
    assert total['points'][-4:] == [[hour - 3 * HOUR, 12], [hour - 2 * HOUR, 19], [hour - HOUR, 19], [hour, 19]]
    assert total['reporting'][0] == [start, 1] and total['reporting'][-1] == [hour, 2]
    assert total['capped'] == []

    year = api(user, 'get', f"/fleets/{fleetRow.id}/widgets/{widget['id']}/history?range=1y").json['total']
    today = now - now % DAY
    eightDaysAgo = (hour - 8 * DAY) - (hour - 8 * DAY) % DAY
    assert (year['tier'], year['interval_s']) == ('day', DAY)
    assert year['points'][0] == [eightDaysAgo, 10]
    assert year['points'][-1] == [today, 19] and year['reporting'][-1] == [today, 2]

    assert api(user, 'get', f"/fleets/{fleetRow.id}/widgets/{widget['id']}/history?range=2w").json['field'] == 'range'


def test_a_total_holding_a_capped_select_says_so(db, fleet, api):
    user, fleetRow, servers = fleet
    saved = save(user, statement=SELECT, fleet_id=fleetRow.id, schedule_minutes=60)
    widget = api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': saved.id}).json
    now = int(time.time())
    hour = now - now % HOUR
    record(saved, servers[0], hour - 2 * HOUR + 1, 3)
    record(saved, servers[1], hour - HOUR + 1, 100, more=True)
    total = api(user, 'get', f"/fleets/{fleetRow.id}/widgets/{widget['id']}/history?range=24h").json['total']
    assert total['points'][-3:] == [[hour - 2 * HOUR, 3], [hour - HOUR, 103], [hour, 103]]
    assert total['capped'] == [hour - HOUR, hour]


def test_a_widget_left_without_a_number_says_why(db, fleet, api):
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    elsewhere, outside = otherFleet(db, user)
    saved = save(user, fleet_id=fleetRow.id)
    widget = api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': saved.id}).json
    base = f"/fleets/{fleetRow.id}/widgets"

    savedQueries.update(user, saved.id, {'fleet_id': None, 'server_ids': [outside[0].id]})
    [shown] = api(user, 'get', base).json['widgets']
    assert (shown['problem'], shown['servers']) == ('no_server', [])
    history = api(user, 'get', f"{base}/{widget['id']}/history").json
    assert (history['servers'], history['total']['points'], history['total']['servers']) == ([], [], 0)

    savedQueries.update(user, saved.id, {'statement': 'DESCRIBE events', 'server_ids': [servers[0].id]})
    [shown] = api(user, 'get', base).json['widgets']
    assert shown['problem'] == 'no_number'
    assert api(user, 'get', f"{base}/{widget['id']}/history").status_code == 400


# Going away with what they follow

def test_widgets_go_with_their_saved_query_their_fleet_and_their_owner(db, fleet, api, make_user):
    from application.DBModels import UsageWidget
    from application.models import savedQueries
    user, fleetRow, servers = fleet
    first, second = save(user, fleet_id=fleetRow.id), save(user, fleet_id=fleetRow.id)
    for saved in (first, second):
        api(user, 'post', f'/fleets/{fleetRow.id}/widgets', {'saved_query_id': saved.id})
    savedQueries.delete(user, first.id)
    assert [w.saved_query_id for w in widgetRows(fleetRow.id)] == [second.id]

    fleetId = fleetRow.id
    assert api(user, 'post', f'/fleets/delete/{fleetId}').status_code == 200
    assert widgetRows(fleetId) == []

    owner = make_user(f'owner-{time.time_ns()}@test.local')
    kept, keptServers = otherFleet(db, owner, names=('misp-k',))
    saved = save(owner, fleet_id=kept.id)
    api(owner, 'post', f'/fleets/{kept.id}/widgets', {'saved_query_id': saved.id})
    assert len(widgetRows(kept.id)) == 1
    db.session.delete(owner)
    db.session.commit()
    assert UsageWidget.query.filter_by(fleet_id=kept.id).count() == 0
