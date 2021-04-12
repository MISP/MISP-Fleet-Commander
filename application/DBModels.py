from application import db
from datetime import datetime
import json
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from application.baseModel import BaseModel


class User(BaseModel):
    __tablename__ = 'users'
    id = db.Column(db.Integer,
                   primary_key=True)
    email = db.Column(db.String(80),
                      index=True,
                      unique=True,
                      nullable=False)
    created = db.Column(db.DateTime,
                        index=False,
                        unique=False,
                        nullable=False,
                        default=datetime.utcnow)
    password = db.Column(db.String(80),
                      index=False,
                      unique=False,
                      nullable=False)

    _default_fields = ['email', 'created']
    _hidden_fields = ['password']
    _readonly_fields = ['created']

    def __repr__(self):
        return self.to_json()


#class UserSettings(BaseModel):
#    __tablename__ == 'user_settings'
#    id = db.Column(db.Integer,
#                    primary_key=True)
#
#    user_id = db.Column(db.Integer,
#                        db.ForeignKey('users.id'),
#                        nullable=False,
#                        index=True)
#
#    user = db.relationship('User',
#        backref=db.backref('user_settings', lazy='joined'))
#
#    def __repr__(self):
#        return self.to_json()

class Server(BaseModel):
    __tablename__ = 'servers'
    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    comment = db.Column(db.String(256),
                     nullable=False,
                     default='')
    url = db.Column(db.String(256),
                    nullable=False,
                    index=True)
    skip_ssl = db.Column(db.Boolean,
                         nullable=False,
                         default=False)
    authkey = db.Column(db.String(40),
                        nullable=True)
    basicauth = db.Column(db.String(120),
                        nullable=True)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    server_group_id = db.Column(db.Integer,
                        db.ForeignKey('server_groups.id'),
                        nullable=False,
                        index=True)
    server_query_id = db.Column(db.Integer,
                        db.ForeignKey('server_queries.id'),
                        nullable=True,
                        index=True)

    user = db.relationship('User',
        backref=db.backref('servers', lazy='joined'))

    server_group = db.relationship('ServerGroup',
        backref=db.backref('servers', lazy='joined', uselist=True))
    
    server_info = db.relationship('ServerQuery',
        backref=db.backref('hostServer', lazy='joined', uselist=False))

    _default_fields = ['id', 'name', 'comment', 'url', 'skip_ssl', 'user', 'auth_method', 'server_info', 'authkey', 'basicauth']
    _hidden_fields = []
    # _hidden_fields = ['authkey', 'basicauth']
    _readonly_fields = ['user_id']

    @hybrid_property
    def auth_method(self):
        methods = []
        if self.authkey:
            methods.append("API Key")
        if self.basicauth:
            methods.append("Basic Auth")
        return methods

    def __repr__(self):
        return self.to_json()


class ServerQuery(BaseModel):
    __tablename__ = 'server_queries'
    id = db.Column(db.Integer,
                   primary_key=True)
    server_id = db.Column(db.Integer,
                     nullable=False,
                     unique=True,
                     index=True)
    timestamp = db.Column(db.Integer,
                    nullable=False,
                    index=True)
    query_result = db.Column(db.JSON, nullable=False)

    _default_fields = ['server_id', 'timestamp', 'query_result']
    _hidden_fields = []
    _readonly_fields = []

    def __repr__(self):
        return self.to_json()


class ServerGroup(BaseModel):
    __tablename__ = 'server_groups'
    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    description = db.Column(db.String(2048),
                            nullable=False,
                            default='')
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    timestamp = db.Column(db.Integer,
                        nullable=False,
                        index=True)

    @hybrid_property
    def server_count(self):
        result = db.session.query(Server.server_group_id, func.count(Server.id)) \
                    .group_by(Server.server_group_id) \
                    .filter_by(server_group_id=self.id).first()
        if result is None:
            the_count = 0
        else:
            server_group_id, the_count = result
        return the_count

    _default_fields = ['id', 'name', 'description', 'timestamp', 'server_count']
    _hidden_fields = []
    _readonly_fields = ['user_id']

    def __repr__(self):
        return self.to_json()
