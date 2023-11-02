#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import db, PinList, PinListEntry
import application.models.servers as serverModel
import application.models.pinlistEntries as pinlistEntryModel
from application.controllers.utils import batchRequest, mispGetRequest, mispPostRequest
from application.models.utils import AvatarGenerator


def index() -> List[PinList]:
    q = PinList.query.all()
    lists = q.all()
    return lists

def indexForUser(user) -> List[PinList]:
    q = PinList.query
    q = q.filter_by(user_id=user.id)
    lists = q.all()
    return lists

def get(entry_id: int) -> Union[PinList, None]:
    q = PinList.query
    q = q.filter_by(id=entry_id)
    entry = q.first()
    return entry

def getForUser(user, entry_id: int) -> Union[PinList, None]:
    q = PinList.query
    q = q.filter_by(user_id=user.id, id=entry_id)
    entry = q.first()
    return entry

def addForUser(user, data):
    existingEntry = PinList.query.filter_by(model=data.get('model'), uuid=data.get('uuid')).first()
    if existingEntry is not None:
        return None
    entry = PinList(model=data.get('model'),
                    uuid=data.get('uuid'),
                    user_id=user.id)
    db.session.add(entry)
    success = True
    try:
        db.session.commit()
    except Exception as e:
        success = False
        db.session.rollback()
        db.session.flush()
    if success:
        avatarGenerator = AvatarGenerator(entry.uuid)
        avatarGenerator.generate()
    return entry

def delete(entry: PinList):
    db.session.delete(entry)
    db.session.commit()
    avatarGenerator = AvatarGenerator(entry.uuid)
    avatarGenerator.delete()

def deleteFromServers(group_id: int, entry: PinList):
    servers = serverModel.index(group_id)
    allRequests = []
    uuidToDelete = entry.uuid
    if servers:
        for server in servers:
            allRequests.append({
                'fn': mispPostRequest,
                'server': server,
                'path': f'/events/delete/{uuidToDelete}',
                'data': {}
            })
        allDeletion = batchRequest(allRequests)
        return allDeletion
    return []

def refreshAllServers(group_id: int, entry: PinList):
    servers = serverModel.index(group_id)
    allRequests = []
    url = __genURLFromModel(entry)
    if servers and url is not None:
        for server in servers:
            allRequests.append({
                'fn': mispGetRequest,
                'server': server,
                'path': url,
                'passAlong': {'server_id': server.id, 'pinlist_id': entry.id}
            })
        allRefresh = batchRequest(allRequests)
        __handleRefreshResults(allRefresh)

def __handleRefreshResults(allRefresh):
    for result in allRefresh:
        data = {
            'pinlist_id': result['_passAlong']['pinlist_id'],
            'server_id': result['_passAlong']['server_id'],
        }
        if result['_status_code'] == 404:
            pinlistEntryModel.deleteForPinlistServer(**data)
        elif result['_status_code'] == 200:
            filteredData = {key: value for key, value in result.items() if not key.startswith('_')}
            data['data'] = filteredData
            pinlistEntryModel.add(data)
            

def __genURLFromModel(entry: PinList) -> Union[str, None]:
    if entry.model == 'event':
        return f'/events/view/{entry.uuid}.json'
    elif entry.model == 'sharinggroup':
        return f'/sharingGroups/view/{entry.uuid}.json'
    return None