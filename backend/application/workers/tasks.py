#!/usr/bin/env python3

import time
from application import db
from application.celery import app as celery_app
from application.DBModels import ServerQuery, Server
from application.controllers.utils import mispGetRequest
from application.marshmallowSchemas import serverSchema
from application.models.servers import attachConnectedServerStatus


@celery_app.task
def add(x, y):
    return x + y


@celery_app.task(name="fetchServerInfoTask")
def fetchServerInfoTask(serverDict):
    return 123
    # server = serverSchema.load(serverDict)
    # serverSettings = mispGetRequest(server, '/servers/serverSettings/diagnostics/light:1')
    # serverUsage = mispGetRequest(server, '/users/statistics')
    # serverUser = mispGetRequest(server, '/users/view/me')
    # connectedServers = mispGetRequest(server, '/servers/index')
    # connectedServers = attachConnectedServerStatus(server, connectedServers)
    # serverContent = []
    # server_query = {
    #     'serverSettings': serverSettings,
    #     'serverUsage': serverUsage,
    #     'serverUser': serverUser,
    #     'connectedServers': connectedServers,
    #     'serverContent': serverContent
    # }
    # server_query_db = saveInfo(server, server_query)
    # return server_query_db

def saveInfo(server, queryResult):
    now = int(time.time())
    server_query = ServerQuery.query.filter_by(server_id=server.id).first()
    if server_query is not None:
        server_query.query_result = queryResult
        server_query.timestamp = now
    else:
        server_query = ServerQuery(server_id=server.id,
                        timestamp=now,
                        query_result=queryResult)
    server.server_info = server_query
    db.session.add(server)
    db.session.commit()
    return server_query