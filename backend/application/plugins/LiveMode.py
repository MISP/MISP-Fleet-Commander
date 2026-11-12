from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import responseJson
from application.models import mispOps
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class LiveMode(BasePlugin):
    name = 'Live Mode'
    description = 'Display and manage the status of MISP.live'
    icon = 'fas fa-toggle-off'
    action_parameters = [
        PluginResponse.genActionParameter('enabled', 'select', 'Live Mode Status', 'Live Mode OFF prevent non-site-admin users to access the instance', None, [
            {'text': 'OFF', 'value': '0'},
            {'text': 'ON', 'value': '1'},
        ]),
    ]

    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        liveMode = LiveMode.getLiveModeFromServer(server)
        data = liveMode
        return SuccessPluginResponse(data, None, 'boolean')

    def index(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return self.view(server, data)

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        selectedState = str(data.get('enabled', True)).strip().lower() in ('1', 'true', 'on')
        return LiveMode.toggleLiveMode(server, selectedState)

    @classmethod
    def getLiveModeFromServer(cls, server: Server) -> Union[bool, None]:
        setting = mispOps.snapshotSettings(server.server_info).get('MISP.live')
        return None if setting is None else setting.get('value')

    @classmethod
    def toggleLiveMode(cls, server: Server, liveModeEnabled: bool = True) -> PluginResponse:
        try:
            response = mispOps.editSetting(server, 'MISP.live', liveModeEnabled)
        except mispOps.MispOpError as e:
            data = responseJson(e.response) if e.response is not None else None
            return FailPluginResponse(data if isinstance(data, dict) else {}, [e.message], None, e.response)
        data = responseJson(response)
        return SuccessPluginResponse(data if isinstance(data, dict) else {}, None, None, response)
