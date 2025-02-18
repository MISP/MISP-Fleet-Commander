#!/usr/bin/env python3

import json
import os
from typing import List, Union
from pathlib import Path

from application import MONITORING_SYSTEM_AVAILABLE


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
        "description": "If the monitoring system is started and functionnal, should the monitoring system be enabled.",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "checkbox",
        "default": False,
        "disabled": False,
        "error": False,
    },
    "monitoring_interval": {
        "name": "Monitoring Interval",
        "description": "The frequency (minute) at which the monitoring system collect metrics",
        "panel": "Scheduler",
        "scope": "Monitoring System",
        "type": "number",
        "default": 10,
        "min": 1,
        "disabled": True,
        "error": {
            "error_message": "The frequency cannot be configured at the moment.",
            "variant": "info",
        },
    },
}

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

    if not MONITORING_SYSTEM_AVAILABLE:
        settings["monitoring_enabled"]["value"] = False
        settings['monitoring_enabled']['disabled'] = True
        settings["monitoring_enabled"]["error"] = {
            "error_message": "Monitoring system is disabled due to missing libraries.",
            "variant": "warning",
        }

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
