"""Large JSON answers are gzip-compressed for clients that accept it"""

import gzip
import json

from flask import jsonify, make_response

from application.compression import MIN_SIZE, compressResponse

LARGE = {"items": [{"setting": f"MISP.setting_{n}", "value": n} for n in range(2000)]}


def answer(app, payload, accept="gzip, deflate, br", status=200):
    headers = {"Accept-Encoding": accept} if accept is not None else {}
    with app.test_request_context(headers=headers):
        response = make_response(jsonify(payload), status)
        response.direct_passthrough = False
        return compressResponse(response)


def test_large_json_is_compressed_when_accepted(app):
    response = answer(app, LARGE)
    assert response.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["Vary"]
    body = response.get_data()
    assert int(response.headers["Content-Length"]) == len(body)
    assert json.loads(gzip.decompress(body)) == LARGE
    assert len(body) * 4 < len(json.dumps(LARGE))


def test_left_alone_when_not_accepted_small_or_not_json(app):
    plain = answer(app, LARGE, accept=None)
    assert "Content-Encoding" not in plain.headers and json.loads(plain.get_data()) == LARGE
    assert "Accept-Encoding" in plain.headers["Vary"]
    refused = answer(app, LARGE, accept="gzip;q=0, identity")
    assert "Content-Encoding" not in refused.headers
    small = answer(app, {"ok": True})
    assert len(small.get_data()) < MIN_SIZE and "Content-Encoding" not in small.headers
    error = answer(app, LARGE, status=500)
    assert "Content-Encoding" not in error.headers
    with app.test_request_context(headers={"Accept-Encoding": "gzip"}):
        text = compressResponse(make_response("x" * (MIN_SIZE * 2)))
        assert "Content-Encoding" not in text.headers


def test_fleet_server_list_is_compressed(db, client, make_user, auth_headers):
    """The answer that weighs most: every server with its last snapshot"""
    from application import redisModel
    from application.DBModels import Fleet, Server

    user = make_user("gzip-user@test.local")
    fleet = Fleet(name="Gzip fleet", description="", user_id=user.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="big", url="https://big.test", authkey="k" * 40, fleet_id=fleet.id, user_id=user.id)
    db.session.add(server)
    db.session.commit()
    finalSettings = [{"setting": f"MISP.setting_{n}", "value": n, "description": "A setting"} for n in range(2000)]
    redisModel.saveServerInfo(server.uuid, {"timestamp": 1, "query_result": {"serverSettings": {"finalSettings": finalSettings}}})

    url = f"/servers/index/{fleet.id}"
    compressed = client.get(url, headers=dict(auth_headers(user), **{"Accept-Encoding": "gzip"}))
    assert compressed.status_code == 200 and compressed.headers["Content-Encoding"] == "gzip"
    servers = json.loads(gzip.decompress(compressed.get_data()))
    assert servers[0]["server_info"]["query_result"]["serverSettings"]["finalSettings"] == finalSettings
    plain = client.get(url, headers=auth_headers(user))
    assert "Content-Encoding" not in plain.headers and json.loads(plain.get_data()) == servers
