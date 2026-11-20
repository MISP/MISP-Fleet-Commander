#!/usr/bin/env python3

import json
import os
from typing import List, Union
from pathlib import Path


current_path = Path(__file__).resolve().parent
setting_path = current_path / "../../config.json"
setting_path = setting_path.resolve()
settings = {}
setting_configuration = {
    "fleet_watching_enabled": {
        "name": "Fleet Watching Enabled",
        "description": "If the watching system should be enabled.",
        "panel": "Scheduler",
        "scope": "Fleet Watcher",
        "type": "checkbox",
        "default": False,
        "disabled": False,
        "error": False,
    },
    "fleet_watching_interval": {
        "name": "Fleet Watching Interval",
        "description": "The frequency (minute) at which the watcher refeshes the wathed fleets",
        "panel": "Scheduler",
        "scope": "Fleet Watcher",
        "type": "number",
        "default": 1,
        "min": 1,
        "disabled": True,
        "error": {
            "error_message": "The frequency cannot be configured at the moment.",
            "variant": "info",
        },
    },
    "monitoring_enabled": {
        "name": "Monitoring Enabled",
        "description": "Collect usage metrics (content, users, logins, load, queues) from the servers of the fleets marked as monitored, and keep their history.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "checkbox",
        "default": True,
        "disabled": False,
        "error": False,
    },
    "monitoring_interval": {
        "name": "Monitoring Interval",
        "description": "How often (minutes) metrics are collected from each server of a monitored fleet.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "number",
        "default": 10,
        "min": 1,
        "max": 1440,
        "disabled": False,
        "error": False,
    },
    "monitoring_raw_retention_days": {
        "name": "Sample Retention",
        "description": "How long (days) every collected sample is kept. Samples draw the 24-hour charts. About 110 kB per server and day at a 10-minute interval. A shorter retention applies at the next hourly roll-up.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "number",
        "default": 14,
        "min": 2,
        "max": 90,
        "disabled": False,
        "error": False,
    },
    "monitoring_hour_retention_days": {
        "name": "Hourly Retention",
        "description": "How long (days) hourly figures are kept. They draw the 7-day and 30-day charts. Never shorter than the sample retention. About 26 kB per server and day.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "number",
        "default": 90,
        "min": 30,
        "max": 730,
        "disabled": False,
        "error": False,
    },
    "monitoring_day_retention_days": {
        "name": "Daily Retention",
        "description": "How long (days) daily figures are kept. They draw the 90-day and 1-year charts. 0 keeps them as long as their server; otherwise at least 365, and never shorter than the hourly retention. About 1 kB per server and day.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "number",
        "default": 0,
        "min": 0,
        "max": 3650,
        "disabled": False,
        "error": False,
    },
    "health_background_refresh_enabled": {
        "name": "Background Refresh Enabled",
        "description": "Keep the status of every server fresh without opening the UI: periodic connection tests and full refreshes of all servers, whether their fleet is watched or not.",
        "panel": "Scheduler",
        "scope": "Background Refresh",
        "type": "checkbox",
        "default": True,
        "disabled": False,
        "error": False,
    },
    "health_connection_test_interval": {
        "name": "Connection Test Interval",
        "description": "How often (minutes) every server gets a connection test. Cheap: one request per server.",
        "panel": "Scheduler",
        "scope": "Background Refresh",
        "type": "number",
        "default": 5,
        "min": 1,
        "max": 1440,
        "disabled": False,
        "error": False,
    },
    "health_full_refresh_interval": {
        "name": "Full Refresh Interval",
        "description": "How often (minutes) every server is fully refreshed (settings, workers, connections, usage). Servers refreshed more recently, for example by fleet watching, are skipped.",
        "panel": "Scheduler",
        "scope": "Background Refresh",
        "type": "number",
        "default": 30,
        "min": 5,
        "max": 1440,
        "disabled": False,
        "error": False,
    },
    "health_max_concurrency": {
        "name": "Maximum Concurrency",
        "description": "How many servers the background refresh queries at the same time.",
        "panel": "Scheduler",
        "scope": "Background Refresh",
        "type": "number",
        "default": 10,
        "min": 1,
        "max": 100,
        "disabled": False,
        "error": False,
    },
    "misp_request_timeout": {
        "name": "MISP Request Timeout",
        "description": "How long (seconds) MFC waits for a MISP server to answer a request before giving up on it. Connecting is given 5 seconds. Connection tests and link tests keep their own, shorter, limits.",
        "panel": "Scheduler",
        "scope": "MISP Requests",
        "type": "number",
        "default": 60,
        "min": 5,
        "max": 600,
        "disabled": False,
        "error": False,
    },
    "job_max_concurrency": {
        "name": "Job Concurrency",
        "description": "How many servers a job sends its requests to at the same time.",
        "panel": "Jobs",
        "scope": "Execution",
        "type": "number",
        "default": 5,
        "min": 1,
        "max": 50,
        "disabled": False,
        "error": False,
    },
    "job_retention_days": {
        "name": "Job Retention",
        "description": "How long (days) jobs and their per-server results are kept. They form the record of the changes made to the servers; older ones are deleted once a day.",
        "panel": "Jobs",
        "scope": "History",
        "type": "number",
        "default": 90,
        "min": 1,
        "max": 3650,
        "disabled": False,
        "error": False,
    },
    "query_max_limit": {
        "name": "Rows per Server",
        "description": "The highest LIMIT a query may ask of each server. A SELECT without LIMIT gets this one.",
        "panel": "Queries",
        "scope": "Limits",
        "type": "number",
        "default": 1000,
        "min": 1,
        "max": 10000,
        "disabled": False,
        "error": False,
    },
    "query_max_answer_mb": {
        "name": "Answer Size",
        "description": "The largest answer (MB) MFC reads from one server for a query. A larger answer is dropped and that server is reported as too large: lower the LIMIT.",
        "panel": "Queries",
        "scope": "Limits",
        "type": "number",
        "default": 20,
        "min": 1,
        "max": 500,
        "disabled": False,
        "error": False,
    },
    "query_rows_ttl_minutes": {
        "name": "Results Lifetime",
        "description": "How long (minutes) the rows a query brought back are kept. They are never written to the database: only the counts and errors of each server are, with the job.",
        "panel": "Queries",
        "scope": "Results",
        "type": "number",
        "default": 60,
        "min": 5,
        "max": 1440,
        "disabled": False,
        "error": False,
    },
}


class SettingError(ValueError):
    pass


# Shortest daily retention when it is not 0 (kept as long as the server): the 1-year charts are drawn from days
DAY_RETENTION_MIN_DAYS = 365


def intValue(setting_name: str) -> int:
    """The saved value as a whole number, or the default when config.json holds something else"""
    value = getRefreshValue(setting_name)
    try:
        if isinstance(value, bool) or not float(value).is_integer():
            raise ValueError
        return int(value)
    except (TypeError, ValueError):
        return int(settings[setting_name]["default"])


def _checkMetricRetention(setting_name: str, days: int):
    """A coarser tier never keeps less than a finer one: the roll-up would otherwise rebuild the hour rows deleted by
    retention from the raw rows still there, every hour. Only the neighbours of the edited setting are compared"""
    if setting_name == "monitoring_raw_retention_days":
        hour = intValue("monitoring_hour_retention_days")
        if days > hour:
            raise SettingError(f"The value must be at most the hourly retention ({hour} days): raise that one first")
    elif setting_name == "monitoring_hour_retention_days":
        raw, day = intValue("monitoring_raw_retention_days"), intValue("monitoring_day_retention_days")
        if days < raw:
            raise SettingError(f"The value must be at least the sample retention ({raw} days)")
        if day and days > day:
            raise SettingError(f"The value must be at most the daily retention ({day} days): raise that one first, or set it to 0")
    elif setting_name == "monitoring_day_retention_days" and days:
        hour = intValue("monitoring_hour_retention_days")
        if days < DAY_RETENTION_MIN_DAYS:
            raise SettingError(f"The value must be 0 (keep them as long as their server) or at least {DAY_RETENTION_MIN_DAYS}")
        if days < hour:
            raise SettingError(f"The value must be 0 or at least the hourly retention ({hour} days)")


CROSS_CHECKS = {
    "monitoring_raw_retention_days": _checkMetricRetention,
    "monitoring_hour_retention_days": _checkMetricRetention,
    "monitoring_day_retention_days": _checkMetricRetention,
}


def validate(setting_name: str, setting_value):
    """Check and normalise a value before saving it. Raises SettingError with a message meant for the user"""
    config = settings.get(setting_name)
    if config is None:
        raise SettingError(f"Unknown setting `{setting_name}`")
    if config.get("disabled"):
        raise SettingError(f"Setting `{setting_name}` cannot be changed")
    if config["type"] == "checkbox":
        if not isinstance(setting_value, bool):
            raise SettingError("The value must be true or false")
    elif config["type"] == "number":
        try:
            number = float(setting_value)
        except (TypeError, ValueError):
            raise SettingError("The value must be a number")
        if isinstance(setting_value, bool) or not number.is_integer():
            raise SettingError("The value must be a whole number")
        setting_value = int(number)
        if "min" in config and setting_value < config["min"]:
            raise SettingError(f"The value must be at least {config['min']}")
        if "max" in config and setting_value > config["max"]:
            raise SettingError(f"The value must be at most {config['max']}")
    if setting_name in CROSS_CHECKS:
        CROSS_CHECKS[setting_name](setting_name, setting_value)
    return setting_value


def loadSetting():
    global settings, setting_configuration
    setting_values = {}
    if os.path.exists(setting_path):
        try:
            with open(setting_path, 'r') as file:
                setting_values = json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            print(f'Error loading setting file: {e}. Using default settings.')
    else:
        print(f'Setting file {setting_path} not found. Using default settings.')
    settings = dict(setting_configuration)

    for setting_name, setting_config in settings.items():
        if setting_name in setting_values:
            settings[setting_name]['value'] = setting_values[setting_name]
        else:
            settings[setting_name]['value'] = setting_config.get('default', None)


def saveSettings():
    global settings
    setting_values = {}
    for setting_name, setting_config in settings.items():
        setting_values[setting_name] = setting_config['value']
    if os.path.exists(setting_path):
        try:
            with open(setting_path, 'w') as file:
                json.dump(setting_values, file, indent=4)
            loadSetting()
        except (json.JSONDecodeError, IOError) as e:
            print(f'Error loading setting file: {e}.')


def index() -> dict:
    global settings
    return settings


def get(setting_name: str) -> Union[dict, None]:
    global settings
    return settings.get(setting_name, None)


def getValue(setting_name: str) -> Union[dict, None]:
    global settings
    return settings.get(setting_name, None).get("value", None)


def getRefreshValue(setting_name: str) -> Union[dict, None]:
    loadSetting()  # Ensure to get the latest setting value, in case it was save in the meantime.
    return getValue(setting_name)


def set(setting_name: str, setting_value: Union[str, bool, int, float]) -> Union[dict, None]:
    if setting_name in settings:
        settings[setting_name]['value'] = setting_value
        saveSettings()
        return settings[setting_name]
    return None


loadSetting()
