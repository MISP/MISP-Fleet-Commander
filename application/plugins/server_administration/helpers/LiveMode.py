from .baseAdministrationHelper import baseAdministrationHelper
from application.controllers.utils import mispGetRequest, mispPostRequest


class LiveMode(baseNotificationHelper):
    name = "Live Mode"
    description = "Live Mode"
    variant = 'primary'
    icon = 'toggle-off'

    def getView(self, server, data={}):
        finalSettings = mispGetRequest(self.server, '/servers/serverSettings/MISP.json')['finalSettings']
        liveMode = [setting for setting in finalSettings if setting['setting'] == 'MISP.live']
        return liveMode

    def execPlugin(self, server, data={}):
        enabled = False
        result = mispPostRequest(self.server, '/servers/serverSettingsEdit/MISP.live', {'Server': {'value': enabled}})
        if 'error' in result:
            return result

        return result

