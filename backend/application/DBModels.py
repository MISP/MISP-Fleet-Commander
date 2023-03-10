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

    # server_group = db.relationship('ServerGroup',
    #     backref=db.backref('server_group', lazy='joined', uselist=True))
    server_group = db.relationship('ServerGroup', back_populates='servers')


    @hybrid_property
    def auth_method(self):
        methods = []
        if self.authkey:
            methods.append("API Key")
        if self.basicauth:
            methods.append("Basic Auth")
        return methods

    @auth_method.setter
    def auth_method(self, method):
        self._auth_method = method

    @hybrid_property
    def server_info(self):
        import application.models.servers as serverModel
        return serverModel.getServerInfo(self.id, True)

    @server_info.setter
    def server_info(self, info):
        self._server_info = info



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

    servers = db.relationship('Server', back_populates='server_group', cascade='all, delete-orphan')
    # servers = db.relationship('Server',
    #     backref=db.backref('server_group', lazy=True, uselist=True, nullable=False),
    #     cascade='all, delete-orphan')
    # servers = db.relationship('Server', back_populates="server_group", lazy="joined", uselist=True, cascade="all, delete-orphan")

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
