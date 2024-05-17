# from application import db
from datetime import datetime
import json
import uuid
from sqlalchemy import func
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.sqlite import JSON
# from application.baseModel import BaseModel
from flask_sqlalchemy import SQLAlchemy

from application.models.auth import create_API_key

db = SQLAlchemy()
from application.baseModel import BaseModel
from application import bcrypt


def generate_uuid():
    return str(uuid.uuid4())

def init_defaults():
    if User.query.first() is None:
        user = User(email='admin@admin.test', password='Password1234')
        db.session.add(user)
        db.session.commit()


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
    updated = db.Column(db.DateTime,
                        index=False,
                        unique=False,
                        nullable=False,
                        default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    hashed_password = db.Column(db.String(80),
                      index=False,
                      unique=False,
                      nullable=False)
    apikey = db.Column(db.String(40),
                      index=False,
                      unique=False,
                      nullable=True,
                      default= create_API_key)

    user_settings = db.relationship("UserSettings", uselist=True, back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def authenticate(cls, email, password_candidate):
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password_candidate):
            return user
        return None
    
    @hybrid_property
    def password(self):
        """Return the hashed user password."""
        return self.hashed_password

    @password.setter
    def password(self, password):
        self.hashed_password = bcrypt.generate_password_hash(password)

    def verify_password(self, candidate):
        return bcrypt.check_password_hash(self.hashed_password, candidate)


class UserSettings(BaseModel):
    __tablename__ = 'user_settings'
    settings_to_json = ['Plugins.enabled_plugins']

    id = db.Column(db.Integer,
                    primary_key=True)

    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    
    name = db.Column(db.String(120), nullable=False, index=True)
    _value = db.Column('value', db.String)
    UniqueConstraint(user_id, name)

    user = db.relationship('User', back_populates='user_settings')

    @property
    def value(self):
        if self.name in self.settings_to_json:
            try:
                decoded = json.loads(self._value)
            except:
                decoded = []
            return decoded
        return self._value

    @value.setter
    def value(self, val):
        if type(val) is list or type(val) is dict:
            val = json.dumps(val)
        self._value = val



class Server(BaseModel):
    __tablename__ = 'servers'
    id = db.Column(db.Integer,
                   primary_key=True)
    name = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    uuid = db.Column(db.CHAR(36),
                     index=True,
                     unique=True,
                     nullable=False,
                     default=generate_uuid)
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
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)
    fleet_id = db.Column(db.Integer,
                        db.ForeignKey('fleets.id'),
                        nullable=False,
                        index=True)
    # server_query_id = db.Column(db.Integer,
    #                     db.ForeignKey('server_queries.id'),
    #                     nullable=True,
    #                     index=True)

    user = db.relationship('User',
        backref=db.backref('servers', lazy='joined'))

    # fleet = db.relationship('Fleet',
    #     backref=db.backref('fleet', lazy='joined', uselist=True))
    fleet = db.relationship('Fleet', back_populates='servers')

    @hybrid_property
    def server_info(self):
        import application.models.servers as serverModel
        return serverModel.getServerInfo(self.id, True)

    @server_info.setter
    def server_info(self, info):
        self._server_info = info

class ServerMinimal(Server):
    @hybrid_property
    def server_info(self):
        return {}

    @server_info.setter
    def server_info(self, info):
        return



class Fleet(BaseModel):
    __tablename__ = 'fleets'
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

    servers = db.relationship('Server', back_populates='fleet', cascade='all, delete-orphan')
    # servers = db.relationship('Server',
    #     backref=db.backref('fleet', lazy=True, uselist=True, nullable=False),
    #     cascade='all, delete-orphan')
    # servers = db.relationship('Server', back_populates="fleet", lazy="joined", uselist=True, cascade="all, delete-orphan")

    @hybrid_property
    def server_count(self):
        result = db.session.query(Server.fleet_id, func.count(Server.id)) \
                    .group_by(Server.fleet_id) \
                    .filter_by(fleet_id=self.id).first()
        if result is None:
            the_count = 0
        else:
            fleet_id, the_count = result
        return the_count


class PinList(BaseModel):
    __tablename__ = 'pin_lists'
    id = db.Column(db.Integer,
                   primary_key=True)
    model = db.Column(db.String(120),
                     nullable=False,
                     index=True)
    uuid = db.Column(db.String(36),
                            nullable=False,
                            default='')
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id'),
                        nullable=False,
                        index=True)

    user = db.relationship('User',
        backref=db.backref('pinlists', lazy='joined'))
    pinlist_entries = db.relationship("PinListEntry", back_populates="pinlist", cascade="all, delete-orphan")
    # pinlist_entries = db.relationship("PinListEntry", cascade="all, delete-orphan")


class PinListEntry(BaseModel):
    __tablename__ = 'pin_list_entries'
    id = db.Column(db.Integer,
                   primary_key=True)
    pinlist_id = db.Column(db.Integer,
                   db.ForeignKey('pin_lists.id'),
                   nullable=False,
                   index=True)
    server_id = db.Column(db.Integer,
                   db.ForeignKey('servers.id'),
                   nullable=False,
                   index=True)
    data = db.Column(db.JSON,
                     nullable=False,
                     default='{}')

    pinlist = db.relationship('PinList', back_populates="pinlist_entries")
        # backref=db.backref('pinlist_entries', lazy='joined', cascade="all, delete-orphan"))
