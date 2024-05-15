#!/usr/bin/env python3

import json
from typing import List, Union

from application.DBModels import User
from application.DBModels import db
from application.marshmallowSchemas import userSchema
import application.models.userSettings as userSettingsModel

from application.models.auth import create_API_key

editFields = ['email', 'password']

def index() -> List[User]:
    q = User.query
    users = q.all()
    return users


def get(user_id: int) -> Union[User, None]:
    return User.query.get(user_id)


def getByEmail(email: str) -> Union[User, None]:
    return User.query.filter_by(email=email).first()


def add(user: dict) -> User:
    user = User(email=user['email'],
                password=user['password'])
    db.session.add(user)
    db.session.commit()
    if 'user_settings' in user and len(user['user_settings']) > 0:
        userSettingsModel.add(user.id, user['user_settings'])
    return user


def edit(user: dict) -> Union[User, None]:
    oldUser = get(user['id'])
    if oldUser is not None:
        for field, value in user.items():
            if field in editFields:
                setattr(oldUser, field, value)
        db.session.commit()
        if 'user_settings' in user:
            # try:
            #     user['user_settings'] = json.loads(user['user_settings'])
            # except ValueError:
            #     user['user_settings'] = {}
            if len(user['user_settings']) > 0:
                userSettingsModel.editForUser(user['id'], user['user_settings'])
        return oldUser
    return None


def delete(user_id: int) -> bool:
    user = get(user_id)
    if user is not None:
        db.session.delete(user)
        db.session.commit()
        return True
    return False


def createAPIKey(user_id: User) -> Union[str, None]:
    user = get(user_id)
    if user is not None:
        token = create_API_key()
        user.apikey = token
        db.session.add(user)
        db.session.commit()
        return token
    return None