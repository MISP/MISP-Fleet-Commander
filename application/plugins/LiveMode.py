from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class LiveMode(BasePlugin):
    name = 'Live Mode'
    description = 'Display and manage the status of MISP.live'
    icon = 'fas fa-toggle-off'
    action_parameters = [
        PluginResponse.genActionParameter('live', 'checkbox', 'Live Mode Status', {0: 'Off', 1: 'On'}),
    ]

    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        liveMode = LiveMode.getLiveModeFromServer(server)
        data = liveMode
        return SuccessPluginResponse(data, None, 'boolean')

    def index(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return self.view(server, data)

    def action(self, servers: List[Server], data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        return [
            LiveMode.toggleLiveMode(server, data.enabled) for server in servers
        ]


    @classmethod
    def getLiveModeFromServer(cls, server: Server) -> bool:
        finalSettings = server.server_info.query_result['serverSettings']['finalSettings']
        liveModeSetting = [setting for setting in finalSettings if setting['setting'] == 'MISP.live'][0]
        liveMode = liveModeSetting['value']
        return liveMode

    @classmethod
    def toggleLiveMode(cls, server: Server, liveModeEnabled: bool = True) -> PluginResponse:
        url = '/servers/serverSettingsEdit/MISP.live'
        result = mispPostRequest(server, url, {'Server': {'value': liveModeEnabled}})
        if 'error' in result:
            actionResponse = FailPluginResponse(result, [result['error']])
        else:
            actionResponse = SuccessPluginResponse(result)
            

        return actionResponse
