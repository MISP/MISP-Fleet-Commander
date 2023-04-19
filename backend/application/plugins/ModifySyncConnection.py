import json
from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class ModifySyncConnection(BasePlugin):
    name = 'Modify Sync Connection'
    description = 'Modifies the synchronisation configuration to all available sync connections.'
    icon = 'fas fa-network-wired'
    action_parameters = [
        PluginResponse.genActionParameter('url_index_filters', 'text', 'URL Index filters', 'Optional filter conditions to be passed on the server index via its `search` URL parameter', 'localhost'),
        PluginResponse.genActionParameter('payload', 'textarea', 'Synchronisation JSON', 'The JSON containing the changes to be applied', '{"push": 1}'),
    ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        urlFilters = data.get('url_index_filters', '')
        payload = data.get('payload', None)
        try:
            payload = json.loads(payload)
        except Exception as e:
            return FailPluginResponse({}, [str(e)])
        payload = ModifySyncConnection.rearrangePayload(payload)
        syncConnections = ModifySyncConnection.getFilteredServers(server, urlFilters)
        result = ModifySyncConnection.pushChangesToAllServers(server, syncConnections, payload)
        return result


    @classmethod
    def rearrangePayload(cls, payload: dict = {}) -> list:
        # Right now, MISP requires this to work..
        if 'push_rules' not in payload:
            payload['push_rules'] = "{\"tags\": []}"
        return payload

    @classmethod
    def getFilteredServers(cls, server: Server, urlFilters: str = '') -> list:
        url = f'/servers/index/search:{urlFilters}'
        servers = mispGetRequest(server, url)

        filteredServers = []
        # Make sure we filter based on server name and URL even if server doesn't support server/index filtering (2.4.171)
        for syncConnection in servers:
            if urlFilters in syncConnection['Server']['name'] or urlFilters in syncConnection['Server']['url']:
                filteredServers.append(syncConnection)

        return filteredServers

    @classmethod
    def pushChangesToAllServers(cls, server: Server, syncConnections: list, payload: str) -> Union[PluginResponse, List[PluginResponse]]:
        errors = []
        for syncConnection in syncConnections:
            result = ModifySyncConnection.pushChanges(server, syncConnection['Server']['id'], payload)
            if not result['success']:
                errors.push(result['error'])
        if len(errors) > 0:
            actionResponse = FailPluginResponse({'success': False, 'message': f"Could not change {len(errors)} sync connections. But successfully changed {len(syncConnections) - len(errors)} sync connections."}, errors)
        else:
            actionResponse = SuccessPluginResponse({'success': True, 'message': f"Successfully changed {len(syncConnections)} sync connections."})
        return actionResponse

    @classmethod
    def pushChanges(cls, server: Server, serverID: int, payload: str) -> dict:
        url = f"/servers/edit/{serverID}"
        result = mispPostRequest(server, url, data=payload)
        if 'error' in result:
            return {'success': False, 'error': result['error']}
        else:
            return {'success': True, 'response': result}
