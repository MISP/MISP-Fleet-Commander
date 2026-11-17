"""Shared MISP reads and writes: the plugins and baseline remediation rely on them reporting every failure"""
import pytest

from test_plugin_failures import UNREACHABLE, Answer, Server, stub


@pytest.fixture(autouse=True)
def _app(app):
    return app


@pytest.fixture()
def ops():
    from application.models import mispOps
    return mispOps


TEMPLATES = Answer(200, [
    # MISP keeps earlier versions of a template, inactive, under the same UUID: listed before or after the latest
    {"ObjectTemplate": {"id": "1", "uuid": "U-ACTIVE", "name": "file", "version": "3", "active": False}},
    {"ObjectTemplate": {"id": "2", "uuid": "U-ACTIVE", "name": "file", "meta-category": "file", "version": "4",
                        "active": True}},
    {"ObjectTemplate": {"id": "3", "uuid": "u-inactive", "name": "abuseipdb", "meta-category": "network",
                        "version": "2", "active": False}},
    {"ObjectTemplate": {"id": "4", "uuid": "u-inactive", "name": "abuseipdb", "version": "1", "active": True}},
])


def test_listings_are_keyed_and_typed(monkeypatch, ops):
    stub(monkeypatch, ops, get=lambda server, url, *rest: {
        "/taxonomies/index": Answer(200, [{"Taxonomy": {"id": "201", "namespace": "tlp", "enabled": True}},
                                         {"Taxonomy": {"id": "7", "namespace": "pap", "enabled": False}}]),
        "/galaxies/index": Answer(200, [{"Galaxy": {"id": "155", "uuid": "g1", "name": "FireHOL", "type": "IPset",
                                                    "namespace": "firehol", "enabled": "0"}}]),
        "/objectTemplates/index/all": TEMPLATES,
    }[url])
    assert ops.taxonomies(Server()) == {"tlp": {"id": 201, "enabled": True}, "pap": {"id": 7, "enabled": False}}
    assert ops.galaxies(Server()) == {"g1": {"id": 155, "enabled": False, "name": "FireHOL", "namespace": "firehol",
                                             "type": "IPset"}}
    templates = ops.objectTemplates(Server())
    assert sorted(templates) == ["u-active", "u-inactive"]
    assert templates["u-active"] == {"id": 2, "active": True, "name": "file", "meta_category": "file", "version": 4}
    assert templates["u-inactive"] == {"id": 3, "active": False, "name": "abuseipdb", "meta_category": "network",
                                       "version": 2}


def test_object_templates_are_only_toggled_when_needed(monkeypatch, ops):
    posted = []
    stub(monkeypatch, ops, get=TEMPLATES, post=lambda server, url, data: posted.append(data) or Answer(200, {}))
    assert ops.setObjectTemplateActive(Server(), "U-Active", True) is False
    assert ops.setObjectTemplateActive(Server(), "u-inactive", True) is True
    assert posted == [{"ObjectTemplate": {"data": 3}}]
    with pytest.raises(ops.MispOpError, match="Could not find object template `u-missing`"):
        ops.setObjectTemplateActive(Server(), "u-missing", True)


def test_settings_are_read_and_changed(monkeypatch, ops):
    calls = []
    stub(monkeypatch, ops, get=lambda server, url, *rest: calls.append(url) or Answer(200, {"name": "MISP.live", "value": True}),
         post=lambda server, url, data: calls.append((url, data)) or Answer(200, {"saved": True, "success": True}))
    assert ops.getSetting(Server(), "MISP.live") is True
    assert ops.editSetting(Server(), "Plugin.Enrichment_services_url", "http://modules").status_code == 200
    assert calls == ["/servers/getSetting/MISP.live",
                     ("/servers/serverSettingsEdit/Plugin.Enrichment_services_url",
                      {"Server": {"value": "http://modules", "force": 1}})]
    # Saved like MISP's settings page does: a diagnostic that fails on purpose does not block the change
    calls.clear()
    ops.editSetting(Server(), "MISP.disable_emailing", True)
    assert calls == [("/servers/serverSettingsEdit/MISP.disable_emailing", {"Server": {"value": True, "force": 1}})]

    stub(monkeypatch, ops, get={"error": "Authentication error", "_status_code": 403},
         post=Answer(405, {"message": "This setting can only be edited via the CLI."}, "Method Not Allowed"))
    with pytest.raises(ops.MispOpError, match="Could not read `Security.salt`: Authentication error"):
        ops.getSetting(Server(), "Security.salt")
    with pytest.raises(ops.MispOpError) as error:
        ops.editSetting(Server(), "MISP.python_bin", "/usr/bin/python3")
    assert error.value.message == ("Could not change `MISP.python_bin`: HTTP 405 Method Not Allowed: "
                                   "This setting can only be edited via the CLI.")
    assert error.value.response.status_code == 405


def test_toggle_object_reports_an_unreachable_server(monkeypatch, ops):
    from application.plugins import ToggleObject as module
    stub(monkeypatch, ops, get=UNREACHABLE)
    response = module.ToggleObject().action(Server(), {"template_uuids": ["u-active"]}).response()
    assert response["status"] == "fail"
    assert response["error"] == ["Could not list the object templates: Server unreachable"]

    posted = []
    stub(monkeypatch, ops, get=TEMPLATES, post=lambda server, url, data: posted.append(data) or Answer(200, {}))
    response = module.ToggleObject().action(Server(), {"template_uuids": ["U-ACTIVE", "u-missing"]}).response()
    assert response["status"] == "success"
    assert response["data"]["data"]["successes"] == ["U-ACTIVE"]
    assert posted == [{"ObjectTemplate": {"data": 2}}]  # The latest version, not the one listed first
    assert response["error"] == ["u-missing - Could not find template with name or UUID `u-missing`"]


def test_live_mode(monkeypatch, ops):
    from application.plugins import LiveMode as module
    stub(monkeypatch, ops, post=Answer(200, {"saved": True, "success": True}))
    response = module.LiveMode().action(Server(), {"enabled": "0"}).response()
    assert response["status"] == "success" and response["request_response"]["status_code"] == 200

    stub(monkeypatch, ops, post=UNREACHABLE)
    response = module.LiveMode().action(Server(), {"enabled": "1"}).response()
    assert response["status"] == "fail"
    assert response["error"] == ["Could not change `MISP.live`: Server unreachable"]
