from application import db
from sqlalchemy.inspection import inspect
from datetime import datetime
import json


class Serializer(object):

    def serialize(self):
        # for c in inspect(self).attrs.keys():
        #     print(c, getattr(self, c))
        return {c: getattr(self, c) for c in inspect(self).attrs.keys()}


    @staticmethod
    def serialize_list(l):
        return [m.serialize() for m in l]


class User(db.Model, Serializer):
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

    def __repr__(self):
        return f'<User[{self.id}] {self.email}, {self.created}>'


class Server(db.Model, Serializer):
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
                        nullable=False)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)

    user = db.relationship('User',
        backref=db.backref('servers', lazy=True))
    
    server_query = db.relationship('ServerQuery',
        backref=db.backref('server', lazy=False))

    # def serialize(self):
    #     pass
        # handle recursive serialize???


    def __repr__(self):
       return f"<Server(name='{self.name}', url='{self.url}'[{self.skip_ssl}], user_id='{self.user_id}', ServerQuery='{self.server_query}')>"


class ServerQuery(db.Model, Serializer):
    __tablename__ = 'server_queries'
    id = db.Column(db.Integer,
                   primary_key=True)
    server_id = db.Column(db.Integer,
                     db.ForeignKey('servers.id'),
                     nullable=False,
                     unique=True,
                     index=True)
    timestamp = db.Column(db.Integer,
                    nullable=False,
                    index=True)
    query_result = db.Column(db.JSON, nullable=False)

    def __repr__(self):
       return f"<ServerQuery(server_id='{self.server_id}', timestamp='{self.timestamp}', query_result='{self.query_result}')>"
