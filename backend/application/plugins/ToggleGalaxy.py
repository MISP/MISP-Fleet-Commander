from typing import List, Optional, Union
from requests import Response as requestsResponse
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse, ErrorPluginResponse


class ToggleGalaxy(BasePlugin):
    name = 'Toggle Galaxy'
    description = 'Allow to enable or disable the selected galaxy'
    icon = 'fas fa-toggle-off'

    def __init__(self):
        super().__init__()
        galaxies = ToggleGalaxy.fetchGalaxies()
        self.action_parameters = [
            PluginResponse.genActionParameter('enabled', 'select', 'Status', 'Status `Enabled` ensure the galaxy is enabled.', None, [
                {'text': 'Disabled', 'value': '0'},
                {'text': 'Enabled', 'value': '1'},
            ]),
            PluginResponse.genActionParameter('galaxies_uuid', 'picker', 'Galaxies', 'The list of galaxies to have their status changed', None, galaxies),
        ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        state = data.get('enabled', None)
        if state is not None:
            state = True if state == '1' else False
        galaxies_uuid = data.get('galaxies_uuid', [])
        result = ToggleGalaxy.toggleGalaxies(server, state, galaxies_uuid)
        return result

    @classmethod
    def fetchGalaxies(cls):
        # TODO: Rely on misp-galaxy to fetch them.
        return [
            {
                'text': f"{galaxy.get('namespace', '-')} :: {galaxy['name']}",
                'value': galaxy['uuid'],
                'group': f"{galaxy.get('namespace', '-')}"
            } for galaxy in ALL_GALAXIES
        ]

    @classmethod
    def toggleGalaxies(cls, server: Server, state: bool, galaxies_uuid: list) -> PluginResponse:
        result = None
        errorCount = 0
        successCount = 0
        errors = []
        successes = []
        if state is None or galaxies_uuid is None:
            result = ErrorPluginResponse({}, [f'Invalid parameters (namespace: `{galaxies_uuid}`, state: `{state}`)'])
            return result

        galaxyIDByUUID = ToggleGalaxy.fetchAllIDs(server)
        if type(galaxyIDByUUID) is requestsResponse:
            return galaxyIDByUUID

        for galaxy_uuid in galaxies_uuid:
            galaxyID = galaxyIDByUUID.get(galaxy_uuid, None)
            if galaxyID is not None:
                if state:
                    success = ToggleGalaxy.enableGalaxy(server, galaxyID)
                else:
                    success = ToggleGalaxy.disableGalaxy(server, galaxyID)
            else:
                success = f'Could not find galaxy with name or UUID `{galaxy_uuid}`'

            if success is True:
                successCount += 1
                successes.append(galaxy_uuid)
            else:
                errorCount += 1
                errors.append(f"{galaxy_uuid} - {success}")

        if successCount > 0:
            successMessage = f"Successfully {'enabled' if state else 'disabled'} {successCount} galaxies."
            if errorCount > 0:
                successMessage += f" {errorCount} galaxies could not be updated"
            data = {
                'message': successMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return SuccessPluginResponse(data, errors)
        else:
            failMessage = f"Count not {'enable' if state else 'disable'} any galaxies. {errorCount} Failed to be updated"
            data = {
                'message': failMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return FailPluginResponse(data, errors)

    @classmethod
    def fetchAllIDs(cls, server: Server) -> Union[list, requestsResponse]:
        url = f'/galaxies/index'
        result = mispGetRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'Galaxy' not in data[0]:
            return result
        galaxyIDByUUID = {}
        for galaxy in data:
            galaxyIDByUUID[galaxy['Galaxy']['uuid']] = int(galaxy['Galaxy']['id'])
        return galaxyIDByUUID

    @classmethod
    def enableGalaxy(cls, server: Server, galaxyID: int) -> Union[bool, str]:
        url = f'/galaxies/enable/{galaxyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in result:
            actionResponse = result['error']
        else:
            actionResponse = True

        return actionResponse

    @classmethod
    def disableGalaxy(cls, server: Server, galaxyID: int) -> Union[bool, str]:
        url = f'/galaxies/disable/{galaxyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        if 'error' in result:
            actionResponse = result['error']
        else:
            actionResponse = True

        return actionResponse


ALL_GALAXIES = [
    {
        "icon": "user-secret",
        "name": "360.net Threat Actors",
        "namespace": "360net",
        "type": "360net-threat-actor",
        "uuid": "20de4abf-f000-48ec-a929-3cdc5c2f3c23",
        "version": "1",
    },
    {
        "icon": "battery-full",
        "name": "Ammunitions",
        "namespace": "Ammunitions",
        "type": "ammunitions",
        "uuid": "e7394838-65a9-4b8a-b484-b8c4c7cf49c3",
        "version": "1",
    },
    {
        "icon": "android",
        "name": "Android",
        "namespace": "misp",
        "type": "android",
        "uuid": "84310ba3-fa6a-44aa-b378-b9e3271c58fa",
        "version": "3",
    },
    {
        "icon": "map",
        "name": "Azure Threat Research Matrix",
        "namespace": "microsoft",
        "type": "atrm",
        "uuid": "b541a056-154c-41e7-8a56-41db3f871c00",
        "version": "3",
    },
    {
        "icon": "map",
        "name": "attck4fraud",
        "namespace": "misp",
        "type": "financial-fraud",
        "uuid": "cc0c8ae9-aec2-42c6-9939-f4f82b051836",
        "version": "2",
    },
    {
        "icon": "door-open",
        "name": "Backdoor",
        "namespace": "misp",
        "type": "backdoor",
        "uuid": "75436e27-cb57-4f32-bf1d-9636dd78a2bf",
        "version": "1",
    },
    {
        "icon": "dollar-sign",
        "name": "Banker",
        "namespace": "misp",
        "type": "banker",
        "uuid": "59f20cce-5420-4084-afd5-0884c0a83832",
        "version": "3",
    },
    {
        "icon": "mobile",
        "name": "Bhadra Framework",
        "namespace": "misp",
        "type": "bhadra-framework",
        "uuid": "e7b7304b-9e9c-4db4-a7dd-561db4eeeb3d",
        "version": "3",
    },
    {
        "icon": "sitemap",
        "name": "Botnet",
        "namespace": "misp",
        "type": "botnet",
        "uuid": "90ccdf38-1649-11e8-b8bf-e7326d553087",
        "version": "2",
    },
    {
        "icon": "bug",
        "name": "Branded Vulnerability",
        "namespace": "misp",
        "type": "branded-vulnerability",
        "uuid": "fda8c7c2-f45a-11e7-9713-e75dac0492df",
        "version": "2",
    },
    {
        "icon": "android",
        "name": "Cancer",
        "namespace": "misp",
        "type": "disease",
        "uuid": "c03eba6e-a08a-11ec-b909-0242ac120002",
        "version": "1",
    },
    {
        "icon": "globe",
        "name": "Cert EU GovSector",
        "namespace": "misp",
        "type": "cert-eu-govsector",
        "uuid": "68858a48-b898-11e7-91ce-bf424ef9b662",
        "version": "2",
    },
    {
        "icon": "globe",
        "name": "China Defence Universities Tracker",
        "namespace": "misp",
        "type": "china-defence-universities",
        "uuid": "c51c59e9-f213-4ad4-9913-09a43d78dff5",
        "version": "1",
    },
    {
        "icon": "mobile",
        "name": "CONCORDIA Mobile Modelling Framework - Attack Pattern",
        "namespace": "cmmf-attack",
        "type": "cmtmf-attack-pattern",
        "uuid": "51060d01-ef29-40ab-8965-8031d0941811",
        "version": "3",
    },
    {
        "icon": "globe",
        "name": "Country",
        "namespace": "misp",
        "type": "country",
        "uuid": "84668357-5a8c-4bdd-9f0f-6b50b2aee4c1",
        "version": "1",
    },
    {
        "icon": "optin-monster",
        "name": "Cryptominers",
        "namespace": "misp",
        "type": "cryptominers",
        "uuid": "917734cb-6bbf-4568-83b6-ad2b912fc5e4",
        "version": "4",
    },
    {
        "icon": "user-secret",
        "name": "Actor Types",
        "namespace": "disarm",
        "type": "disarm-actortypes",
        "uuid": "1658af88-b847-532d-adc9-efaea8604f14",
        "version": "1",
    },
    {
        "icon": "shield-alt",
        "name": "Countermeasures",
        "namespace": "disarm",
        "type": "disarm-countermeasures",
        "uuid": "9a3ac024-7c65-5ac0-87c4-eaed2238eec8",
        "version": "2",
    },
    {
        "icon": "bell",
        "name": "Detections",
        "namespace": "disarm",
        "type": "disarm-detections",
        "uuid": "bb61e6f3-b2bd-5c7d-929c-b6f292ccc56a",
        "version": "2",
    },
    {
        "icon": "map",
        "name": "Techniques",
        "namespace": "disarm",
        "type": "disarm-techniques",
        "uuid": "a90f2bb6-11e1-58a7-9962-ba37886720ec",
        "version": "2",
    },
    {
        "icon": "map",
        "name": "Election guidelines",
        "namespace": "misp",
        "type": "guidelines",
        "uuid": "c1dc03b2-89b3-42a5-9d41-782ef726435a",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "Entity",
        "namespace": "misp",
        "type": "entity",
        "uuid": "f1b42b47-778f-4e50-bda5-969ee7f9029f",
        "version": "1",
    },
    {
        "icon": "internet-explorer",
        "name": "Exploit-Kit",
        "namespace": "misp",
        "type": "exploit-kit",
        "uuid": "6ab240ec-bd79-11e6-a4a6-cec0c932ce01",
        "version": "4",
    },
    {
        "icon": "fire",
        "name": "Firearms",
        "namespace": "Firearms",
        "type": "firearms",
        "uuid": "94af82d1-d62b-45a7-8c99-83c421cc0f3b",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "FIRST CSIRT Services Framework",
        "namespace": "first",
        "type": "first-csirt-services-framework",
        "uuid": "4a72488f-ef5b-4895-a5d9-c625dee663cb",
        "version": "1",
    },
    {
        "icon": "database",
        "name": "FIRST DNS Abuse Techniques Matrix",
        "namespace": "first-dns",
        "type": "first-dns",
        "uuid": "67d44607-ae1d-4b01-a419-c311e68fb28a",
        "version": "1",
    },
    {
        "icon": "user-shield",
        "name": "GSMA MoTIF",
        "namespace": "gsma",
        "type": "gsma-motif",
        "uuid": "57cf3a17-e186-407a-b58b-d53887ce4950",
        "version": "1",
    },
    {
        "icon": "wheelchair",
        "name": "Handicap",
        "namespace": "misp",
        "type": "handicap",
        "uuid": "84310ba3-fa6a-44aa-b378-b9e3271c7777",
        "version": "2",
    },
    {
        "icon": "ninja",
        "name": "Intelligence Agencies",
        "namespace": "intelligence-agency",
        "type": "intelligence-agency",
        "uuid": "3ef969e7-96cd-4048-aa83-191ac457d0db",
        "version": "1",
    },
    {
        "icon": "user-secret",
        "name": "INTERPOL DWVA Taxonomy",
        "namespace": "interpol",
        "type": "dwva",
        "uuid": "a375d7fd-0a3e-41cf-a531-ef56033df967",
        "version": "1",
    },
    {
        "icon": "shield-virus",
        "name": "Malpedia",
        "namespace": "misp",
        "type": "malpedia",
        "uuid": "1d1c9af9-37fa-4deb-a928-f9b0abc7354a",
        "version": "2",
    },
    {
        "icon": "user-secret",
        "name": "Microsoft Activity Group actor",
        "namespace": "misp",
        "type": "microsoft-activity-group",
        "uuid": "74c869e8-0b8e-4e5f-96e6-cd992e07a505",
        "version": "3",
    },
    {
        "icon": "map",
        "name": "Misinformation Pattern",
        "namespace": "misinfosec",
        "type": "amitt-misinformation-pattern",
        "uuid": "4d381145-9a5e-4778-918c-fbf23d78544e",
        "version": "4",
    },
    {
        "icon": "map",
        "name": "MITRE ATLAS Attack Pattern",
        "namespace": "mitre-atlas",
        "type": "mitre-atlas-attack-pattern",
        "uuid": "3f3d21aa-d8a1-4f8f-b31e-fc5425eec821",
        "version": "1",
    },
    {
        "icon": "link",
        "name": "MITRE ATLAS Course of Action",
        "namespace": "mitre-atlas",
        "type": "mitre-atlas-course-of-action",
        "uuid": "29d13ede-9667-415c-bb75-b34a4bd89a81",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "Attack Pattern",
        "namespace": "mitre-attack",
        "type": "mitre-attack-pattern",
        "uuid": "c4e851fa-775f-11e7-8163-b774922098cd",
        "version": "10",
    },
    {
        "icon": "link",
        "name": "Course of Action",
        "namespace": "mitre-attack",
        "type": "mitre-course-of-action",
        "uuid": "6fcb4472-6de4-11e7-b5f7-37771619e14e",
        "version": "7",
    },
    {
        "icon": "user-shield",
        "name": "MITRE D3FEND",
        "namespace": "mitre",
        "type": "mitre-d3fend",
        "uuid": "77d1bbfa-2982-4e0a-9238-1dae4a48c5b4",
        "version": "1",
    },
    {
        "icon": "sitemap",
        "name": "mitre-data-component",
        "namespace": "mitre-attack",
        "type": "mitre-data-component",
        "uuid": "afff2d74-5d4a-4aa7-995a-3701a2dbe593",
        "version": "1",
    },
    {
        "icon": "sitemap",
        "name": "mitre-data-source",
        "namespace": "mitre-attack",
        "type": "mitre-data-source",
        "uuid": "dca5da28-fdc0-4b37-91cd-989d139d96cf",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "Enterprise Attack - Attack Pattern",
        "namespace": "deprecated",
        "type": "mitre-enterprise-attack-attack-pattern",
        "uuid": "fa7016a8-1707-11e8-82d0-1b73d76eb204",
        "version": "5",
    },
    {
        "icon": "link",
        "name": "Enterprise Attack - Course of Action",
        "namespace": "deprecated",
        "type": "mitre-enterprise-attack-course-of-action",
        "uuid": "fb5a36c0-1707-11e8-81f5-d732b22a4982",
        "version": "5",
    },
    {
        "icon": "user-secret",
        "name": "Enterprise Attack - Intrusion Set",
        "namespace": "deprecated",
        "type": "mitre-enterprise-attack-intrusion-set",
        "uuid": "1f3b8c56-1708-11e8-b211-17a60c0f73ee",
        "version": "5",
    },
    {
        "icon": "optin-monster",
        "name": "Enterprise Attack - Malware",
        "namespace": "deprecated",
        "type": "mitre-enterprise-attack-malware",
        "uuid": "fbb19af0-1707-11e8-9fd6-dbd88a04d33a",
        "version": "5",
    },
    {
        "icon": "gavel",
        "name": "Enterprise Attack - Tool",
        "namespace": "deprecated",
        "type": "mitre-enterprise-attack-tool",
        "uuid": "fbfa0470-1707-11e8-be22-eb46b373fdd3",
        "version": "5",
    },
    {
        "icon": "certificate",
        "name": "Assets",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-assets",
        "uuid": "86b19468-784e-4ec9-9af9-f069aa4cf70d",
        "version": "1",
    },
    {
        "icon": "skull-crossbones",
        "name": "Groups",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-groups",
        "uuid": "abb28bd9-fa79-4815-b5b3-fb138f433e55",
        "version": "1",
    },
    {
        "icon": "layer-group",
        "name": "Levels",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-levels",
        "uuid": "34d60262-0e7d-4c91-859b-de1fa9c54ae7",
        "version": "1",
    },
    {
        "icon": "file-code",
        "name": "Software",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-software",
        "uuid": "9443a27f-f8b0-4bc7-ba88-7c023d727932",
        "version": "1",
    },
    {
        "icon": "chess-pawn",
        "name": "Tactics",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-tactics",
        "uuid": "e521606c-3c66-4621-9040-6f0f792fc999",
        "version": "1",
    },
    {
        "icon": "user-ninja",
        "name": "Techniques",
        "namespace": "mitre-attack-ics",
        "type": "mitre-ics-techniques",
        "uuid": "99261a7e-2270-40eb-823f-834cc1ad3159",
        "version": "1",
    },
    {
        "icon": "user-secret",
        "name": "Intrusion Set",
        "namespace": "mitre-attack",
        "type": "mitre-intrusion-set",
        "uuid": "1023f364-7831-11e7-8318-43b5531983ab",
        "version": "8",
    },
    {
        "icon": "optin-monster",
        "name": "Malware",
        "namespace": "mitre-attack",
        "type": "mitre-malware",
        "uuid": "d752161c-78f6-11e7-a0ea-bfa79b407ce4",
        "version": "6",
    },
    {
        "icon": "map",
        "name": "Mobile Attack - Attack Pattern",
        "namespace": "deprecated",
        "type": "mitre-mobile-attack-attack-pattern",
        "uuid": "1c6d1332-1708-11e8-847c-e3c5643c41a5",
        "version": "5",
    },
    {
        "icon": "link",
        "name": "Mobile Attack - Course of Action",
        "namespace": "deprecated",
        "type": "mitre-mobile-attack-course-of-action",
        "uuid": "0282356a-1708-11e8-8f53-975633d5c03c",
        "version": "5",
    },
    {
        "icon": "user-secret",
        "name": "Mobile Attack - Intrusion Set",
        "namespace": "deprecated",
        "type": "mitre-mobile-attack-intrusion-set",
        "uuid": "0314e554-1708-11e8-b049-8f8a42b5bb62",
        "version": "5",
    },
    {
        "icon": "optin-monster",
        "name": "Mobile Attack - Malware",
        "namespace": "deprecated",
        "type": "mitre-mobile-attack-malware",
        "uuid": "03e3853a-1708-11e8-95c1-67cf3f801a18",
        "version": "5",
    },
    {
        "icon": "gavel",
        "name": "Mobile Attack - Tool",
        "namespace": "deprecated",
        "type": "mitre-mobile-attack-tool",
        "uuid": "1d0b4bce-1708-11e8-9e6e-1b130c9b0a91",
        "version": "5",
    },
    {
        "icon": "map",
        "name": "Pre Attack - Attack Pattern",
        "namespace": "deprecated",
        "type": "mitre-pre-attack-attack-pattern",
        "uuid": "1f665850-1708-11e8-9cfe-4792b2a91402",
        "version": "5",
    },
    {
        "icon": "user-secret",
        "name": "Pre Attack - Intrusion Set",
        "namespace": "deprecated",
        "type": "mitre-pre-attack-intrusion-set",
        "uuid": "1fb6d5b4-1708-11e8-9836-8bbc8ce6866e",
        "version": "5",
    },
    {
        "icon": "gavel",
        "name": "mitre-tool",
        "namespace": "mitre-attack",
        "type": "mitre-tool",
        "uuid": "d5cbd1a2-78f6-11e7-a833-7b9bccca9649",
        "version": "7",
    },
    {
        "icon": "industry",
        "name": "NACE",
        "namespace": "NACE",
        "type": "NACE",
        "uuid": "f184d102-7df1-4ea5-84f5-71f061814fc5",
        "version": "1",
    },
    {
        "icon": "industry",
        "name": "NAICS",
        "namespace": "misp",
        "type": "naics",
        "uuid": "b73ecad4-6529-4625-8c4f-ee3ef703a72a",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "NICE Competency areas",
        "namespace": "nist-nice",
        "type": "nice-framework-competency_areas",
        "uuid": "e78357aa-01bd-4635-99a1-8eb860fa3bd5",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "NICE Knowledges",
        "namespace": "nist-nice",
        "type": "nice-framework-knowledges",
        "uuid": "de7e23f2-cef8-44ed-b209-b584f7da58a2",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "OPM codes in cybersecurity",
        "namespace": "nist-nice",
        "type": "nice-framework-opm_codes",
        "uuid": "2c56dfbc-82a5-48db-aea4-854ede951c65",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "NICE Skills",
        "namespace": "nist-nice",
        "type": "nice-framework-skills",
        "uuid": "96c5b9e7-5e70-479e-990c-8f1dea06c520",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "NICE Tasks",
        "namespace": "nist-nice",
        "type": "nice-framework-tasks",
        "uuid": "98ba1aa3-d171-49e4-adf1-b7fb5e26a942",
        "version": "1",
    },
    {
        "icon": "user",
        "name": "NICE Work Roles",
        "namespace": "nist-nice",
        "type": "nice-framework-work_roles",
        "uuid": "10a2e9d7-781b-4ff4-bb3e-f0003108fe41",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "o365-exchange-techniques",
        "namespace": "misp",
        "type": "cloud-security",
        "uuid": "44574c7e-b732-4466-a7be-ef363374013a",
        "version": "1",
    },
    {
        "icon": "cloud",
        "name": "online-service",
        "namespace": "misp",
        "type": "online-service",
        "uuid": "c0a960b6-bba4-4914-8d54-87011aaf447e",
        "version": "1",
    },
    {
        "icon": "shield-alt",
        "name": "Preventive Measure",
        "namespace": "misp",
        "type": "preventive-measure",
        "uuid": "8168995b-adcd-4684-9e37-206c5771505a",
        "version": "4",
    },
    {
        "icon": "book",
        "name": "Producer",
        "namespace": "misp",
        "type": "producer",
        "uuid": "2d74a15e-9c88-452e-af14-d0ecd2e9cd63",
        "version": "1",
    },
    {
        "icon": "btc",
        "name": "Ransomware",
        "namespace": "misp",
        "type": "ransomware",
        "uuid": "3f44af2e-1480-4b6b-9aa8-f9bb21341078",
        "version": "4",
    },
    {
        "icon": "eye",
        "name": "RAT",
        "namespace": "misp",
        "type": "rat",
        "uuid": "06825db6-4797-11e7-ac4d-af25fdcdd299",
        "version": "3",
    },
    {
        "icon": "globe-europe",
        "name": "Regions UN M49",
        "namespace": "misp",
        "type": "region",
        "uuid": "d151a79a-e029-11e9-9409-f3e0cf3d93aa",
        "version": "2",
    },
    {
        "icon": "map",
        "name": "rsit",
        "namespace": "RSIT",
        "type": "rsit",
        "uuid": "ddff602c-d2a3-431e-b9e2-2eb5a39a6473",
        "version": "1",
    },
    {
        "icon": "industry",
        "name": "Sector",
        "namespace": "misp",
        "type": "sector",
        "uuid": "e1bb134c-ae4d-11e7-8aa9-f78a37325439",
        "version": "2",
    },
    {
        "icon": "link",
        "name": "Sigma-Rules",
        "namespace": "misp",
        "type": "sigma-rules",
        "uuid": "9cf7cd2e-d5f1-48c4-9909-7896ba1c96b2",
        "version": "1",
    },
    {
        "icon": "link",
        "name": "Dark Patterns",
        "namespace": "misp",
        "type": "social-dark-patterns",
        "uuid": "41c42956-972e-4eef-a3e3-ef3ea35ff1f8",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "SoD Matrix",
        "namespace": "sod-matrix",
        "type": "sod-matrix",
        "uuid": "50104ead-7315-457c-b596-b4471cabf28b",
        "version": "1",
    },
    {
        "icon": "key",
        "name": "Stealer",
        "namespace": "misp",
        "type": "stealer",
        "uuid": "f2ef4033-9001-4427-a418-df8c48e6d054",
        "version": "1",
    },
    {
        "icon": "user-shield",
        "name": "Surveillance Vendor",
        "namespace": "misp",
        "type": "surveillance-vendor",
        "uuid": "c3a92f3a-14f1-11ea-8ab7-fb9951e35286",
        "version": "1",
    },
    {
        "icon": "bullseye",
        "name": "Target Information",
        "namespace": "misp",
        "type": "target-information",
        "uuid": "709ed29c-aa00-11e9-82cd-67ac1a6ee3bc",
        "version": "1",
    },
    {
        "icon": "cart-arrow-down",
        "name": "TDS",
        "namespace": "misp",
        "type": "tds",
        "uuid": "1b9a7d8e-bd7a-11e6-a4a6-cec0c932ce01",
        "version": "4",
    },
    {
        "icon": "map",
        "name": "Tea Matrix",
        "namespace": "tea-matrix",
        "type": "tea-matrix",
        "uuid": "c5f2dfb4-21a1-42d8-a452-1d3c36a204ff",
        "version": "1",
    },
    {
        "icon": "user-secret",
        "name": "Threat Actor",
        "namespace": "misp",
        "type": "threat-actor",
        "uuid": "698774c7-8022-42c4-917f-8d6e4f06ada3",
        "version": "3",
    },
    {
        "icon": "bullhorn",
        "name": "Tidal Campaigns",
        "namespace": "tidal",
        "type": "campaigns",
        "uuid": "3db4b6cb-5b89-4096-a057-e0205777adc9",
        "version": "1",
    },
    {
        "icon": "user-secret",
        "name": "Tidal Groups",
        "namespace": "tidal",
        "type": "groups",
        "uuid": "877cdc4b-3392-4353-a7d4-2e46d40e5936",
        "version": "1",
    },
    {
        "icon": "list",
        "name": "Tidal References",
        "namespace": "tidal",
        "type": "references",
        "uuid": "efd98ec4-16ef-41c4-bc3c-60c7c1ae8b39",
        "version": "1",
    },
    {
        "icon": "file-code",
        "name": "Tidal Software",
        "namespace": "tidal",
        "type": "software",
        "uuid": "6eb44da4-ed4f-4a5d-a444-0f105ff1b3c2",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "Tidal Tactic",
        "namespace": "tidal",
        "type": "tactic",
        "uuid": "16b963e7-4b88-44e0-b184-16bf9e71fdc9",
        "version": "1",
    },
    {
        "icon": "user-ninja",
        "name": "Tidal Technique",
        "namespace": "tidal",
        "type": "technique",
        "uuid": "298b6aee-981b-4fd8-8759-a2e72ad223fa",
        "version": "1",
    },
    {
        "icon": "map",
        "name": "Threat Matrix for storage services",
        "namespace": "microsoft",
        "type": "tmss",
        "uuid": "d6532b58-99e0-44a9-93c8-affe055e4443",
        "version": "1",
    },
    {
        "icon": "optin-monster",
        "name": "Tool",
        "namespace": "misp",
        "type": "tool",
        "uuid": "9b8037f7-bc8f-4de1-a797-37266619bc0b",
        "version": "3",
    },
    {
        "icon": "plane",
        "name": "UAVs/UCAVs",
        "namespace": "misp",
        "type": "uavs",
        "uuid": "bef5c29d-b0db-4923-aa9a-80921f26d3ab",
        "version": "1",
    },
    {
        "icon": "virus",
        "name": "UKHSA Culture Collections",
        "namespace": "gov.uk",
        "type": "ukhsa-culture-collections",
        "uuid": "bbe11c06-1d6a-477e-88f1-cdda2d71de56",
        "version": "1",
    }
]
