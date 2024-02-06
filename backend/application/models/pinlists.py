#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import Server, db, PinList, PinListEntry
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

def deleteFromServer(server_id: int, entry: PinList):
    server = serverModel.get(server_id)
    url = __genDeleteURLFromModel(entry)
    if server and url is not None:
        deletion = mispPostRequest(server, url)
        __afterDeleteActions(entry, server)
        return deletion
    return []

def deleteFromServers(fleet_id: int, entry: PinList):
    servers = serverModel.index(fleet_id)
    allRequests = []
    url = __genDeleteURLFromModel(entry)
    if servers and url is not None:
        for server in servers:
            allRequests.append({
                'fn': mispPostRequest,
                'server': server,
                'path': url,
                'data': {}
            })
        allDeletion = batchRequest(allRequests)
        return allDeletion
    return []

def refreshAllServers(fleet_id: int, entry: PinList):
    servers = serverModel.index(fleet_id)
    allRequests = []
    url = __genViewURLFromModel(entry)
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

def refreshServerEntry(server_id: int, entry: PinList):
    server = serverModel.get(server_id)
    url = __genViewURLFromModel(entry)
    if server:
        refreshResult = mispGetRequest(server, url)
        refreshResult['_passAlong'] = {'pinlist_id': entry.id}
        refreshResult['_passAlong']['server_id'] = server.id
        __handleRefreshResults([refreshResult])

def publishEventOnServer(server_id: int, entry: PinList):
    server = serverModel.get(server_id)
    url = __genActionURLFromModel(entry, 'publish')
    if server is not None:
        result = mispPostRequest(server, url)
        return result

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
            

def __genViewURLFromModel(entry: PinList) -> Union[str, None]:
    if entry.model == 'event':
        return f'/events/view/{entry.uuid}.json'
    elif entry.model == 'attribute':
        return f'/attributes/view/{entry.uuid}.json'
    elif entry.model == 'sharinggroup':
        return f'/sharingGroups/view/{entry.uuid}.json'
    elif entry.model == 'sighting':
        return f'/sightings/view/{entry.uuid}.json'
    elif entry.model == 'analystdata':
        return f'/analyst_data/view/all/{entry.uuid}.json'
    return None

def __genDeleteURLFromModel(entry: PinList) -> Union[str, None]:
    if entry.model == 'event':
        return f'/events/delete/{entry.uuid}'
    elif entry.model == 'attribute':
        return f'/attributes/delete/{entry.uuid}/1'
    elif entry.model == 'sharinggroup':
        return f'/sharingGroups/delete/{entry.uuid}'
    elif entry.model == 'sighting':
        return f'/sightings/delete/{entry.uuid}'
    elif entry.model == 'analystdata':
        return f'/analyst_data/delete/all/{entry.uuid}'
    return None

def __genActionURLFromModel(entry: PinList, action: str) -> Union[str, None]:
    if entry.model == 'event':
        if action == 'publish':
            return f'/events/publish/{entry.uuid}'
    return None

def __afterDeleteActions(entry: PinList, server: Server) -> bool:
    if entry.model == 'event':
        url_blocklist = f'/event_blocklists/delete/{entry.uuid}'
        blocklist_deletion = mispPostRequest(server, url_blocklist)
        return True if blocklist_deletion else False
    elif entry.model == 'analystdata':
        url_blocklist = f'/analyst_data_blocklists/delete/{entry.uuid}'
        blocklist_deletion = mispPostRequest(server, url_blocklist)
        return True if blocklist_deletion else False
    return True