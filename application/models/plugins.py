
# import time
# from abc import ABC, abstractmethod

# def feature_enabled(method):
#     method.feature_enabled = False
#     return method

from collections import defaultdict
from typing import List, Optional
import json
from application.DBModels import db, User, Server, ServerQuery
# from application import loadedPlugins


class PluginResponse:

    def __init__(self, status: str, data: dict, errors: Optional[List] = [], component: Optional[str] = None):
        self.status = status
        self.data = data
        self.errors = errors
        self.component = component

    def response(self) -> dict:
        response = {
            'status': self.status,
            'data': self.data,
        }
        if self.errors:
            response['error'] = self.errors
        if self.component:
            response['component'] = self.component

        return response

    def genActionParameter(key: str, type: str, label: Optional[str], options: Optional[dict]) -> dict:
        return {
            'key': key,
            'type': type,
            'label': label if label is not None else key,
            'options': options,
        }

    def __iter__(self):
        yield from self.__dict__.items()

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return str(type(self)) + json.dumps(dict(self), ensure_ascii=False)

    def __repr__(self):
        return self.__str__()
    
    def to_json(self):
        return json.dumps(dict(self), ensure_ascii=False)


class SuccessPluginResponse(PluginResponse):
    def __init__(self, data: dict, errors: Optional[List] = [], component: Optional[str] = None):
        super().__init__('success', data, errors, component)

class FailPluginResponse(PluginResponse):
    def __init__(self, data: dict, errors: Optional[List] = [], component: Optional[str] = None):
        super().__init__('fail', data, errors, component)

class ErrorPluginResponse(PluginResponse):
    def __init__(self, data: dict, errors: Optional[List] = [], component: Optional[str] = None):
        super().__init__('error', data, errors, component)


class BasePlugin:
    id = 'unamed-plugin'
    name = 'Unamed plugin'
    description = ''
    icon = 'fas fa-plugin'
    action_parameters = []

    def __init__(self):
        self.name = type(self).name if type(self).name != BasePlugin.name else BasePlugin.name
        self.id = type(self).id if type(self).id != BasePlugin.id else self.name.replace(' ', '-').lower()
        self.description = type(self).description if type(self).description != BasePlugin.description else BasePlugin.description
        self.icon = type(self).icon if type(self).icon != BasePlugin.icon else BasePlugin.icon
        self.action_parameters = type(self).action_parameters if type(self).action_parameters != BasePlugin.action_parameters else BasePlugin.action_parameters

    def view(self, server: Server, data: Optional[dict]) -> PluginResponse:
        pass

    def index(self, servers: List[Server], data: Optional[dict]) -> PluginResponse:
        pass
    
    def notifications(self, server: Server, data: Optional[dict]) -> PluginResponse:
        pass

    def action(self, servers: List[Server], data: Optional[dict]) -> PluginResponse:
        pass

    def introspection(self):
        return {
            'view': type(self).view != BasePlugin.view,
            'index': type(self).index != BasePlugin.index,
            'notifications': type(self).notifications != BasePlugin.notifications,
            'action': type(self).action != BasePlugin.action,
        }


    def __iter__(self):
        yield from self.__dict__.items()

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(dict(self), ensure_ascii=False)

    def __repr__(self):
        return self.__str__()
    
    def to_json(self):
        return self.__str__()


def getAllIndexValue(loadedPlugins: list, servers: List[Server]) -> list:
    indexValues = defaultdict(dict)
    for plugin in loadedPlugins:
        print(plugin['id'])
        for server in servers:
            indexValues[server.id][plugin['id']] = getIndexValue(server, plugin)
    return indexValues

def getIndexValue(server: Server, plugin):
    pluginInstance = plugin['instance']
    return pluginInstance.index(server)

# class baseAdministrationHelper:
#     name = 'base'
#     def __init__(self):
#         self.server = None

#     def setServer(self, server):
#         self.server = server

#     @classmethod
#     @feature_enabled
#     def getView(self, server, data={}):
#         pass
    
#     @classmethod
#     @feature_enabled
#     def execPlugin(self, server, data={}):
#         pass
    
#     def introspection(self):
#         return {
#             'view': getattr(self.run, 'feature_enabled', True),
#             'exec': getattr(self.run, 'feature_enabled', True),
#         }


# class Severity:
#     NA = 0
#     LOW = 1
#     MEDIUM = 2
#     HIGH = 3


# class baseNotificationHelper:
#     name = 'base'
#     def __init__(self):
#         self.server = None

#     def setServer(self, server):
#         self.server = server

#     @classmethod
#     @feature_enabled
#     def query(self):
#         pass
    
#     @classmethod
#     @feature_enabled
#     def accept(self):
#         pass

#     @classmethod
#     @feature_enabled
#     def process(self):
#         pass

#     @classmethod
#     @feature_enabled
#     def delete(self):
#         pass

#     def queryHelper(self):
#         queryResult = self.query()
#         results = []
#         if type(queryResult) != list:
#             queryResult = [queryResult]
#         for qr in queryResult:
#             if qr is None:
#                 continue
#             data = qr['data'] if 'data' in qr else qr
#             severity = qr['severity'] if 'severity' in qr else Severity.NA
#             title = qr['title'] if 'title' in qr else ''
#             results.append({
#                 "timestamp": int(time.time()),
#                 "origin": self.name,
#                 "severity": severity,
#                 "title": title,
#                 "data": data
#             })
#         return results


#     def introspection(self):
#         return {
#             'query': getattr(self.query, 'feature_enabled', True),
#             'accept': getattr(self.accept, 'feature_enabled', True),
#             'process': getattr(self.process, 'feature_enabled', True),
#             'delete': getattr(self.delete, 'feature_enabled', True),
#         }
