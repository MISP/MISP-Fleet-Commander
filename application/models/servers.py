
from typing import List
from application.DBModels import db, User, Server, ServerQuery


def index(group_id=None):
    q = Server.query
    if group_id is not None:
        q = q.filter_by(server_group_id=group_id)
    servers = q.all()
    return servers

def searchAll(text: str) -> List:
    search = "%{}%".format(text)
    query = Server.query.filter(
        (Server.name.ilike(search)) |
        (Server.url.ilike(search)) |
        (Server.comment.ilike(search))
    )
    servers = query.limit(10).all()
    return servers
