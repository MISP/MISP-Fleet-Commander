import json
from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class GalaxyImport(BasePlugin):
    name = 'Galaxy Import'
    description = 'Call the /galaxies/import endpoint with the provided data'
    icon = 'fas fa-globe'
    action_parameters = [
        PluginResponse.genActionParameter('payload', 'textarea', 'Galaxy JSON', 'The JSON of the Galaxy to import', '[{"GalaxyCluster": { ...'),
    ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        payload = data.get('payload', None)
        try:
            payload = json.loads(payload)
        except Exception as e:
            return FailPluginResponse({}, [str(e)])
        result = GalaxyImport.importGalaxy(server, payload)
        return result


    @classmethod
    def importGalaxy(cls, server: Server, payload: str) -> PluginResponse:
        result = None
        if payload is None:
            result = FailPluginResponse({}, [f'Invalid parameters (payload: `{payload}`)'])

        result = GalaxyImport.doImport(server, payload)
        return result

    @classmethod
    def doImport(cls, server: Server, payload: dict) -> PluginResponse:
        url = '/galaxies/import'
        result = mispPostRequest(server, url, data=payload, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in data:
            actionResponse = FailPluginResponse(data, [data['error']], None, result)
        else:
            if result.ok:
                actionResponse = SuccessPluginResponse(data, None, None, result)
            else:
                actionResponse = FailPluginResponse(data, [data['errors']], None, result)


        return actionResponse
