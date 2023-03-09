#!/usr/bin/env python3

from marshmallow import Schema, fields
from marshmallow_sqlalchemy import ModelConversionError, SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.fields import Nested
from sqlalchemy import event
from sqlalchemy.orm import mapper

from application import db
from application.DBModels import Server, ServerGroup, ServerQuery, User
from application.baseModel import BaseModel


# Automatically Generating Schemas For SQLAlchemy Models
# https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models
# def setup_schema(Base):
#     # Create a function which incorporates the Base and session information
#     def setup_schema_fn():
#         for class_ in Base.registry._class_registry.values():
#             if hasattr(class_, "__tablename__"):
#                 if class_.__name__.endswith("Schema"):
#                     raise ModelConversionError(
#                         "For safety, setup_schema can not be used when a"
#                         "Model class ends with 'Schema'"
#                     )

#                 class Meta(BaseMeta):
#                     model = class_

#                 schema_class_name = "%sSchema" % class_.__name__


#                 ClassSchema = SQLAlchemyAutoSchema
#                 relationships = class_.__mapper__.relationships.keys()
#                 for key in relationships:
#                     is_list = class_.__mapper__.relationships[key].uselist
#                     # if is_list:
#                     #     setattr(ClassSchema, key, SmartNested())
#                     # else:
#                     #     pass

#                 schema_class = type(
#                     schema_class_name, (ClassSchema,), {"Meta": Meta}
#                 )

#                 setattr(class_, "__marshmallow__", schema_class)

#                 def makeDumpFn():  # Factory function that generates the dump function
#                     def dumpFn(self):
#                         return self.__marshmallow__().dump(self)
#                     return dumpFn
#                 setattr(class_, "dump", makeDumpFn())

#     return setup_schema_fn


# # Listen for the SQLAlchemy event and run setup_schema.
# # Note: This has to be done after Base and session are setup
# def setupListener():
#     event.listen(mapper, "after_configured", setup_schema(BaseModel))


# class BaseMeta:
#     sqla_session = db.Session
#     include_fk = True
#     load_instance = True # Optional: deserialize to model instances


# class SmartNested(Nested):
#     def serialize(self, attr, obj, accessor=None):
#         if attr not in obj.__dict__:
#             return {"id": int(getattr(obj, attr + "_id"))}
#         return super(SmartNested, self).serialize(attr, obj, accessor)

class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        sqla_session = db.Session
        include_relationships = True
        load_instance = True # Optional: deserialize to model instances


class UserSchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = User


class ServerGroupSchema(BaseSchema):
    server_count = fields.Integer()

    class Meta(BaseSchema.Meta):
        model = ServerGroup


class ServerQuerySchema(BaseSchema):
    class Meta(BaseSchema.Meta):
        model = ServerQuery


class ServerSchema(BaseSchema):
    server_group = Nested(ServerGroupSchema, many=False)
    server_info = Nested(ServerQuerySchema, many=False)

    auth_method = fields.Str()

    class Meta(BaseSchema.Meta):
        model = Server


class PluginSchema(Schema):
    id = fields.Str()
    name = fields.Str()
    filename = fields.Str()
    icon = fields.Str()
    description = fields.Str()
    features = fields.Dict()
    action_parameters = fields.List(fields.Dict())


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