
from application.DBModels import db, User, Server, ServerQuery


def index(group_id=None):
    q = Server.query
    if group_id is not None:
        q = q.filter_by(server_group_id=group_id)
    servers = q.all()
    return servers
