#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import db, PinListEntry, PinList
import application.models.servers as serverModel


def index() -> List[PinListEntry]:
    q = PinListEntry.query.all()
    lists = q.all()
    return lists

def get(entry_id: int) -> Union[PinListEntry, None]:
    q = PinListEntry.query
    q = q.filter_by(id=entry_id)
    entry = q.first()
    return entry

def add(data):
    existingEntry = PinListEntry.query.filter_by(pinlist_id=data.get('pinlist_id'), server_id=data.get('server_id')).first()
    if existingEntry is not None:
        return None
    entry = PinListEntry(pinlist_id=data.get('pinlist_id'),
                         server_id=data.get('server_id'),
                         data=data.get('data', {}))
    db.session.add(entry)
    db.session.commit()
    return entry

def getEntriesOnServerForUser(user_id: int, server_id: int) -> list:
    q = PinListEntry.query
    q = q.filter_by(user_id=user_id, server_id=server_id)
    entries = q.all()
    return entries

def getAllForUser(user_id: int) -> list:
    q = PinListEntry.query
    q = q.join(PinListEntry.pinlist.and_(PinList.user_id == user_id))
    entries = q.all()
    return entries

def getEntriesFromPinned(pinlist_id: int) -> list:
    q = PinListEntry.query
    q = q.filter_by(pinlist_id=pinlist_id)
    entries = q.all()
    return entries

def deleteForPinlistServer(server_id: int, pinlist_id: int):
    q = PinListEntry.query
    q = q.filter_by(server_id=server_id, pinlist_id=pinlist_id)
    entry = q.first()
    if entry is not None:
        delete(entry)

def delete(entry: PinListEntry):
    db.session.delete(entry)
    db.session.commit()
