"""Plugins report what went wrong on a server: a request that failed (unreachable, timeout), an HTTP error status,
or a refusal MISP answered with HTTP 200. None of these may be counted as a success"""
import pytest


@pytest.fixture(autouse=True)
def _app(app):
    return app


class Answer:
    def __init__(self, status, body, reason=None):
        self.status_code, self._body = status, body
        self.ok = status < 400
        self.reason = reason or ("OK" if self.ok else "Forbidden")
        self.headers, self.url, self.elapsed = {}, "https://misp.test/x", 0.1

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


class Server:
    id, name, url, authkey, skip_ssl = 1, "misp", "https://misp.test", "k", False


UNREACHABLE = {"error": "Server unreachable"}


@pytest.mark.parametrize("result, expected", [
    (UNREACHABLE, "Server unreachable"),
    ({"error": "Authentication error", "_status_code": 403}, "Authentication error"),
    ({"saved": True}, None),
    ({"Server": {"id": 1}, "_status_code": 200}, None),
    ({"saved": False, "errors": {"url": ["Invalid URL"]}}, "url: Invalid URL"),
    (Answer(200, {"saved": True, "success": True}), None),
    (Answer(200, [{"Taxonomy": {"id": 1}}]), None),
    (Answer(200, None), None),
    (Answer(200, {"saved": False, "name": "Could not enable"}), "Could not enable"),
    (Answer(403, {"name": "Forbidden", "message": "You do not have permission", "url": "/x"}),
     "HTTP 403 Forbidden: You do not have permission"),
    (Answer(500, None, "Internal Server Error"), "HTTP 500 Internal Server Error"),
    (None, "No answer"),
])
def test_misp_request_error(result, expected):
    from application.controllers.utils import mispRequestError
    assert mispRequestError(result) == expected


def stub(monkeypatch, module, get=None, post=None):
    if get is not None:
        monkeypatch.setattr(module, "mispGetRequest", lambda *a, **k: get(*a) if callable(get) else get)
    if post is not None:
        monkeypatch.setattr(module, "mispPostRequest", lambda *a, **k: post(*a) if callable(post) else post)


def test_toggle_taxonomy_on_an_unreachable_server(monkeypatch):
    from application.plugins import ToggleTaxonomy as module
    stub(monkeypatch, module, get=UNREACHABLE)
    response = module.ToggleTaxonomy().action(Server(), {"enabled": "1", "taxonomies_uuid": ["tlp"]}).response()
    assert response["status"] == "fail"
    assert response["error"] == ["Could not list the taxonomies: Server unreachable"]


def test_a_refused_taxonomy_change_is_not_a_success(monkeypatch):
    from application.plugins import ToggleTaxonomy as module
    index = Answer(200, [{"Taxonomy": {"id": 3, "namespace": "tlp"}}, {"Taxonomy": {"id": 4, "namespace": "pap"}}])
    stub(monkeypatch, module, get=index,
         post=lambda server, url, *rest: Answer(403, {"message": "Not allowed"}) if url.endswith("/4") else Answer(200, {"saved": True}))
    response = module.ToggleTaxonomy().action(Server(), {"enabled": "0", "taxonomies_uuid": ["tlp", "pap", "nope"]}).response()
    assert response["data"]["data"]["successes"] == ["tlp"]
    assert response["error"] == ["pap - HTTP 403 Forbidden: Not allowed", "nope - Could not find taxonomy with name `nope`"]


def test_taxonomy_tags_that_cannot_be_created_are_reported(monkeypatch):
    from application.plugins import ToggleTaxonomy as module
    stub(monkeypatch, module, get=Answer(200, [{"Taxonomy": {"id": 3, "namespace": "tlp"}}]),
         post=lambda server, url, *rest: UNREACHABLE if "addTag" in url else Answer(200, {"saved": True}))
    response = module.ToggleTaxonomy().action(Server(), {"enabled": "1", "taxonomies_uuid": ["tlp"]}).response()
    assert response["status"] == "fail"
    assert response["error"] == ["tlp - Enabled, but its tags could not be created: Server unreachable"]


def test_toggle_galaxy_failures(monkeypatch):
    from application.plugins import ToggleGalaxy as module
    stub(monkeypatch, module, get=Answer(200, {"name": "Not an index"}))
    response = module.ToggleGalaxy().action(Server(), {"enabled": "1", "galaxies_uuid": ["u1"]}).response()
    assert response["error"] == ["Could not list the galaxies: unexpected answer"]

    stub(monkeypatch, module, get=Answer(200, [{"Galaxy": {"id": 7, "uuid": "u1"}}]),
         post=Answer(200, {"saved": False, "errors": "Galaxy not found"}))
    response = module.ToggleGalaxy().action(Server(), {"enabled": "1", "galaxies_uuid": ["u1"]}).response()
    assert response["status"] == "fail" and response["error"] == ["u1 - Galaxy not found"]


def test_query_organisation_failures(monkeypatch):
    from application.plugins import QueryOrganisation as module
    plugin = module.QueryOrganisation()
    stub(monkeypatch, module, get=UNREACHABLE)
    assert plugin.action(Server(), {"org_name_or_uuid": "CIRCL"}).response()["error"] == ["Server unreachable"]
    stub(monkeypatch, module, get=Answer(404, {"message": "Invalid organisation"}, "Not Found"))
    assert plugin.action(Server(), {"org_name_or_uuid": "CIRCL"}).response()["error"] == ["Invalid organisation"]
    stub(monkeypatch, module, get=Answer(200, {"Organisation": {"name": "CIRCL"}}))
    response = plugin.action(Server(), {"org_name_or_uuid": "CIRCL"}).response()
    assert response["status"] == "success" and response["data"]["message"] == "Organisation `CIRCL` exists on server `misp`"


def test_galaxy_import_failures(monkeypatch):
    from application.plugins import GalaxyImport as module
    stub(monkeypatch, module, post=UNREACHABLE)
    assert module.GalaxyImport.doImport(Server(), {}).response()["error"] == ["Server unreachable"]
    stub(monkeypatch, module, post=Answer(403, {"message": "Could not import", "errors": ["Bad cluster"]}))
    assert module.GalaxyImport.doImport(Server(), {}).response()["error"] == ["HTTP 403 Forbidden: Could not import - Bad cluster"]


def test_mass_user_import_failures(monkeypatch):
    from application.plugins import MassUserImport as module
    stub(monkeypatch, module, post=UNREACHABLE)
    assert module.MassUserImport.addUser(Server(), {"email": "a@a.test"}) == "a@a.test - Server unreachable"
    stub(monkeypatch, module, post=Answer(403, {"message": "The user could not be saved.",
                                               "errors": {"email": ["An account with this email exists"]}}))
    assert module.MassUserImport.addUser(Server(), {"email": "a@a.test"}) == \
        "a@a.test - HTTP 403 Forbidden: The user could not be saved. - email: An account with this email exists"
    stub(monkeypatch, module, post=Answer(200, {"User": {"id": 5}}))
    assert module.MassUserImport.addUser(Server(), {"email": "a@a.test"}) is True

