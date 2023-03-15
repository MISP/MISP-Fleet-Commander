#!/usr/bin/env python3

import time
from application import celery_app
from application.controllers.websocket import SocketioEmitter
from application.marshmallowSchemas import serverSchema
import application.models.servers as serverModel


socketioEmitter = SocketioEmitter()


@celery_app.task(name="fetchServerInfoTask")
def fetchServerInfoTask(serverDict):
    server = serverSchema.load(serverDict)
    serverInfo = serverModel.fetchServerInfo(server)
    socketioEmitter.udpate_server(serverInfo)

