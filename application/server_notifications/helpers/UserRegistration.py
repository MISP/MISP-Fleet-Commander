from .baseNotificationHelper import baseNotificationHelper, Severity
from application.controllers.utils import mispGetRequest, mispPostRequest


class UserRegistration(baseNotificationHelper):
    name = "User Registration"

    def query(self):
        results = []
        registrations = mispGetRequest(self.server, '/users/registrations')
        if 'error' in registrations:
            return results

        for registration in registrations:
            registration = registration['Inbox']
            results.append({
                "title": self._getTitle(registration['data']),
                "severity": self._getSeverity(registration['data']),
                "data": {
                    "registration": registration['data'],
                    "comment": registration['comment']
                }
            })
        return results

    def _getTitle(self, registration):
        if registration:
            return f"`{registration['email']}` requested an account for organisation `{registration['org_name']}`."
        else:
            return "Invalid registration object"

    def _getSeverity(self, registration):
        return Severity.MEDIUM