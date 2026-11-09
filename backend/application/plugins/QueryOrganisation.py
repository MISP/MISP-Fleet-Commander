from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest, mispRequestError, responseJson
from application.models.plugins import BasePlugin, ErrorPluginResponse, PluginResponse, SuccessPluginResponse, FailPluginResponse


class QueryOrganisation(BasePlugin):
    name = 'Query Organisation'
    description = 'Allow to query a server to check if the organisation exists'
    icon = 'fas fa-building'
    action_parameters = [
        PluginResponse.genActionParameter(
            'org_name_or_uuid',
            'input',
            'Organisation name / UUID',
            'The organisation name or UUID to check',
            'ORGNAME',
        ),
    ]


    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        org_name = data.get('org_name_or_uuid', None)
        if org_name is None or len(org_name) == 0:
            return ErrorPluginResponse({}, ['Must provide an Organisation name or UUID'])
        return self.getOrganisation(server, org_name)


    @classmethod
    def getOrganisation(cls, server: Server, org_name_or_uuid: str) -> PluginResponse:
        url = f'/organisations/view/{org_name_or_uuid}'
        result = mispGetRequest(server, url, rawResponse=True, nocache=True)
        error = mispRequestError(result)
        if isinstance(result, dict):  # The request failed
            return FailPluginResponse({}, [error])
        data = responseJson(result)
        if result.status_code == 404:
            message = data.get('message') if isinstance(data, dict) else None
            return FailPluginResponse(data, [message or f'Organisation `{org_name_or_uuid}` not found'], None, result)
        if error is not None:
            return FailPluginResponse(data, [error], None, result)
        if not isinstance(data, dict) or 'Organisation' not in data:
            return FailPluginResponse(data, ['Unexpected answer'], None, result)
        data['message'] = f"Organisation `{data['Organisation']['name']}` exists on server `{server.name}`"
        return SuccessPluginResponse(data, None, None, result)

