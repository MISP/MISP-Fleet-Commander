from flask import Blueprint, request, jsonify, send_file
# from flask import current_app as app
from application.marshmallowSchemas import pinlistSchema, pinlistsSchema, pinlistEntriesSchema
from application.controllers.instance import token_required
import application.models.pinlists as pinlistsModel
import application.models.pinlistEntries as pinlistsEntriesModel
from application.models.utils import AvatarGenerator


BPpinLists = Blueprint('pinLists', __name__)

@BPpinLists.route('/pinlists/index', methods=['GET'])
@token_required
def index(user):
    """Get all pinned entries for the user"""
    entries = pinlistsModel.indexForUser(user)
    return pinlistsSchema.dump(entries)


@BPpinLists.route('/pinlists/add', methods=['POST'])
@token_required
def add(user):
    """Add an pinned entry for the user"""
    entry = pinlistsModel.addForUser(user, request.json)
    if entry is not None:
        return pinlistSchema.dump(entry)
    return jsonify({'error': 'Could not add entry. Similar entry already exists'})


@BPpinLists.route('/pinlists/delete/<int:entry_id>', methods=['DELETE', 'POST'])
@token_required
def delete(user, entry_id):
    """Delete a pinned entry"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        entry = pinlistsModel.delete(entry)
        return jsonify([entry_id])
    else:
        return jsonify({})


@BPpinLists.route('/pinlists/getAvatar/<int:entry_id>.png', methods=['GET'])
def getAvatar(entry_id):
    """Return the avatar of the pinned entry"""
    entry = pinlistsModel.get(entry_id)
    if entry is not None:
        avatarGenerator = AvatarGenerator(entry.uuid)
        fullPath = avatarGenerator.getPath()
        try:
            return send_file(fullPath)
        except FileNotFoundError:
            return "Not found", 404
    else:
        return "Not found", 404


@BPpinLists.route('/pinlists/getEntriesOnServer/<int:entry_id>', methods=['GET'])
@token_required
def getEntriesOnServer(user, server_id):
    """Return all entries linked to the pinned entry existing on the server"""
    entries = pinlistsEntriesModel.getEntriesOnServerForUser(user.id, server_id)
    return pinlistEntriesSchema.dump(entries)


@BPpinLists.route('/pinlists/getAllEntries', methods=['GET'])
@token_required
def getAllEntries(user):
    """Return all entries"""
    entries = pinlistsEntriesModel.getAllForUser(user.id)
    return pinlistEntriesSchema.dump(entries)


@BPpinLists.route('/pinlists/getAllEntriesFromServer/<int:server_id>', methods=['GET'])
@token_required
def getAllEntriesFromServer(user, server_id):
    """Return all entries for the provided server"""
    entries = pinlistsEntriesModel.getAllEntriesFromServerForUser(user.id, server_id)
    return pinlistEntriesSchema.dump(entries)


@BPpinLists.route('/pinlists/getEntriesFromPinned/<int:entry_id>', methods=['GET'])
@token_required
def getEntriesFromPinned(user, entry_id):
    """Return all entries linked to the pinned entry"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        entries = pinlistsEntriesModel.getEntriesFromPinned(entry.id)
        return pinlistEntriesSchema.dump(entries)
    else:
        return jsonify([])


@BPpinLists.route('/pinlists/deleteFromServer/<int:server_id>/<int:entry_id>', methods=['DELETE', 'POST'])
@token_required
def deleteFromServer(user, server_id, entry_id):
    """Delete the data associated with the pin entry on all servers"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        result = pinlistsModel.deleteFromServer(server_id, entry)
        return jsonify(result)
    else:
        return jsonify({})


@BPpinLists.route('/pinlists/deleteFromServers/<int:fleet_id>/<int:entry_id>', methods=['DELETE', 'POST'])
@token_required
def deleteFromServers(user, fleet_id, entry_id):
    """Delete the data associated with the pin entry on all servers"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        result = pinlistsModel.deleteFromServers(fleet_id, entry)
        return jsonify(result)
    else:
        return jsonify({})


@BPpinLists.route('/pinlists/refreshAllServers/<int:fleet_id>/<int:entry_id>', methods=['POST'])
@token_required
def refreshAllServers(user, fleet_id, entry_id):
    """Collect the data associated with that entry on all servers"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        pinlistsModel.refreshAllServers(fleet_id, entry)
    return jsonify({})


@BPpinLists.route('/pinlists/refreshServerEntry/<int:server_id>/<int:entry_id>', methods=['POST'])
@token_required
def refreshServerEntry(user, server_id, entry_id):
    """Collect the data associated with that entry on all servers"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        pinlistsModel.refreshServerEntry(server_id, entry)
    return jsonify({})



@BPpinLists.route('/pinlists/publishEventOnServer/<int:server_id>/<int:entry_id>', methods=['POST'])
@token_required
def publishEventOnServer(user, server_id, entry_id):
    """Collect the data associated with that entry on all servers"""
    entry = pinlistsModel.getForUser(user, entry_id)
    if entry is not None:
        pinlistsModel.publishEventOnServer(server_id, entry)
    return jsonify({})

