#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import ServerGroup


def index() -> List[ServerGroup]:
    q = ServerGroup.query.all()
    groups = q.all()
    return groups

def indexForUser(user) -> List[ServerGroup]:
    q = ServerGroup.query
    q = q.filter_by(user_id=user.id)
    groups = q.all()
    return groups

def get(group_id: int) -> Union[ServerGroup, None]:
    return ServerGroup.query.get(group_id)

def getForUser(user, group_id: int) -> Union[ServerGroup, None]:
    q = ServerGroup.query
    q = q.filter_by(user_id=user.id, id=group_id)
    group = q.first()
    return group