from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
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
        data = result.json()
        if 'error' in result:
            actionResponse = FailPluginResponse(result, [result['error']], None, result)
        else:
            if result.status_code == 404:
                actionResponse = FailPluginResponse(data, [data['message']], None, result)
            else:
                data['message'] = f"Organisation `{data['Organisation']['name']}` exists on server `{server.name}`"
                actionResponse = SuccessPluginResponse(data, None, None, result)

        return actionResponse

