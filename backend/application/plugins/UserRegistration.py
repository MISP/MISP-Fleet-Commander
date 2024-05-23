from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginNotification, PluginResponse, SuccessPluginResponse, FailPluginResponse


class UserRegistration(BasePlugin):
    name = 'User Registration'
    description = 'Display the list of open user registration'
    icon = 'fas fa-user-plus'
    _default_severity = PluginNotification.Severity.MEDIUM

    def notifications(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        success, notifications = UserRegistration.doQuery(server)
        if success:
            pluginNotifications = [
                PluginNotification(
                    notification['title'],
                    notification.get('severity', UserRegistration._default_severity),
                    notification.get('timestamp', None),
                    notification.get('origin', None),
                    notification.get('data', {}),
                ) for notification in notifications
            ]
            return SuccessPluginResponse(pluginNotifications, None, None)
        else:
            return FailPluginResponse([], notifications['error'])


    @classmethod
    def doQuery(cls, server: Server):
        results = []
        registrations = mispGetRequest(server, '/users/registrations')
        if 'error' in registrations:
            return False, registrations

        for registration in registrations:
            registration = registration['Inbox']
            results.append({
                "title": UserRegistration.makeTitle(registration['data']),
                "severity": UserRegistration._default_severity,
                "data": {
                    "registration": registration['data'],
                    "comment": registration['comment']
                }
            })
        return True, results

    @classmethod
    def makeTitle(cls, registration):
        if registration:
            return f"`{registration['email']}` requested an account for organisation `{registration['org_name']}`."
        else:
            return "Invalid registration object"
