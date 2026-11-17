from flask import Blueprint, jsonify, request

from application.controllers.instance import token_required
import application.models.baselines as baselineModel
import application.models.baselineDrift as baselineDrift
import application.models.baselineLibrary as baselineLibrary
import application.models.baselineReference as baselineReference
import application.models.baselineRemediation as baselineRemediation
import application.models.jobs as jobModel

BPbaselines = Blueprint('baselines', __name__)


def errorResponse(error: baselineModel.BaselineError):
    return jsonify(error.toDict()), error.status


def jsonBody() -> dict:
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise baselineModel.BaselineError('The body must be a JSON object')
    return body


@BPbaselines.route('/baselines/types', methods=['GET'])
@token_required
def types(user):
    """Rule types, their comparators and value kinds, severities, and the server-specific settings"""
    return jsonify(baselineModel.ruleTypes())


@BPbaselines.route('/baselines/fleet/<int:fleet_id>', methods=['GET'])
@token_required
def view(user, fleet_id):
    """The fleet's baseline and its rules. A fleet without a baseline has no rules and no ID"""
    try:
        return jsonify(baselineModel.getForUser(user, fleet_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>', methods=['DELETE'])
@token_required
def deleteBaseline(user, fleet_id):
    """Removes the fleet's baseline with all its rules"""
    try:
        return jsonify(baselineModel.deleteRules(user, fleet_id, None))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/rules', methods=['POST'])
@token_required
def addRules(user, fleet_id):
    """`{rules: [{type, key, expected, comparator?, severity?, note?, label?, force?}], on_conflict?}`. All rules
    are added or none: invalid ones are listed in `errors` with their index. `on_conflict` decides for rules already
    in the baseline: `error` (409, default), `skip` or `replace`"""
    try:
        body = jsonBody()
        return jsonify(baselineModel.addRules(user, fleet_id, body.get('rules'),
                                              body.get('on_conflict') or 'error')), 201
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/rules/delete', methods=['POST'])
@token_required
def deleteRules(user, fleet_id):
    """`{rule_ids: [...]}`"""
    try:
        body = jsonBody()
        if 'rule_ids' not in body:
            raise baselineModel.BaselineError('`rule_ids` is required', field='rule_ids')
        return jsonify(baselineModel.deleteRules(user, fleet_id, body['rule_ids']))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/copy', methods=['POST'])
@token_required
def copy(user, fleet_id):
    """`{from_fleet_id | from_saved_id | from_preset, mode?}`: `replace` (default) makes the rules identical to the
    source's, `merge` adds them, overwriting rules with the same type and key. The rules are validated against this
    fleet, all or none"""
    try:
        return jsonify(baselineLibrary.copyForUser(user, fleet_id, jsonBody()))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/copy/preview', methods=['POST'])
@token_required
def copyPreview(user, fleet_id):
    """Same body as the copy: the rules it would add, replace (with the current ones) and remove, and how many stay
    as they are. Nothing is changed"""
    try:
        return jsonify(baselineLibrary.previewCopyForUser(user, fleet_id, jsonBody()))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/drift', methods=['GET'])
@token_required
def drift(user, fleet_id):
    """Every rule against every server of the fleet: `servers[].results` maps a rule ID to `{state, actual,
    reason}`, `state` being `match`, `drift` or `unknown`. Results of a server that cannot be reached are `unknown`
    (and `stale`), with its last known values"""
    try:
        return jsonify(baselineDrift.driftForUser(user, fleet_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/check', methods=['POST'])
@token_required
def check(user, fleet_id):
    """Lists again, in the background, the taxonomies, galaxies and object templates the rules need on every server
    of the fleet (settings and versions come with the usual refresh). Answers 202 with the servers checked"""
    try:
        return jsonify(baselineDrift.checkFleet(user, fleet_id)), 202
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/remediation/preview', methods=['POST'])
@token_required
def remediationPreview(user, fleet_id):
    """What fixing the drift would change: `{server_ids?, rule_ids?}` narrows the scope (the whole fleet otherwise),
    `{items: [{server_id, rule_id}]}` names exact cells. Per server, each drifting rule with its `current` and
    `expected` values and an `action`: `apply`, or `manual` with the `reason`. Unreachable servers are `excluded`"""
    try:
        body = jsonBody()
        return jsonify(baselineRemediation.previewForUser(user, fleet_id, body.get('server_ids'),
                                                          body.get('rule_ids'), body.get('items')))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/fleet/<int:fleet_id>/remediation', methods=['POST'])
@token_required
def remediate(user, fleet_id):
    """`{items: [{server_id, rule_id}]}`, or `{server_ids, rule_ids}` (the servers and rules a preview listed): starts a
    job fixing those that still drift and can be fixed from here. Answers 202 with the job, 409 when nothing is left
    to fix"""
    try:
        body = jsonBody()
        job = baselineRemediation.startForUser(user, fleet_id, body.get('items'), body.get('server_ids'),
                                               body.get('rule_ids'))
        return jsonify({'job_id': job.id, 'job': jobModel.serializeJob(job, withResults=True)}), 202
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/reference/<int:server_id>', methods=['GET'])
@token_required
def reference(user, server_id):
    """What one of the user's servers could give a baseline: `settings` from its last refresh (secrets left out),
    and `content` (taxonomies, galaxies, object templates by rule type) listed from MISP now. A server that cannot be
    reached gives what it listed last (`source: snapshot`) or the reason"""
    try:
        return jsonify(baselineReference.referenceForUser(user, server_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/rules/<int:rule_id>', methods=['PUT'])
@token_required
def updateRule(user, rule_id):
    """Changes `expected`, `comparator`, `severity`, `note`, `label` or `force`; the type and key are fixed. The rule
    is a fleet's or a saved baseline's"""
    try:
        return jsonify(baselineModel.updateRule(user, rule_id, jsonBody()))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/rules/<int:rule_id>', methods=['DELETE'])
@token_required
def deleteRule(user, rule_id):
    try:
        baselineModel.deleteRule(user, rule_id)
    except baselineModel.BaselineError as e:
        return errorResponse(e)
    return jsonify({'id': rule_id})


# Saved baselines and presets

@BPbaselines.route('/baselines/library', methods=['GET'])
@token_required
def library(user):
    """The user's saved baselines and the presets, without their rules: `rule_count` and `types` ({type: count})"""
    return jsonify(baselineLibrary.libraryForUser(user))


@BPbaselines.route('/baselines/presets/<preset_id>', methods=['GET'])
@token_required
def viewPreset(user, preset_id):
    try:
        return jsonify(baselineLibrary.presetForUser(user, preset_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/saved', methods=['POST'])
@token_required
def createSaved(user):
    """`{name, description?, from_fleet_id}` keeps a copy of a fleet's rules; `{name, description?, rules,
    server_id?}` keeps rules picked on a reference server; `{name, description?}` alone starts an empty one. A name
    already used is a 409 (`name_taken`)"""
    try:
        return jsonify(baselineLibrary.createSaved(user, jsonBody())), 201
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/saved/<int:saved_id>', methods=['GET'])
@token_required
def viewSaved(user, saved_id):
    try:
        return jsonify(baselineLibrary.savedForUser(user, saved_id))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/saved/<int:saved_id>/rules', methods=['POST'])
@token_required
def addSavedRules(user, saved_id):
    """`{rules, on_conflict?}`, as for a fleet's baseline. Setting values take the types the user's servers report"""
    try:
        body = jsonBody()
        return jsonify(baselineLibrary.addSavedRules(user, saved_id, body.get('rules'),
                                                     body.get('on_conflict') or 'error')), 201
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/saved/<int:saved_id>', methods=['PUT'])
@token_required
def updateSaved(user, saved_id):
    """`{name?, description?, from_fleet_id?}`: renames, describes, or replaces its rules with a fleet's"""
    try:
        return jsonify(baselineLibrary.updateSaved(user, saved_id, jsonBody()))
    except baselineModel.BaselineError as e:
        return errorResponse(e)


@BPbaselines.route('/baselines/saved/<int:saved_id>', methods=['DELETE'])
@token_required
def deleteSaved(user, saved_id):
    try:
        baselineLibrary.deleteSaved(user, saved_id)
    except baselineModel.BaselineError as e:
        return errorResponse(e)
    return jsonify({'id': saved_id})
