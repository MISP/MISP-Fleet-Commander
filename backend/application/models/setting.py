#!/usr/bin/env python3

import json
import os
from typing import List, Union
from pathlib import Path

from application.DBModels import User
from application.DBModels import db
from application.marshmallowSchemas import userSchema
import application.models.userSettings as userSettingsModel

from application.models.auth import create_API_key


current_path = Path(__file__).resolve().parent
setting_path = current_path / "../../config.json"
setting_path = setting_path.resolve()
settings = {}
setting_configuration = {
    "monitoring_enabled": {
        "name": "Monitoring Enabled",
        "description": "If the monitoring system is started and functionnal, fleets marked to be monitored will be.",
        "scope": "monitoring",
        "type": "checkbox",
        "default": False,
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
