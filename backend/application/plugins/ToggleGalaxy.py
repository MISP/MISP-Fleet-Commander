from typing import List, Optional, Union
from requests import Response as requestsResponse
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class ToggleGalaxy(BasePlugin):
    name = 'Toggle Galaxy'
    description = 'Allow to enable or disable the selected galaxy'
    icon = 'fas fa-toggle-off'
    action_parameters = [
        PluginResponse.genActionParameter('enabled', 'select', 'Status', 'Status `Enabled` ensure the galaxy is enabled.', None, [
            {'text': 'Disabled', 'value': '0'},
            {'text': 'Enabled', 'value': '1'},
        ]),
        PluginResponse.genActionParameter('galaxy_name_or_uuid', 'text', 'Galaxy Name or UUID', 'The name or UUID of the galaxy to toggle', None),
    ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        state = data.get('enabled', None)
        if state is not None:
            state = True if state == '1' else False
        galaxy_name_uuid = data.get('galaxy_name_or_uuid', None)
        result = ToggleGalaxy.toggleGalaxy(server, state, galaxy_name_uuid)
        return result


    @classmethod
    def toggleGalaxy(cls, server: Server, state: bool, galaxy_name_uuid: str) -> PluginResponse:
        result = None
        if state is None or galaxy_name_uuid is None:
            result = FailPluginResponse({}, [f'Invalid parameters (namespace: `{galaxy_name_uuid}`, state: `{state}`)'])

        galaxyIDOrRequestResponse = ToggleGalaxy.getGalaxyID(server, galaxy_name_uuid)
        if type(galaxyIDOrRequestResponse) is not requestsResponse:
            if state:
                result = ToggleGalaxy.enableGalaxy(server, galaxyIDOrRequestResponse)
            else:
                result = ToggleGalaxy.disableGalaxy(server, galaxyIDOrRequestResponse)
        else:
            galaxyIDOrRequestResponse.status_code = 404
            galaxyIDOrRequestResponse.reason = 'Not Found'
            result = FailPluginResponse({}, [f'Could not find galaxy with name or UUID `{galaxy_name_uuid}`'], None, galaxyIDOrRequestResponse)
        return result

    @classmethod
    def getGalaxyID(cls, server: Server, galaxy_name_uuid: str) -> Union[int, requestsResponse]:
        url = f'/galaxies/index/value:{galaxy_name_uuid}'
        result = mispGetRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        for galaxy in data:
            if galaxy['Galaxy']['name'] == galaxy_name_uuid or galaxy['Galaxy']['uuid'] == galaxy_name_uuid:
                return int(galaxy['Galaxy']['id'])
        return result


    @classmethod
    def enableGalaxy(cls, server: Server, galaxyID: int) -> PluginResponse:
        url = f'/galaxies/enable/{galaxyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in result:
            actionResponse = FailPluginResponse(result, [result['error']], None, result)
        else:
            actionResponse = SuccessPluginResponse(data, [], None, result)

        return actionResponse

    @classmethod
    def disableGalaxy(cls, server: Server, galaxyID: int) -> PluginResponse:
        url = f'/galaxies/disable/{galaxyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in result:
            actionResponse = FailPluginResponse(data, [result['error']], None, result)
        else:
            actionResponse = SuccessPluginResponse(data, [], None, result)

        return actionResponse
