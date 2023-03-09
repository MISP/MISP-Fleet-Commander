from typing import List, Optional, Union
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

        taxonomyID = ToggleTaxonomy.getTaxonomyID(server, namespace)
        if taxonomyID is not None:
            if state:
                result = ToggleTaxonomy.enabledTaxonomy(server, taxonomyID)
            else:
                result = ToggleTaxonomy.disableTaxonomy(server, taxonomyID)
        else:
            result = FailPluginResponse({}, [f'Could not found taxonomy with namespace `{namespace}`'])
        return result

    @classmethod
    def getTaxonomyID(cls, server: Server, namespace: str) -> int:
        urlTaxonomyIndex = f'/taxonomies/index/value:{namespace}'
        result = mispGetRequest(server, urlTaxonomyIndex, {})
        for taxonomy in result:
            if taxonomy['Taxonomy']['namespace'] == namespace:
                return int(taxonomy['Taxonomy']['id'])


    @classmethod
    def enabledTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        urlEnable = f'/taxonomies/enable/{taxonomyID}'
        urlAddTags = f'/taxonomies/addTag/{taxonomyID}'
        result = mispPostRequest(server, urlEnable, {})
        if 'error' in result:
            actionResponse = FailPluginResponse(result, [result['error']])
        else:
            result = mispPostRequest(server, urlAddTags, {})
            if 'error' in result:
                actionResponse = FailPluginResponse(result, [result['error']])
            else:
                actionResponse = SuccessPluginResponse(result)

        return actionResponse

    @classmethod
    def disableTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        print('di')
        url = f'/taxonomies/disable/{taxonomyID}'
        result = mispPostRequest(server, url, {})
        if 'error' in result:
            actionResponse = FailPluginResponse(result, [result['error']])
        else:
            actionResponse = SuccessPluginResponse(result)

        return actionResponse
