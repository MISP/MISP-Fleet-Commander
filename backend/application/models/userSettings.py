#!/usr/bin/env python3

from pathlib import Path
from typing import List, Union

from application.DBModels import UserSettings
from application.DBModels import db
from application import all_user_settings
from application import loadedPlugins

PLUGIN_SETTING_FULL_PATH = 'Plugins.enabled_plugins'
ALL_SETTINGS = all_user_settings
VALID_SETTING_NAMES = set()
for panel, panel_settings in ALL_SETTINGS.items():
    for user_setting in panel_settings:
        if 'name' in user_setting:

            if user_setting['name'] == 'enabled_plugins':
                user_setting['options'] = [{'text': plugin['name'], 'value': plugin['id']} for plugin in loadedPlugins]

            full_setting_name = f"{panel}.{user_setting['name']}"
            user_setting['full_setting_name'] = full_setting_name
            VALID_SETTING_NAMES.add(full_setting_name)
VALID_SETTING_NAMES = list(VALID_SETTING_NAMES)


def index() -> List[UserSettings]:
    q = UserSettings.query
    user_settings = q.all()
    return user_settings


def get(id: int) -> Union[UserSettings, None]:
    return UserSettings.query.get(id)


def getForUser(user_id: int, setting_name: str) -> Union[UserSettings, None]:
    q = UserSettings.query
    q = q.filter_by(user_id=user_id, name=setting_name)
    user_settings = q.first()
    return user_settings


def add(user_id: int, user_settings: dict) -> UserSettings:
    userSetting = UserSettings(user_id=user_id)
    userSetting.name = user_settings['name']
    userSetting.value = user_settings['value']
    if userSetting.name in VALID_SETTING_NAMES:
        db.session.add(userSetting)
        db.session.commit()
    return userSetting


def editForUser(user_id: int, user_settings: dict) -> Union[UserSettings, None]:
    setting_name = user_settings['name']
    if setting_name:
        oldUserSettings = getForUser(user_id, setting_name)
        if oldUserSettings is not None:
            oldUserSettings.value = user_settings['value']
            db.session.commit()
            return oldUserSettings
        else:
            return add(user_id, user_settings)


def edit(id: int, user_settings: dict) -> Union[UserSettings, None]:
    oldUserSettings = get(id)
    if oldUserSettings is not None:
        oldUserSettings.value = user_settings['value']
        db.session.commit()
        return oldUserSettings
    return None


def delete(id: int) -> bool:
    userSetting = get(id)
    if userSetting is not None:
        db.session.delete(userSetting)
        db.session.commit()
        return True
    return False


def getSettingConfig() -> dict:
    return {
        'all_settings': ALL_SETTINGS,
        'all_setting_names': VALID_SETTING_NAMES,
    }


def togglePlugin(user_id: int, plugin_name: str) -> Union[list[str], None]:
    plugin_settings = getForUser(user_id, PLUGIN_SETTING_FULL_PATH)
    if plugin_settings is not None:
        updated_value = plugin_settings.value
        if plugin_name in plugin_settings.value:
            updated_value.remove(plugin_name) # type: ignore
        else:
            updated_value.append(plugin_name) # type: ignore
        plugin_settings.value = updated_value
        db.session.commit()
    return plugin_settings.value # type: ignore
