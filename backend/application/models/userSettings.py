#!/usr/bin/env python3

from typing import List, Union
from sqlalchemy.orm.attributes import flag_modified    

from application.DBModels import UserSettings
from application.DBModels import db

ALLOWED_SETTINGS = [
    'enabled_plugins',
]

def index() -> List[UserSettings]:
    q = UserSettings.query
    user_settings = q.all()
    return user_settings


def get(id: int) -> Union[UserSettings, None]:
    return UserSettings.query.get(id)


def getForUser(user_id: int) -> Union[UserSettings, None]:
    q = UserSettings.query
    q = q.filter_by(user_id=user_id)
    user_settings = q.first()
    return user_settings


def add(user_id: int, user_settings: dict) -> UserSettings:
    userSetting = UserSettings(user_id=user_id)
    userSetting.settings = {}
    for setting, value in user_settings.items():
        if setting in ALLOWED_SETTINGS:
            userSetting.settings[setting] = value
    db.session.add(userSetting)
    db.session.commit()
    return userSetting


def editForUser(user_id: int, user_settings: dict) -> Union[UserSettings, None]:
    oldUserSettings = getForUser(user_id)
    if oldUserSettings is not None:
        newSettings = oldUserSettings.settings
        for setting, value in user_settings.items():
            if setting in ALLOWED_SETTINGS:
                newSettings[setting] = value
        oldUserSettings.settings = newSettings
        flag_modified(oldUserSettings, 'settings')
        db.session.commit()
        return oldUserSettings
    else:
        return add(user_id, user_settings)


def edit(id: int, user_settings: dict) -> Union[UserSettings, None]:
    oldUserSettings = get(id)
    if oldUserSettings is not None:
        for setting, value in user_settings.items():
            if setting in ALLOWED_SETTINGS:
                oldUserSettings.settings[setting] = value
        flag_modified(oldUserSettings, 'settings')
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
