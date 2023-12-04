#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import Fleet


def index() -> List[Fleet]:
    q = Fleet.query.all()
    fleets = q.all()
    return fleets

def indexForUser(user) -> List[Fleet]:
    q = Fleet.query
    q = q.filter_by(user_id=user.id)
    fleets = q.all()
    return fleets

def get(fleet_id: int) -> Union[Fleet, None]:
    return Fleet.query.get(fleet_id)

def getForUser(user, fleet_id: int) -> Union[Fleet, None]:
    q = Fleet.query
    q = q.filter_by(user_id=user.id, id=fleet_id)
    fleet = q.first()
    return fleet