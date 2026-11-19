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
