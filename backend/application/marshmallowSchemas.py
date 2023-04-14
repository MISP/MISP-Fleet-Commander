#!/usr/bin/env python3

from pprint import pprint
from marshmallow import EXCLUDE, INCLUDE, RAISE, Schema, ValidationError, fields, pre_load, validates_schema
from marshmallow_sqlalchemy import ModelConversionError, SQLAlchemyAutoSchema, fields as mafields
from sqlalchemy import event
from sqlalchemy.orm import mapper

from application import db
from application.DBModels import Server, ServerGroup, User
from application.baseModel import BaseModel



class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        sqla_session = db.session
        include_relationships = True
        load_instance = True


class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = User


class ServerGroupSchema(BaseSchema):

    server_count = fields.Integer(dump_only=True)
    servers = mafields.Nested(lambda: ServerSchema(exclude=('server_group', 'server_info', )), many=True, dump_only=True)

    class Meta(BaseSchema.Meta):
        model = ServerGroup
        unknown = EXCLUDE


class ServerSchema(BaseSchema):

    server_group = mafields.Nested(lambda: ServerGroupSchema(exclude=('servers', )), many=False)
    # server_info = mafields.Nested(lambda: ServerQuerySchema, many=False)
    server_info = fields.Nested(lambda: ServerQuerySchema)

    class Meta(BaseSchema.Meta):
        model = Server
        unknown = INCLUDE


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


class TaskSchema(Schema):
    id = fields.UUID()
    status = fields.Str()
    message = fields.Str()


serverSchema = ServerSchema()
serversSchema = ServerSchema(many=True)

userSchema = UserSchema()
usersSchema = UserSchema(many=True)

serverQuerySchema = ServerQuerySchema()
serverQuerysSchema = ServerQuerySchema(many=True)

serverGroupSchema = ServerGroupSchema()
serverGroupsSchema = ServerGroupSchema(many=True)

pluginSchema = PluginSchema()
pluginsSchema = PluginSchema(many=True)

taskSchema = TaskSchema()
tasksSchema = TaskSchema(many=True)