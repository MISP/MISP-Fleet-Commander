from flask import Blueprint, jsonify, request
# from flask import current_app as app
from application.controllers.instance import token_required
import application.models.servers as serverModel


BPserverManagement = Blueprint('serverManagement', __name__)


def runOperation(user, server_id, operation, title, failureMessage, user_id=None, payload=None):
    """Run a user administration operation on one MISP server, recorded as a one-server job. Answers MISP's
    result, or `{"error": …}`"""
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'error': failureMessage})
    params = {'operation': operation}
    if user_id is not None:
        params['user_id'] = user_id
    if payload is not None:
        params['payload'] = payload
    unit = jobRunner.runInline(user, 'server_management', server, params, title=f'{title} on {server.name}',
                               emitter=socketEmitter)
    if not unit.ok:
        return jsonify({'error': unit.summary or failureMessage})
    return jsonify(unit.response)


@BPserverManagement.route('/server-management/user/add-options/<int:server_id>', methods=['GET'])
@token_required
def addUserOptions(user, server_id):
    """The organisations and roles of the MISP instance, to choose from when adding a user"""
    import application.models.serverManagement as serverManagementModel
    server = serverModel.getForUser(user, server_id)
    if server is None:
        return jsonify({'message': 'Unknown server'}), 404
    try:
        return jsonify(serverManagementModel.addUserOptions(server))
    except serverManagementModel.MISPListError as e:
        return jsonify({'message': f'Could not list the organisations and roles of {server.name}: {e}'}), 502


@BPserverManagement.route('/server-management/user/add/<int:server_id>', methods=['POST'])
@token_required
def addUser(user, server_id):
    """Create a user on the MISP instance"""
    payload = request.json or {}
    email = payload.get('email') if isinstance(payload, dict) else None
    return runOperation(user, server_id, 'add_user', f'Add user {email}' if email else 'Add user',
                        'Could not create user.', payload=payload)


@BPserverManagement.route('/server-management/user/set-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def setPassword(user, server_id, user_id):
    """Set the password of a user on the MISP instance"""
    return runOperation(user, server_id, 'set_password', f'Set the password of user #{user_id}',
                        'Could not set password for user.', user_id=user_id, payload=request.json or {})


@BPserverManagement.route('/server-management/user/reset-password/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def resetPassword(user, server_id, user_id):
    """Reset password for a user on the MISP instance"""
    return runOperation(user, server_id, 'reset_password', f'Reset the password of user #{user_id}',
                        'Could not reset password user.', user_id=user_id)


@BPserverManagement.route('/server-management/user/gen-authkey/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def genAuthkey(user, server_id, user_id):
    """Generate an authkey for a user on the MISP instance"""
    return runOperation(user, server_id, 'gen_authkey', f'Generate an authkey for user #{user_id}',
                        'Could not generate authkey for user.', user_id=user_id)


@BPserverManagement.route('/server-management/user/disable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def disable(user, server_id, user_id):
    """Disable a user on the MISP instance"""
    return runOperation(user, server_id, 'disable', f'Disable user #{user_id}', 'Could not disable user.',
                        user_id=user_id)


@BPserverManagement.route('/server-management/user/enable/<int:server_id>/<int:user_id>', methods=['POST'])
@token_required
def enable(user, server_id, user_id):
    """Enable a user on the MISP instance"""
    return runOperation(user, server_id, 'enable', f'Enable user #{user_id}', 'Could not enable user.',
                        user_id=user_id)


# Organisations

def organisationError(e):
    body = {'message': e.message}
    if getattr(e, 'field', None):
        body['field'] = e.field
    return jsonify(body), e.status


def ownedServerOr404(user, server_id):
    server = serverModel.getForUser(user, server_id)
    if server is None:
        import application.models.organisations as organisationModel
        raise organisationModel.OrganisationError('Unknown server', 404)
    return server


def wantsRefresh() -> bool:
    return request.args.get('refresh', '').lower() in ('1', 'true', 'yes')


@BPserverManagement.route('/server-management/organisations/<int:server_id>', methods=['GET'])
@token_required
def organisationIndex(user, server_id):
    """The organisations of the MISP instance, kept 10 minutes (`?refresh=1` lists them again):
    `{server_id, fetched_at, cached, organisations}`"""
    import application.models.mispOps as mispOps
    import application.models.organisations as organisationModel
    try:
        server = ownedServerOr404(user, server_id)
        return jsonify({'server_id': server.id, **organisationModel.organisationsOf(server, refresh=wantsRefresh())})
    except organisationModel.OrganisationError as e:
        return organisationError(e)
    except mispOps.MispOpError as e:
        return jsonify({'message': e.message}), 502


@BPserverManagement.route('/server-management/organisations/<int:server_id>/fleet', methods=['GET'])
@token_required
def organisationFleet(user, server_id):
    """How the server's organisations compare with the other servers of its fleet, by UUID: `{compared,
    unavailable, organisations: {uuid: {same, renamed, other_uuid}}}`"""
    import application.models.mispOps as mispOps
    import application.models.organisations as organisationModel
    try:
        server = ownedServerOr404(user, server_id)
        return jsonify(organisationModel.fleetComparison(server, refresh=wantsRefresh()))
    except organisationModel.OrganisationError as e:
        return organisationError(e)
    except mispOps.MispOpError as e:
        return jsonify({'message': e.message}), 502


def runOrganisationOperation(user, server, operation, title, params):
    """A one-server job: the saved organisation (`{"Organisation": …}`), 502 with MISP's reason otherwise"""
    from application.controllers.websocket import socketEmitter
    import application.models.jobRunner as jobRunner
    unit = jobRunner.runInline(user, 'server_management', server, {'operation': operation, **params},
                               title=f'{title} on {server.name}', emitter=socketEmitter)
    if not unit.ok:
        return jsonify({'message': unit.summary or 'MISP refused the change'}), 502
    return jsonify(unit.response)


@BPserverManagement.route('/server-management/organisations/<int:server_id>/add', methods=['POST'])
@token_required
def organisationAdd(user, server_id):
    """Create an organisation on the MISP instance: `{name, uuid?, local?, type?, nationality?, sector?,
    description?, contacts?, restricted_to_domain?}`"""
    import application.models.organisations as organisationModel
    try:
        server = ownedServerOr404(user, server_id)
        fields = organisationModel.cleanFields(request.get_json(silent=True))
    except organisationModel.OrganisationError as e:
        return organisationError(e)
    return runOrganisationOperation(user, server, 'add_organisation', f"Add organisation {fields['name']}",
                                    {'payload': fields})


@BPserverManagement.route('/server-management/organisations/<int:server_id>/edit/<int:org_id>', methods=['POST'])
@token_required
def organisationEdit(user, server_id, org_id):
    """Change an organisation of the MISP instance: only the fields given"""
    import application.models.organisations as organisationModel
    try:
        server = ownedServerOr404(user, server_id)
        changes = organisationModel.cleanFields(request.get_json(silent=True), partial=True)
    except organisationModel.OrganisationError as e:
        return organisationError(e)
    return runOrganisationOperation(user, server, 'edit_organisation', f'Edit organisation #{org_id}',
                                    {'org_id': org_id, 'payload': changes})


@BPserverManagement.route('/server-management/organisations/<int:server_id>/copy', methods=['POST'])
@token_required
def organisationCopy(user, server_id):
    """Create one of the server's organisations, with its UUID, on other servers of its fleet: `{uuid, server_ids,
    local?}`. Answers 202 with the job"""
    import application.models.jobs as jobModel
    import application.models.mispOps as mispOps
    import application.models.organisations as organisationModel
    import application.models.userJobs as userJobs
    try:
        server = ownedServerOr404(user, server_id)
        job = organisationModel.startCopy(user, server, request.get_json(silent=True))
    except organisationModel.OrganisationError as e:
        return organisationError(e)
    except userJobs.JobError as e:
        return jsonify({'message': e.message}), e.status
    except mispOps.MispOpError as e:
        return jsonify({'message': e.message}), 502
    return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True)}), 202
