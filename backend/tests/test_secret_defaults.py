"""Secrets must come from the environment, never from defaults committed in the source"""
import importlib


def test_no_default_grafana_or_influxdb_token(monkeypatch):
    for name in ("GRAFANA_APIKEY", "INFLUXDB_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    import config
    import application.monitoring.config as monitoringConfig
    try:
        assert importlib.reload(config).Config.GRAFANA_APIKEY is None
        assert importlib.reload(monitoringConfig).INFLUXDB_TOKEN is None
    finally:
        importlib.reload(config)
        importlib.reload(monitoringConfig)


def test_tokens_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("GRAFANA_APIKEY", "grafana-token")
    monkeypatch.setenv("INFLUXDB_TOKEN", "influx-token")
    import config
    import application.monitoring.config as monitoringConfig
    try:
        assert importlib.reload(config).Config.GRAFANA_APIKEY == "grafana-token"
        assert importlib.reload(monitoringConfig).INFLUXDB_TOKEN == "influx-token"
    finally:
        monkeypatch.undo()
        importlib.reload(config)
        importlib.reload(monitoringConfig)
