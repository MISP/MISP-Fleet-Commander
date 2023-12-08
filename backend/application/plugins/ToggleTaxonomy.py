from typing import List, Optional, Union
from requests import Response as requestsResponse
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse


class ToggleTaxonomy(BasePlugin):
    name = 'Toggle Taxonomy'
    description = 'Allow to enable or disable the selected taxonomy'
    icon = 'fas fa-toggle-off'
    action_parameters = [
        PluginResponse.genActionParameter('enabled', 'select', 'Status', 'Status `Enabled` ensure a taxonomy is enabled and all its tag are created.', None, [
            {'text': 'Disabled', 'value': '0'},
            {'text': 'Enabled', 'value': '1'},
        ]),
        PluginResponse.genActionParameter('taxonomy_namespace', 'text', 'Taxonomy namespace', 'The namespace of the taxonomy to toggle', 'None'),
    ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        state = data.get('enabled', None)
        namespace = data.get('taxonomy_namespace', None)
        result = ToggleTaxonomy.toggleTaxonomy(server, state, namespace)
        return result


    @classmethod
    def toggleTaxonomy(cls, server: Server, state: bool, namespace: str) -> PluginResponse:
        result = None
        if state is None or namespace is None:
            result = FailPluginResponse({}, [f'Invalid parameters (namespace: `{namespace}`, state: `{state}`)'])

        taxonomyIDOrRequestResponse = ToggleTaxonomy.getTaxonomyID(server, namespace)
        if type(taxonomyIDOrRequestResponse) is not requestsResponse:
            if state:
                result = ToggleTaxonomy.enabledTaxonomy(server, taxonomyIDOrRequestResponse)
            else:
                result = ToggleTaxonomy.disableTaxonomy(server, taxonomyIDOrRequestResponse)
        else:
            taxonomyIDOrRequestResponse.status_code = 404
            taxonomyIDOrRequestResponse.reason = 'Not Found'
            result = FailPluginResponse({}, [f'Could not find taxonomy with namespace `{namespace}`'], None, taxonomyIDOrRequestResponse)
        return result

    @classmethod
    def getTaxonomyID(cls, server: Server, namespace: str) -> Union[int, requestsResponse]:
        urlTaxonomyIndex = f'/taxonomies/index/value:{namespace}'
        result = mispGetRequest(server, urlTaxonomyIndex, {}, rawResponse=True, nocache=True)
        data = result.json()
        for taxonomy in data:
            if taxonomy['Taxonomy']['namespace'] == namespace:
                return int(taxonomy['Taxonomy']['id'])
        return result


    @classmethod
    def enabledTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        urlEnable = f'/taxonomies/enable/{taxonomyID}'
        urlAddTags = f'/taxonomies/addTag/{taxonomyID}'
        resultEnable = mispPostRequest(server, urlEnable, {}, rawResponse=True, nocache=True)
        if 'error' in resultEnable:
            actionResponse = FailPluginResponse(resultEnable, [resultEnable['error']], None, resultEnable)
        else:
            resultAdd = mispPostRequest(server, urlAddTags, {}, rawResponse=True, nocache=True)
            data = resultAdd.json()
            if 'error' in resultAdd:
                actionResponse = FailPluginResponse(data, [resultAdd['error']], None, resultAdd)
            else:
                actionResponse = SuccessPluginResponse(data, [], None, resultAdd)

        return actionResponse

    @classmethod
    def disableTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        print('di')
        url = f'/taxonomies/disable/{taxonomyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in result:
            actionResponse = FailPluginResponse(data, [result['error']], None, result)
        else:
            actionResponse = SuccessPluginResponse(data, [], None, result)

        return actionResponse
