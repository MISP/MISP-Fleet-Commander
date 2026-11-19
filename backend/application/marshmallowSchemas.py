#!/usr/bin/env python3

import json
from pprint import pprint
from marshmallow import EXCLUDE, INCLUDE, RAISE, Schema, ValidationError, fields, post_dump, pre_load, validates_schema
from marshmallow_sqlalchemy import ModelConversionError, SQLAlchemyAutoSchema, fields as mafields
from sqlalchemy import event
from sqlalchemy.orm import mapper

from application import db
from application.DBModels import Server, Fleet, User, PinList, PinListEntry, UserSettings
from application.baseModel import BaseModel


class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        sqla_session = db.session
        include_relationships = True
        load_instance = True


class UserSchema(BaseSchema):

    hashed_password = fields.Str(load_only=True)
    password = fields.Str(load_only=True)
    # API keys are only shown once, in the response that generates them, and only their hash is stored
    has_apikey = fields.Boolean(dump_only=True)
    is_admin = fields.Boolean(dump_only=True)
    # user_settings = mafields.Nested(lambda: UserSettingSchema(), many=True, dump_only=True)
    user_settings = mafields.Nested(lambda: UserSettingSchema(), many=True, dump_only=True)

    class Meta(BaseSchema.Meta):
        include_relationships = False
        model = User
        exclude = ('apikey_hash', )
        unknown = EXCLUDE


class UserSettingSchema(BaseSchema):

    _value = fields.Str(load_only=True)
    # value = fields.Str()
    value = fields.Method("json_or_string")

    def json_or_string(self, obj):
        if obj.name in UserSettings.settings_to_json:
            return obj.value
        else:
            return str(obj.value)
    class Meta(BaseSchema.Meta):
        include_relationships = True
        model = UserSettings
        unknown = EXCLUDE


class FleetSchema(BaseSchema):

    server_count = fields.Integer(dump_only=True)
    servers = mafields.Nested(lambda: ServerSchema(exclude=('fleet', 'server_info', )), many=True, dump_only=True)
    watched_timestamp = fields.Integer(dump_only=True)
    monitored_timestamp = fields.Integer(dump_only=True)

    class Meta(BaseSchema.Meta):
        model = Fleet
        unknown = EXCLUDE


def existOrNone(data):
    return

def authkeyHint(authkey):
    """Masked form of an authkey that is safe to show: only its last 4 characters"""
    if not authkey:
        return None
    return f"••••{authkey[-4:]}"


class ServerSchema(BaseSchema):

    # The authkey never leaves the backend; clients only get a masked hint
    authkey = fields.Str(load_only=True, allow_none=True)
    authkey_hint = fields.Function(lambda server: authkeyHint(server.authkey), dump_only=True)
    has_authkey = fields.Function(lambda server: bool(server.authkey), dump_only=True)
    fleet = mafields.Nested(lambda: FleetSchema(exclude=('servers', )), many=False)
    # server_info = mafields.Nested(lambda: ServerQuerySchema, many=False)
    server_info = fields.Nested(lambda: ServerQuerySchema, validate=existOrNone, load_default=None)
    connection_status = fields.Dict(dump_only=True, allow_none=True)
    watched_timestamp = fields.Integer(dump_only=True)

    class Meta(BaseSchema.Meta):
        model = Server
        exclude = ('authkey_enc', )
        unknown = INCLUDE


# What lists of servers show (fleet table, Strategic View, Connections page). A full snapshot is several hundred KB
# per server, mostly MISP's settings and diagnostics, which only the server page shows: it asks for them on its own
# (`/servers/queryInfo/<id>`). Lists keep the API user, usage, sync connections, the status parts of the diagnostics
# and the two settings they read.
LIGHT_SNAPSHOT_SECTIONS = ('serverUser', 'serverUsage', 'connectedServers')
LIGHT_SERVER_SETTINGS = ('version', 'proxyStatus', 'zmqStatus', 'moduleStatus', 'workers', 'backgroundJobsStatus',
                         '_latency', '_status_code', 'error', 'message', 'name')
LIGHT_FINAL_SETTINGS = ('MISP.uuid', 'MISP.background_jobs')


def lightServerInfo(info):
    """A snapshot (`{timestamp, query_result}`, other keys kept) reduced to what lists show, flagged `light`"""
    if not isinstance(info, dict) or not isinstance(info.get('query_result'), dict):
        return info
    result = info['query_result']
    light = {key: result[key] for key in LIGHT_SNAPSHOT_SECTIONS if key in result}
    settings = result.get('serverSettings')
    if isinstance(settings, dict):
        light['serverSettings'] = {key: settings[key] for key in LIGHT_SERVER_SETTINGS if key in settings}
        if isinstance(settings.get('finalSettings'), list):
            light['serverSettings']['finalSettings'] = [
                entry for entry in settings['finalSettings']
                if isinstance(entry, dict) and entry.get('setting') in LIGHT_FINAL_SETTINGS]
    elif 'serverSettings' in result:
        light['serverSettings'] = settings
    return dict(info, query_result=light, light=True)


class ServerListSchema(ServerSchema):
    """A server with its snapshot reduced to what lists show (see `lightServerInfo`)"""

    @post_dump
    def lighten_server_info(self, server, **kwargs):
        server['server_info'] = lightServerInfo(server.get('server_info'))
        return server


class PinlistSchema(BaseSchema):

    class Meta(BaseSchema.Meta):
        model = PinList
        unknown = EXCLUDE


class PinlistEntrySchema(BaseSchema):

    server_id = fields.Integer()
    pinlist_id = fields.Integer()

    class Meta(BaseSchema.Meta):
        model = PinListEntry
        unknown = EXCLUDE


class ServerQuerySchema(Schema):
    timestamp = fields.Integer()
    query_result = fields.Dict()


class PluginSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    filename = fields.Str()
    icon = fields.Str()
    description = fields.Str()
    features = fields.Dict()
    action_parameters = fields.List(fields.Dict())
    quickActionMeta = fields.Dict()


class TaskSchema(Schema):
    id = fields.UUID()
    status = fields.Str()
    message = fields.Str()


serverSchema = ServerSchema()
serversSchema = ServerSchema(many=True)

serversListSchema = ServerListSchema(many=True)
# A server named by an event or a search result: its snapshot travels on its own, if at all
serverSchemaWithoutInfo = ServerSchema(exclude=('server_info', ))
serversSchemaWithoutInfo = ServerSchema(exclude=('server_info', ), many=True)

userSchema = UserSchema()
usersSchema = UserSchema(many=True)

userSettingSchema = UserSettingSchema()
userSettingsSchema = UserSettingSchema(many=True)

serverQuerySchema = ServerQuerySchema()
serverQuerysSchema = ServerQuerySchema(many=True)

fleetSchema = FleetSchema()
fleetsSchema = FleetSchema(many=True)

pinlistSchema = PinlistSchema()
pinlistsSchema = PinlistSchema(many=True)

pinlistEntrySchema = PinlistEntrySchema()
pinlistEntriesSchema = PinlistEntrySchema(many=True)

pluginSchema = PluginSchema()
pluginsSchema = PluginSchema(many=True)

taskSchema = TaskSchema()
tasksSchema = TaskSchema(many=True)
