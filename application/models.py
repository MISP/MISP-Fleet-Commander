from application import db
from sqlalchemy.inspection import inspect
from datetime import datetime
import json



class Serializer(object):

    def serialize(self):
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
    url = db.Column(db.String(256),
                    nullable=False,
                    index=True)
    authkey = db.Column(db.String(40),
                        nullable=False)
    user_id = db.Column(db.Integer,
                        nullable=False,
                        index=True) 

    def __repr__(self):
       return f"<Server(name='{self.name}', url='{self.url}', user_id='{self.user_id}')>"
