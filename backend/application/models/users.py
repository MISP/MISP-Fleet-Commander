#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import User
from application.DBModels import db
from application.marshmallowSchemas import userSchema

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
    return user


def edit(user: dict) -> Union[User, None]:
    oldUser = get(user['id'])
    if oldUser is not None:
        for field, value in user.items():
            if field in editFields:
                setattr(oldUser, field, value)
        db.session.commit()
        return oldUser
    return None


def delete(user_id: int) -> bool:
    user = get(user_id)
    if user is not None:
        db.session.delete(user)
        db.session.commit()
        return True
    return False