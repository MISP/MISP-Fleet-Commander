
# import time
# from abc import ABC, abstractmethod

from collections import defaultdict
import time
from typing import List, Literal, Optional, Union
import json
from application import flaskApp
from application.DBModels import Server
from requests import Response as requestsResponse
# from application import loadedPlugins


class PluginResponse:

    def __init__(self, status: str, data: dict, errors: Optional[List] = [], component: Optional[str] = None, request: Optional[requestsResponse] = None):
        self.status = status
        self.data = data
        self.errors = errors
        self.component = component
        self.requestsResponse = request

    def response(self) -> dict:
        response = {
            'status': self.status,
            'data': self.data,
        }
        if self.errors:
            response['error'] = self.errors
        if self.component:
            response['component'] = self.component
        if self.requestsResponse is not None:
            response['request_response'] = {
                'timestamp': int(time.time()),
                'headers': dict(self.requestsResponse.headers),
                'status_code': self.requestsResponse.status_code,
                'reason': self.requestsResponse.reason,
                'elapsed_time': str(self.requestsResponse.elapsed),
                'url': self.requestsResponse.url,
            }

        return response

    def genActionParameter(
        key: str,
        type: Literal['select', 'checkbox', 'textarea', 'text', 'input', 'picker'],
        label: Optional[str],
        description: Optional[str] = '',
        placeholder: Optional[str] = '',
        options: Optional[dict] = {}
    ) -> dict:
        return {
            'key': key,
            'type': type,
            'label': label if label is not None else key,
            'description': description,
            'placeholder': placeholder,
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
    def __init__(self, data: Union[dict, list], errors: Optional[List] = [], component: Optional[str] = None, request: Optional[requestsResponse] = None):
        super().__init__('success', data, errors, component, request)

class FailPluginResponse(PluginResponse):
    def __init__(self, data: Union[dict, list], errors: Optional[List] = [], component: Optional[str] = None, request: Optional[requestsResponse] = None):
        super().__init__('fail', data, errors, component, request)

class ErrorPluginResponse(PluginResponse):
    def __init__(self, data: dict, errors: Optional[List] = [], component: Optional[str] = None, request: Optional[requestsResponse] = None):
        super().__init__('error', data, errors, component, request)


class PluginNotification:

    class Severity:
        NA = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3

    def __init__(
        self,
        title: str,
        severity: Optional[Union[int, None]] = 0,
        timestamp: Optional[Union[int, None]] = None,
        origin: Optional[str] = '',
        data: Optional[dict] = {}
    ) -> List[dict]:
        self.title = title
        self.severity = severity if severity is not None else PluginNotification.Severity.NA
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.origin = origin
        self.data = data

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


class BasePlugin:
    id = 'unamed-plugin'
    name = 'Unamed plugin'
    description = ''
    icon = 'fas fa-plugin'
    abstract_class = False
    disabled = False
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


def getPluginFromID(loadedPlugins: list, pluginID: str):
    return next((plugin for plugin in loadedPlugins if plugin['id'] == pluginID), None)

def getAllIndexValues(loadedPlugins: list, servers: List[Server]) -> dict:
    indexValues = defaultdict(dict)
    for plugin in loadedPlugins:
        if plugin['features']['index']:
            for server in servers:
                indexValues[server.id][plugin['id']] = getIndexValue(server, plugin)
    return indexValues

def getIndexValue(server: Server, plugin) -> dict:
    pluginInstance = plugin['instance']
    try:
        indexValue = pluginInstance.index(server)
    except Exception as e:
        flaskApp.logger.error('getIndexValue failed for plugin {0}. Error: {1}'.format(plugin['id'], str(e)))
        indexValue = FailPluginResponse({}, [str(e)])
    return indexValue.response()

def getAllViewValues(loadedPlugins: list, server: Server) -> dict:
    viewValues = defaultdict(dict)
    for plugin in loadedPlugins:
        if plugin['features']['view']:
            viewValues[plugin['id']] = getViewValue(server, plugin)
    return viewValues

def getViewValue(server: Server, plugin) -> dict:
    pluginInstance = plugin['instance']
    try:
        viewValue = pluginInstance.view(server)
    except Exception as e:
        flaskApp.logger.error('getViewValue failed for plugin {0}. Error: {1}'.format(plugin['id'], str(e)))
        viewValue = FailPluginResponse({}, [str(e)])
    return viewValue.response()

def doAction(server: Server, plugin, data: Optional[dict]) -> dict:
    pluginInstance = plugin['instance']
    try:
        actionResult = pluginInstance.action(server, data)
    except Exception as e:
        flaskApp.logger.error('doAction failed for plugin {0}. Error: {1}'.format(plugin['id'], str(e)))
        actionResult = FailPluginResponse({}, [str(e)])
    return actionResult.response()

def getNotificationForPlugin(server: Server, plugin) -> list:
    pluginInstance = plugin['instance']
    notifications = pluginInstance.notifications(server)
    try:
        notifications = pluginInstance.notifications(server)
        notifications.data = [notificationData.to_dict() for notificationData in notifications.data]
    except Exception as e:
        flaskApp.logger.error('getNotificationForPlugin failed for plugin {0}. Error: {1}'.format(plugin['id'], str(e)))
        notifications = FailPluginResponse({}, [str(e)])
    return notifications.response()

def getAllNotifications(loadedPlugins: list, server: Server) -> dict:
    allNotifications = defaultdict(dict)
    for plugin in loadedPlugins:
        if plugin['features']['notifications']:
            allNotifications[plugin['id']] = getNotificationForPlugin(server, plugin)
    return allNotifications
