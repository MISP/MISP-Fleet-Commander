"""Whether a server runs complex queries: told by its answer to `GET /attributes/queryDescribe`, cached for the UI,
forgotten on refresh, edit and delete"""
import json
from pathlib import Path

import pytest
import requests

ANSWERS = json.loads((Path(__file__).parent / 'fixtures' / 'misp_support_check.json').read_text())
ROLE_WITHOUT = {'id': '3', 'name': 'User', 'perm_site_admin': False, 'perm_complex_query': False}


def body(name):
    return json.dumps(ANSWERS[name]['body']).encode()


class FakeResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


@pytest.mark.parametrize('status, answer, role, state', [
    (200, body('supported'), None, 'supported'),
    (404, body('not_supported'), None, 'not_supported'),
    (403, body('no_permission'), ROLE_WITHOUT, 'no_permission'),
    (403, body('no_permission'), {**ROLE_WITHOUT, 'perm_complex_query': '0', 'perm_site_admin': '0'}, 'no_permission'),
    # The role says nothing (older MISP, stale schema cache), or says it may: a 403 is then not explained
    (403, body('no_permission'), {'id': '3', 'name': 'User', 'perm_site_admin': False}, 'unavailable'),
    (403, body('no_permission'), {**ROLE_WITHOUT, 'perm_complex_query': True}, 'unavailable'),
    (403, body('no_permission'), {**ROLE_WITHOUT, 'perm_site_admin': True}, 'unavailable'),
    (403, body('no_permission'), None, 'unavailable'),
    (500, b'<pre class="cake-error">Warning</pre>', None, 'unknown'),
    (200, b'{"tables": {}}', None, 'unknown'),
    (200, b'<html>Login</html>', None, 'unknown'),
])
def test_classify(app, status, answer, role, state):
    from application.models import queryCapability
    found = queryCapability.classify(status, answer, role)
    assert (found['state'], found['status']) == (state, status)
    assert (found['detail'] == '') == (state == 'supported')


def test_the_role_alone_never_makes_a_server_supported(app):
    from application.models import queryCapability
    role = {**ROLE_WITHOUT, 'perm_complex_query': True, 'perm_site_admin': True}
    assert queryCapability.classify(404, body('not_supported'), role)['state'] == 'not_supported'


@pytest.fixture()
def owned(db, make_user):
    from application import redisModel
    from application.DBModels import Fleet, Server
    alice = make_user('capability-alice@test.local')
    bob = make_user('capability-bob@test.local')
    fleet = Fleet(name='Capability', description='', user_id=alice.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name='hub', url='https://hub.test', authkey='k' * 40, fleet_id=fleet.id, user_id=alice.id)
    db.session.add(server)
    db.session.commit()
    yield alice, bob, server
    redisModel.deleteServerData(server.uuid, server.id)
    db.session.delete(server)
    db.session.commit()
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch):
    """Fake MISP: `answer` is (status, body) or an error dict; `requests` keeps (method, url, data)"""
    import application.models.queryCapability as queryCapability
    state = {'answer': (200, body('supported')), 'requests': []}

    def fakeRequest(server, method, url, data=None, timeout=None, max_bytes=None):
        state['requests'].append((method, url, data))
        answer = state['answer']
        return answer if isinstance(answer, dict) else FakeResponse(*answer)
    monkeypatch.setattr(queryCapability, 'mispRawRequest', fakeRequest)
    return state


def test_check_asks_the_server_with_no_body_and_keeps_the_answer(owned, misp):
    from application import redisModel
    from application.models import queryCapability
    _, _, server = owned
    found = queryCapability.check(server)
    assert found['state'] == 'supported'
    assert misp['requests'] == [('GET', '/attributes/queryDescribe', None)]
    key = f'query-capability:{server.id}'
    assert json.loads(redisModel.redisClient.get(key))['state'] == 'supported'
    assert 3500 < redisModel.redisClient.ttl(key) <= 3600


def test_a_403_is_explained_by_the_snapshot_role(owned, misp):
    from application import redisModel
    from application.models import queryCapability
    _, _, server = owned
    misp['answer'] = (403, body('no_permission'))
    assert queryCapability.check(server)['state'] == 'unavailable'
    redisModel.saveServerInfo(server.uuid, {'timestamp': 1, 'query_result': {'serverUser': {
        'User': {'id': '4'}, 'Role': ROLE_WITHOUT}}})
    assert queryCapability.check(server)['state'] == 'no_permission'


@pytest.mark.parametrize('answer, state', [({'error': 'Server unreachable'}, 'unreachable'),
                                           ((502, b''), 'unknown')])
def test_an_unclear_answer_is_asked_again_soon(owned, misp, answer, state):
    from application import redisModel
    from application.models import queryCapability
    _, _, server = owned
    misp['answer'] = answer
    found = queryCapability.check(server)
    assert found['state'] == state
    assert 0 < redisModel.redisClient.ttl(f'query-capability:{server.id}') <= 60
    if state == 'unreachable':
        assert (found['status'], found['detail']) == (None, 'Server unreachable')


def test_get_reads_the_cache_until_refresh(owned, misp):
    from application.models import queryCapability
    _, _, server = owned
    assert queryCapability.get(server)['state'] == 'supported'
    misp['answer'] = (404, body('not_supported'))
    cached = queryCapability.get(server)
    assert (cached['state'], cached['cached']) == ('supported', True)
    assert queryCapability.get(server, refresh=True)['state'] == 'not_supported'
    assert len(misp['requests']) == 2


def test_route_is_owner_scoped(client, auth_headers, owned, misp):
    alice, bob, server = owned
    response = client.get(f'/servers/queryCapability/{server.id}', headers=auth_headers(alice))
    assert response.status_code == 200
    assert response.get_json()['state'] == 'supported'
    misp['answer'] = (404, body('not_supported'))
    assert client.get(f'/servers/queryCapability/{server.id}', headers=auth_headers(alice)).get_json()['cached']
    refreshed = client.get(f'/servers/queryCapability/{server.id}?refresh=1', headers=auth_headers(alice))
    assert refreshed.get_json()['state'] == 'not_supported'
    assert client.get(f'/servers/queryCapability/{server.id}', headers=auth_headers(bob)).status_code == 404
    assert len(misp['requests']) == 2


def test_refresh_edit_and_delete_forget_it(client, auth_headers, owned, misp):
    from application import redisModel
    from application.models import queryCapability, servers as serverModel
    alice, _, server = owned
    key = f'query-capability:{server.id}'
    queryCapability.check(server)
    serverModel.saveInfo(server, {'timestamp': 1, 'query_result': {}})
    assert redisModel.redisClient.get(key) is None
    queryCapability.check(server)
    response = client.post('/servers/edit', json={'id': server.id, 'url': 'https://hub2.test'},
                           headers=auth_headers(alice))
    assert response.status_code == 200
    assert redisModel.redisClient.get(key) is None
    queryCapability.check(server)
    redisModel.deleteServerData(server.uuid, server.id)
    assert redisModel.redisClient.get(key) is None


def test_raw_request_passes_refusals_through_and_never_caches(monkeypatch):
    from application.controllers import utils
    sent = []

    class Session:
        def request(self, method, url, **options):
            sent.append((method, url, options))
            return FakeResponse(403, body('no_permission'))

    class Server:
        url = 'https://hub.test/'
        authkey = 'k' * 40
        skip_ssl = True

    monkeypatch.setattr(utils, 'getRequestPSession', lambda: Session())
    monkeypatch.setattr(utils, 'getMISPRequestSession', lambda: pytest.fail('the cached session was used'))
    response = utils.mispRawRequest(Server(), 'GET', '/attributes/queryDescribe')
    assert response.status_code == 403
    [(method, url, options)] = sent
    assert (method, url, options['json'], options['verify']) == ('GET', 'https://hub.test/attributes/queryDescribe',
                                                                 None, False)
    assert options['headers']['Authorization'] == 'k' * 40

    class Failing:
        def request(self, *args, **kwargs):
            raise requests.exceptions.ConnectTimeout()

    monkeypatch.setattr(utils, 'getRequestPSession', lambda: Failing())
    assert utils.mispRawRequest(Server(), 'GET', '/attributes/queryDescribe') == {'error': 'Server unreachable'}
