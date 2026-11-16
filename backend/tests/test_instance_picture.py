"""The picture of a MISP instance: the logo of its login page, fetched by the backend from the server's own URL and
answered as a data URI"""
import base64

import pytest

# Login pages as MISP serves them: MISP 3 marks a light and a dark logo, built from `MISP.baseurl`, which is not
# necessarily the address MFC uses
MISP3_LOGIN = """<html><body>
<img class="oml-logo-dark" src="https://localhost:4443/img/misp-logo-horizontal-light.png" alt="MISP">
<img class="oml-logo-light" src="https://localhost:4443/img/misp-logo-horizontal.png" alt="MISP">
</body></html>"""
MISP2_LOGIN = """<html><body><img src="/img/custom/logo.png" style="display:block;"/></body></html>"""
INLINE_LOGIN = """<html><body><img src="data:image/png;base64,iVBORw0KGgo=" /></body></html>"""
PNG = b"\x89PNG\r\n\x1a\nlogo"


class Response:
    def __init__(self, content, content_type="image/png", status_code=200):
        self.content, self.status_code = content, status_code
        self.headers = {"Content-Type": content_type}


@pytest.fixture()
def owned(db, make_user):
    from application.DBModels import Fleet, Server
    alice, bob = make_user("alice@test.local"), make_user("bob@test.local")
    fleet = Fleet(name="picture fleet", description="", user_id=alice.id, timestamp=1)
    db.session.add(fleet)
    db.session.commit()
    server = Server(name="picture-misp", url="https://misp.example:8443", authkey="K" * 40, fleet_id=fleet.id,
                    user_id=alice.id)
    db.session.add(server)
    db.session.commit()
    yield {"alice": alice, "bob": bob, "server": server}
    db.session.delete(server)
    db.session.delete(fleet)
    db.session.commit()


@pytest.fixture()
def misp(monkeypatch):
    """Stubs the MISP instance: `pages` maps a requested URL to what it answers; `requests` records the calls"""
    import application
    import application.models.instancePicture as pictureModel
    state = {"pages": {}, "requests": []}

    def fakeGet(server, url, rawResponse=False, **kwargs):
        state["requests"].append((url, server.authkey))
        answer = state["pages"].get(url, {"error": "Server unreachable"})
        return answer
    monkeypatch.setattr(pictureModel, "mispGetHTMLRequest", fakeGet)
    application.redisClient.flushdb()
    return state


def picture(client, auth_headers, user, server):
    response = client.get(f"/servers/getInstancePicture/{server.id}", headers=auth_headers(user))
    assert response.status_code == 200
    return response.get_json()


def test_misp3_logo_is_fetched_from_the_servers_own_address(owned, client, auth_headers, misp):
    server = owned["server"]
    misp["pages"]["/users/login"] = MISP3_LOGIN
    misp["pages"]["https://misp.example:8443/img/misp-logo-horizontal.png"] = Response(PNG)
    assert picture(client, auth_headers, owned["alice"], server) == \
        "data:image/png;base64," + base64.b64encode(PNG).decode()
    # Anonymous: the login page and the logo are read without the server's authkey
    assert [authkey for _, authkey in misp["requests"]] == [None, None]


def test_relative_and_inline_logos(owned, client, auth_headers, misp):
    server = owned["server"]
    misp["pages"]["/users/login"] = MISP2_LOGIN
    misp["pages"]["https://misp.example:8443/img/custom/logo.png"] = Response(PNG, "image/png; charset=binary")
    assert picture(client, auth_headers, owned["alice"], server).startswith("data:image/png;base64,")

    import application
    application.redisClient.flushdb()
    misp["pages"]["/users/login"] = INLINE_LOGIN
    assert picture(client, auth_headers, owned["alice"], server) == "data:image/png;base64,iVBORw0KGgo="


@pytest.mark.parametrize("login, answer", [
    (MISP2_LOGIN, Response(b"<html>not found</html>", "text/html")),  # Not an image
    (MISP2_LOGIN, Response(PNG, status_code=404)),
    (MISP2_LOGIN, Response(b"x" * (1024 * 1024 + 1))),  # Too big
    (MISP2_LOGIN, {"error": "Server unreachable"}),
    ("<html><body>No image</body></html>", None),
    ('<img src="javascript:alert(1)">', None),
    ('<img src="data:text/html;base64,PHNjcmlwdD4=">', None),
])
def test_no_picture(owned, client, auth_headers, misp, login, answer):
    misp["pages"]["/users/login"] = login
    if answer is not None:
        misp["pages"]["https://misp.example:8443/img/custom/logo.png"] = answer
    assert picture(client, auth_headers, owned["alice"], owned["server"]) == ""


def test_unreachable_server_has_no_picture(owned, client, auth_headers, misp):
    assert picture(client, auth_headers, owned["alice"], owned["server"]) == ""


def test_pictures_are_cached(owned, client, auth_headers, misp):
    server = owned["server"]
    misp["pages"]["/users/login"] = MISP2_LOGIN
    misp["pages"]["https://misp.example:8443/img/custom/logo.png"] = Response(PNG)
    first = picture(client, auth_headers, owned["alice"], server)
    assert picture(client, auth_headers, owned["alice"], server) == first
    assert len(misp["requests"]) == 2


def test_only_the_owner_gets_the_picture(owned, client, auth_headers, misp):
    misp["pages"]["/users/login"] = MISP2_LOGIN
    misp["pages"]["https://misp.example:8443/img/custom/logo.png"] = Response(PNG)
    assert picture(client, auth_headers, owned["bob"], owned["server"]) == ""
    assert misp["requests"] == []
    assert client.get(f"/servers/getInstancePicture/{owned['server'].id}").status_code == 401
