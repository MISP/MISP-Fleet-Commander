# from application import db
from datetime import datetime
import json
import uuid
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
# from application.baseModel import BaseModel
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
from application.baseModel import BaseModel
from application import bcrypt


def generate_uuid():
    return str(uuid.uuid4())


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
    server_group_id = db.Column(db.Integer,
                        db.ForeignKey('server_groups.id'),
                        nullable=False,
                        index=True)
    # server_query_id = db.Column(db.Integer,
    #                     db.ForeignKey('server_queries.id'),
    #                     nullable=True,
    #                     index=True)

    user = db.relationship('User',
        backref=db.backref('servers', lazy='joined'))

    # server_group = db.relationship('ServerGroup',
    #     backref=db.backref('server_group', lazy='joined', uselist=True))
    server_group = db.relationship('ServerGroup', back_populates='servers')

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
