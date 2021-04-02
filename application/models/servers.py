
from application.DBModels import db, User, Server, ServerQuery


def index():
    servers = Server.query.all()
    return servers
