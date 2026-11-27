"""Reading the metric sources: MISP 3.0.0 answers, older formats, translated titles and broken answers"""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "metrics_misp_3.0.0.json").read_text())
MB = 1024 ** 2


@pytest.fixture()
def answers():
    return copy.deepcopy(FIXTURE)


def test_catalogue_is_consistent():
    from application.models import metricCatalogue as catalogue
    keys = [metric.key for metric in catalogue.CATALOGUE]
    assert len(keys) == len(set(keys))
    sources = {source.name for source in catalogue.SOURCES} | {"logins"}
    for metric in catalogue.CATALOGUE:
        assert metric.kind in catalogue.KINDS and metric.group in catalogue.GROUPS and metric.source in sources
    assert catalogue.SOURCES[0].name == "statistics"  # Asked first: an unreachable server gets nothing else


def test_misp_3_statistics(answers):
    from application.models.metricCatalogue import parseStatistics
    assert parseStatistics(answers["statistics"]) == {
        "events": 4291, "attributes": 2923792, "objects": 70189, "event_reports": 173, "analyst_data": 764,
        "correlations": 342383, "proposals": 8, "users": 6, "users_pgp": 0, "orgs": 91, "local_orgs": 4,
        "contributing_orgs": 67,
    }


def test_older_statistics_miss_some_keys(answers):
    from application.models.metricCatalogue import parseStatistics
    stats = answers["statistics"]["stats"]
    for field in ("analyst_data_count", "eventreport_count"):
        del stats[field]
    stats["proposal_count"] = None
    values = parseStatistics(answers["statistics"])
    assert "analyst_data" not in values and "event_reports" not in values and "proposals" not in values
    assert values["events"] == 4291


@pytest.mark.parametrize("answer", [{}, {"stats": {}}, {"stats": "nope"}, [], None])
def test_unreadable_statistics(answer):
    from application.models.metricCatalogue import UnreadableAnswer, parseStatistics
    with pytest.raises(UnreadableAnswer):
        parseStatistics(answer)


def test_registrations(answers):
    from application.models.metricCatalogue import UnreadableAnswer, parseRegistrations
    assert parseRegistrations(answers["registrations"]) == {"pending_registrations": 1}
    assert parseRegistrations([]) == {"pending_registrations": 0}
    assert parseRegistrations({"data": [{}, {}]}) == {"pending_registrations": 2}
    with pytest.raises(UnreadableAnswer):
        parseRegistrations({"name": "Not Found"})


def test_misp_3_diagnostics(answers):
    from application.models.metricCatalogue import parseDiagnostics
    assert parseDiagnostics(answers["diagnostics"]) == {
        "queue_cache": 0, "queue_default": 0, "queue_email": 0, "queue_prio": 0, "queue_update": 0,
        "redis_memory_bytes": 42894624, "redis_memory_peak_bytes": 206394256,
    }


def test_diagnostics_without_redis_or_workers(answers):
    from application.models.metricCatalogue import UnreadableAnswer, parseDiagnostics
    diagnostics = answers["diagnostics"]
    diagnostics["workers"]["prio"]["jobCount"] = "12"
    del diagnostics["workers"]["email"]["jobCount"]
    del diagnostics["redisInfo"]
    assert parseDiagnostics(diagnostics) == {"queue_cache": 0, "queue_default": 0, "queue_prio": 12,
                                             "queue_update": 0}
    with pytest.raises(UnreadableAnswer):
        parseDiagnostics({"version": {}, "redisInfo": {"connection": False}})


def test_misp_3_system_widget(answers):
    from application.models.metricCatalogue import parseSystemWidget
    values = parseSystemWidget(answers["system_widget"])
    assert values == {
        "disk_used_pct": 77.27, "load_1": 4.16015625, "load_5": 4.869140625, "load_15": 4.6298828125,
        "memory_free_bytes": int(round(3099.95 * MB)), "memory_used_pct": 90.23,
    }
    assert not any(isinstance(value, str) for value in values.values())  # The key owner's email is never kept


def test_system_widget_is_read_by_value_format():
    """Titles are translated; the disk line carries a warning above MISP's threshold"""
    from application.models.metricCatalogue import UnreadableAnswer, parseSystemWidget
    answer = {"data": [
        {"title": "Utilisateur", "value": "77 rue@misp.test"},
        {"title": "Système", "value": "Linux 5.10.0-21 - x86_64"},
        {"title": "Utilisation du disque", "value": "91.2% - [Above Threshold]", "class": "red"},
        {"title": "Charge", "value": "0.5 - 0.25 - 0"},
        {"title": "Mémoire", "value": "512 MB free (75 % used)"},
    ]}
    assert parseSystemWidget(answer) == {"disk_used_pct": 91.2, "load_1": 0.5, "load_5": 0.25, "load_15": 0.0,
                                         "memory_free_bytes": 512 * MB, "memory_used_pct": 75.0}
    with pytest.raises(UnreadableAnswer):
        parseSystemWidget({"data": [{"title": "User", "value": "admin@misp.test"}]})
    with pytest.raises(UnreadableAnswer):
        parseSystemWidget({"message": "Widget not found"})


def test_misp_3_admin_widget(answers):
    """The "MySQL DB disk usage" line is the size of MISP's database"""
    from application.models.metricCatalogue import parseAdminWidget
    assert parseAdminWidget(answers["admin_widget"]) == {
        "redis_memory_bytes": 41 * MB, "redis_memory_peak_bytes": 197 * MB, "db_size_bytes": int(round(8893.8 * MB)),
    }


def test_admin_widget_without_redis_and_translated():
    from application.models.metricCatalogue import parseAdminWidget
    assert parseAdminWidget({"data": [{"title": "MySQL DB disk usage", "value": "120.5M"}]}) == \
        {"db_size_bytes": int(round(120.5 * MB))}
    translated = {"data": [{"title": "Mémoire Redis actuelle", "value": "2M"},
                           {"title": "Pic mémoire Redis", "value": "3M"},
                           {"title": "Espace disque de la base", "value": "1.5G"}]}
    assert parseAdminWidget(translated) == {"redis_memory_bytes": 2 * MB, "redis_memory_peak_bytes": 3 * MB,
                                            "db_size_bytes": int(1.5 * 1024 ** 3)}
    assert parseAdminWidget({"data": [{"title": "Taille", "value": "10M"}]}) == {"db_size_bytes": 10 * MB}
    # Another layout: the English titles
    other = {"data": [{"title": "Uptime", "value": "3 days"}, {"title": "MySQL DB disk usage", "value": "4M"}]}
    assert parseAdminWidget(other) == {"db_size_bytes": 4 * MB}


@pytest.mark.parametrize("text, size", [("8893.8M", int(round(8893.8 * MB))), ("1.5G", int(1.5 * 1024 ** 3)),
                                        ("512K", 512 * 1024), ("10", 10), ("2 MB", 2 * MB), ("3GiB", 3 * 1024 ** 3),
                                        ("abc", None), ("", None), (None, None), ("-1M", None)])
def test_sizes(text, size):
    from application.models.metricCatalogue import parseSize
    assert parseSize(text) == size


def test_misp_3_api_activity(answers):
    """The header's total: the per-key rows (names and emails) are never kept"""
    from application.models.metricCatalogue import parseApiActivity
    assert parseApiActivity(answers["api_activity_widget"]) == {"api_requests_24h": 1998}


def test_api_activity_formats():
    from application.models.metricCatalogue import UnreadableAnswer, parseApiActivity
    # Translated header: the badges are summed
    translated = {"data": [{"type": "header", "value": "2 clés · 12 requêtes"},
                           {"type": "user", "name": "a", "badge": 5}, {"type": "user", "name": "b", "badge": "7"}]}
    assert parseApiActivity(translated) == {"api_requests_24h": 12}
    assert parseApiActivity({"data": [{"type": "header", "value": "No API activity in this period."}]}) == \
        {"api_requests_24h": 0}
    # MISP 2.4: one row per key, its count at the start of `html`
    legacy = {"data": [{"title": "a@misp.test", "html": "120 (last: 2024-01-01)"},
                       {"title": "b@misp.test", "html": "30 <span>…</span>"}]}
    assert parseApiActivity(legacy) == {"api_requests_24h": 150}
    assert parseApiActivity({"data": []}) == {"api_requests_24h": 0}
    with pytest.raises(UnreadableAnswer):
        parseApiActivity({"data": [{"title": "something", "html": "no number"}]})


def test_own_account(answers):
    """`/users/view/me`: the account behind Fleet Commander's key, and how MISP counts the key's requests"""
    from application.models.metricCatalogue import OwnAccount, UnreadableAnswer, parseOwnAccount
    key = "AbCd" + "x" * 32 + "WxYz"
    assert parseOwnAccount(answers["own_account"], key) == OwnAccount(16, "admin@misp.test", "AbCdWxYz")
    assert parseOwnAccount({"User": {"id": "bad", "email": " Admin@MISP.test "}}, f" {key}\n") == \
        OwnAccount(None, "admin@misp.test", "AbCdWxYz")
    assert parseOwnAccount({"User": {"id": 3, "email": "a@b.c"}}, "short").key == ""
    for broken in ({"User": {"id": "16"}}, {"name": "Forbidden"}, [], None):
        with pytest.raises(UnreadableAnswer):
            parseOwnAccount(broken, key)


def own():
    from application.models.metricCatalogue import OwnAccount
    return OwnAccount(16, "admin@misp.test", "AbCdWxYz")


def test_api_activity_leaves_fleet_commanders_own_requests_out(answers):
    """MISP 2.5 and 3: the rows of its account (by email, any case), and its key when MISP does not know whose it is"""
    from application.models.metricCatalogue import parseApiActivity
    widget = answers["api_activity_widget"]
    assert parseApiActivity(widget, own()) == {"api_requests_24h": 1998}  # Not among the keys
    widget["data"][0]["value"] = "10 keys · 3698 requests · 7 unknown"
    widget["data"] += [{"type": "user", "name": "Admin@MISP.test", "meta": "key AbCd · ORGNAME · admin", "badge": 1500},
                       {"type": "user", "glyph": "warn", "name": "AbCdWxYz", "meta": "Unknown key", "badge": "200"}]
    assert parseApiActivity(widget, own()) == {"api_requests_24h": 1998}
    assert parseApiActivity(widget) == {"api_requests_24h": 3698}
    # Translated header: the other keys' badges
    widget["data"][0]["value"] = "10 clés · 3698 requêtes"
    assert parseApiActivity(widget, own()) == {"api_requests_24h": 1998}
    # Only Fleet Commander's key was used
    alone = {"data": [{"type": "header", "value": "1 key · 40 requests"},
                      {"type": "user", "name": "admin@misp.test", "badge": 40}]}
    assert parseApiActivity(alone, own()) == {"api_requests_24h": 0}


def test_api_activity_leaves_fleet_commanders_own_requests_out_on_misp_2_4():
    """MISP 2.4 links each known key to its owner and shows the key; an unknown key is only shown"""
    from application.models.metricCatalogue import parseApiActivity
    legacy = {"data": [
        {"html_title": '<a href="https://misp.test/auth_keys/view/3">ab01ab01</a>',
         "html": '120 (<a href="https://misp.test/admin/users/view/2">a@misp.test</a>)'},
        {"html_title": '<a href="https://misp.test/auth_keys/view/9">ef01ef01</a>',
         "html": '900 (<a href="https://misp.test/admin/users/view/16">admin@misp.test</a>)'},
        {"html_title": '<a href="https://misp.test/auth_keys/view/8">cd01cd01</a>',
         "html": '30 (<a href="https://misp.test/admin/users/view/160">x@misp.test</a>)'},
        {"title": "AbCdWxYz", "html": '7 (<span class="red">Unknown key</span>)'},
        {"title": "zzzzzzzz", "html": '3 (<span class="red">Unknown key</span>)'},
    ]}
    assert parseApiActivity(legacy) == {"api_requests_24h": 1060}
    assert parseApiActivity(legacy, own()) == {"api_requests_24h": 153}
    # Its key known to MISP, under another account than the one it reported (legacy key bookkeeping)
    other = {"data": [{"html_title": '<a href="https://misp.test/auth_keys/view/9">AbCdWxYz</a>',
                       "html": '40 (<a href="https://misp.test/admin/users/view/5">y@misp.test</a>)'}]}
    assert parseApiActivity(other, own()) == {"api_requests_24h": 0}


def test_login_log_entries(answers):
    """Web logins and failed web logins; a rejected API key (`auth_fail`, 267020) is not a login"""
    from application.models.metricCatalogue import LoginEntry, parseLoginLogs, parseLogCreated
    entries = parseLoginLogs(answers["logs"])
    assert entries == [
        LoginEntry(267013, "logins", parseLogCreated("2026-11-17 15:26:32")),
        LoginEntry(267021, "failed_logins", parseLogCreated("2026-11-17 15:28:05")),
        LoginEntry(267426, "logins", parseLogCreated("2026-11-18 07:26:53")),
    ]
    assert parseLogCreated("2026-11-18 07:26:53") == int(datetime(2026, 11, 18, 7, 26, 53, tzinfo=timezone.utc).timestamp())
    mixed = {"data": [{"id": 5, "action": "login", "created": "bad date"}, {"Log": {"id": "x", "action": "login"}},
                      {"Log": {"id": "6", "action": "edit"}}, "junk"]}
    assert parseLoginLogs(mixed) == [LoginEntry(5, "logins", None)]


def test_logins_of_fleet_commanders_own_account(answers):
    """Its logins are left out, by user id or email; failed attempts on it are kept"""
    from application.models.metricCatalogue import OwnAccount, parseLoginLogs
    owner = OwnAccount(2, "other@misp.test", "AbCdWxYz")
    assert [entry.id for entry in parseLoginLogs(answers["logs"], owner)] == [267013, 267021]
    byEmail = {"data": [{"Log": {"id": "7", "action": "login", "user_id": "", "email": "Other@MISP.test"}},
                        {"Log": {"id": "8", "action": "login", "user_id": "3", "email": "else@misp.test"}}]}
    assert [entry.id for entry in parseLoginLogs(byEmail, owner)] == [8]
