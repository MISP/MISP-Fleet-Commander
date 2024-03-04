from typing import List, Optional, Union
from requests import Response as requestsResponse
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, ErrorPluginResponse, PluginResponse, SuccessPluginResponse, FailPluginResponse


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

    def __init__(self):
        super().__init__()
        taxonomies = ToggleTaxonomy.fetchTaxonomies()
        self.action_parameters = [
            PluginResponse.genActionParameter('enabled', 'select', 'Status', 'Status `Enabled` ensure a taxonomy is enabled and all its tag are created.', None, [
                {'text': 'Disabled', 'value': '0'},
                {'text': 'Enabled', 'value': '1'},
            ]),
            PluginResponse.genActionParameter('taxonomies_uuid', 'picker', 'Taxonomies', 'The taxonomies to have their status changed', None, taxonomies),
        ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        state = data.get('enabled', None)
        if state is not None:
            state = True if state == '1' else False
        namespace = data.get('taxonomies_uuid', [])
        result = ToggleTaxonomy.toggleTaxonomy(server, state, namespace)
        return result


    @classmethod
    def fetchTaxonomies(cls):
        # TODO: Rely on misp-taxonomies to fetch them.
        return [
            {
                'text': taxonomy['namespace'],
                'value': taxonomy['namespace']
            } for taxonomy in ALL_TAXONOMIES
        ]


    @classmethod
    def toggleTaxonomy(cls, server: Server, state: bool, taxonomies: str) -> PluginResponse:
        result = None
        errorCount = 0
        successCount = 0
        errors = []
        successes = []
        if state is None or taxonomies is None:
            result = ErrorPluginResponse({}, [f'Invalid parameters (namespace: `{taxonomies}`, state: `{state}`)'])
            return result

        taxonomyIDByName = ToggleTaxonomy.fetchAllIDs(server)
        if type(taxonomyIDByName) is requestsResponse:
            return taxonomyIDByName

        for taxonomy in taxonomies:
            taxonomyID = taxonomyIDByName.get(taxonomy, None)
            if taxonomyID is not None:
                if state:
                    success = ToggleTaxonomy.enableTaxonomy(server, taxonomyID)
                else:
                    success = ToggleTaxonomy.disableTaxonomy(server, taxonomyID)
            else:
                success = f'Could not find taxonomy with name `{taxonomy}`'

            if success is True:
                successCount += 1
                successes.append(taxonomy)
            else:
                errorCount += 1
                errors.append(f"{taxonomy} - {success}")
        
        if successCount > 0:
            successMessage = f"Successfully {'enabled' if state else 'disabled'} {successCount} taxonomies."
            if errorCount > 0:
                successMessage += f" {errorCount} taxonomies could not be updated"
            data = {
                'message': successMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return SuccessPluginResponse(data, errors)
        else:
            failMessage = f"Count not {'enable' if state else 'disable'} any taxonomies. {errorCount} Failed to be updated"
            data = {
                'message': failMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return FailPluginResponse(data, errors)

    @classmethod
    def fetchAllIDs(cls, server: Server) -> Union[int, requestsResponse]:
        urlTaxonomyIndex = f'/taxonomies/index'
        result = mispGetRequest(server, urlTaxonomyIndex, {}, rawResponse=True, nocache=True)
        data = result.json()
        if 'Taxonomy' not in data[0]:
            return result
        taxonomyIDByName = {}
        for taxonomy in data:
            taxonomyIDByName[taxonomy['Taxonomy']['namespace']] = int(taxonomy['Taxonomy']['id'])
        return taxonomyIDByName


    @classmethod
    def enableTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        urlEnable = f'/taxonomies/enable/{taxonomyID}'
        urlAddTags = f'/taxonomies/addTag/{taxonomyID}'

        resultEnable = mispPostRequest(server, urlEnable, {}, rawResponse=True, nocache=True)
        if 'error' in resultEnable:
            actionResponse = resultEnable['error']
        else:
            resultAdd = mispPostRequest(server, urlAddTags, {}, rawResponse=True, nocache=True)
            if 'error' in resultAdd:
                actionResponse = resultAdd['error']
            else:
                actionResponse = True

        return actionResponse

    @classmethod
    def disableTaxonomy(cls, server: Server, taxonomyID: int) -> PluginResponse:
        url = f'/taxonomies/disable/{taxonomyID}'
        result = mispPostRequest(server, url, {}, rawResponse=True, nocache=True)
        if 'error' in result:
            actionResponse = result['error']
        else:
            actionResponse = True

        return actionResponse


ALL_TAXONOMIES = [
  {
    "namespace": "CERT-XLM",
    "version": "2"
  },
  {
    "namespace": "DFRLab-dichotomies-of-disinformation",
    "version": "1"
  },
  {
    "namespace": "DML",
    "version": "1"
  },
  {
    "namespace": "PAP",
    "version": "2"
  },
  {
    "namespace": "access-method",
    "version": "1"
  },
  {
    "namespace": "accessnow",
    "version": "3"
  },
  {
    "namespace": "action-taken",
    "version": "2"
  },
  {
    "namespace": "admiralty-scale",
    "version": "5"
  },
  {
    "namespace": "adversary",
    "version": "6"
  },
  {
    "namespace": "ais-marking",
    "version": "2"
  },
  {
    "namespace": "approved-category-of-action",
    "version": "1"
  },
  {
    "namespace": "binary-class",
    "version": "2"
  },
  {
    "namespace": "cccs",
    "version": "2"
  },
  {
    "namespace": "circl",
    "version": "5"
  },
  {
    "namespace": "coa",
    "version": "2"
  },
  {
    "namespace": "collaborative-intelligence",
    "version": "3"
  },
  {
    "namespace": "common-taxonomy",
    "version": "3"
  },
  {
    "namespace": "copine-scale",
    "version": "3"
  },
  {
    "namespace": "course-of-action",
    "version": "2"
  },
  {
    "namespace": "cryptocurrency-threat",
    "version": "1"
  },
  {
    "namespace": "csirt-americas",
    "version": "1"
  },
  {
    "namespace": "csirt_case_classification",
    "version": "1"
  },
  {
    "namespace": "cssa",
    "version": "8"
  },
  {
    "namespace": "cti",
    "version": "1"
  },
  {
    "namespace": "current-event",
    "version": "1"
  },
  {
    "namespace": "cyber-threat-framework",
    "version": "2"
  },
  {
    "namespace": "cycat",
    "version": "1"
  },
  {
    "namespace": "cytomic-orion",
    "version": "1"
  },
  {
    "namespace": "data-classification",
    "version": "1"
  },
  {
    "namespace": "dcso-sharing",
    "version": "1"
  },
  {
    "namespace": "ddos",
    "version": "2"
  },
  {
    "namespace": "de-vs",
    "version": "1"
  },
  {
    "namespace": "dhs-ciip-sectors",
    "version": "2"
  },
  {
    "namespace": "diamond-model",
    "version": "1"
  },
  {
    "namespace": "dni-ism",
    "version": "3"
  },
  {
    "namespace": "domain-abuse",
    "version": "2"
  },
  {
    "namespace": "drugs",
    "version": "2"
  },
  {
    "namespace": "economical-impact",
    "version": "4"
  },
  {
    "namespace": "ecsirt",
    "version": "2"
  },
  {
    "namespace": "enisa",
    "version": "20170725"
  },
  {
    "namespace": "estimative-language",
    "version": "5"
  },
  {
    "namespace": "eu-marketop-and-publicadmin",
    "version": "1"
  },
  {
    "namespace": "eu-nis-sector-and-subsectors",
    "version": "1"
  },
  {
    "namespace": "euci",
    "version": "3"
  },
  {
    "namespace": "europol-event",
    "version": "1"
  },
  {
    "namespace": "europol-incident",
    "version": "1"
  },
  {
    "namespace": "event-assessment",
    "version": "2"
  },
  {
    "namespace": "event-classification",
    "version": "1"
  },
  {
    "namespace": "failure-mode-in-machine-learning",
    "version": "1"
  },
  {
    "namespace": "file-type",
    "version": "1"
  },
  {
    "namespace": "flesch-reading-ease",
    "version": "2"
  },
  {
    "namespace": "fpf",
    "version": "0"
  },
  {
    "namespace": "gdpr",
    "version": "0"
  },
  {
    "namespace": "gea-nz-activities",
    "version": "1"
  },
  {
    "namespace": "gea-nz-entities",
    "version": "1"
  },
  {
    "namespace": "gea-nz-motivators",
    "version": "1"
  },
  {
    "namespace": "gsma-attack-category",
    "version": "1"
  },
  {
    "namespace": "gsma-fraud",
    "version": "1"
  },
  {
    "namespace": "gsma-network-technology",
    "version": "3"
  },
  {
    "namespace": "honeypot-basic",
    "version": "4"
  },
  {
    "namespace": "ics",
    "version": "1"
  },
  {
    "namespace": "iep",
    "version": "2"
  },
  {
    "namespace": "iep2-policy",
    "version": "1"
  },
  {
    "namespace": "iep2-reference",
    "version": "1"
  },
  {
    "namespace": "ifx-vetting",
    "version": "3"
  },
  {
    "namespace": "incident-disposition",
    "version": "2"
  },
  {
    "namespace": "infoleak",
    "version": "7"
  },
  {
    "namespace": "information-security-data-source",
    "version": "1"
  },
  {
    "namespace": "information-security-indicators",
    "version": "1"
  },
  {
    "namespace": "interception-method",
    "version": "1"
  },
  {
    "namespace": "ioc",
    "version": "2"
  },
  {
    "namespace": "iot",
    "version": "2"
  },
  {
    "namespace": "kill-chain",
    "version": "2"
  },
  {
    "namespace": "maec-delivery-vectors",
    "version": "1"
  },
  {
    "namespace": "maec-malware-behavior",
    "version": "1"
  },
  {
    "namespace": "maec-malware-capabilities",
    "version": "2"
  },
  {
    "namespace": "maec-malware-obfuscation-methods",
    "version": "1"
  },
  {
    "namespace": "malware_classification",
    "version": "2"
  },
  {
    "namespace": "misinformation-website-label",
    "version": "1"
  },
  {
    "namespace": "misp",
    "version": "12"
  },
  {
    "namespace": "monarc-threat",
    "version": "1"
  },
  {
    "namespace": "ms-caro-malware",
    "version": "1"
  },
  {
    "namespace": "ms-caro-malware-full",
    "version": "2"
  },
  {
    "namespace": "mwdb",
    "version": "2"
  },
  {
    "namespace": "nato",
    "version": "2"
  },
  {
    "namespace": "nis",
    "version": "2"
  },
  {
    "namespace": "open_threat",
    "version": "1"
  },
  {
    "namespace": "osint",
    "version": "11"
  },
  {
    "namespace": "pandemic",
    "version": "4"
  },
  {
    "namespace": "passivetotal",
    "version": "2"
  },
  {
    "namespace": "pentest",
    "version": "3"
  },
  {
    "namespace": "priority-level",
    "version": "2"
  },
  {
    "namespace": "ransomware",
    "version": "6"
  },
  {
    "namespace": "retention",
    "version": "3"
  },
  {
    "namespace": "rt_event_status",
    "version": "2"
  },
  {
    "namespace": "runtime-packer",
    "version": "1"
  },
  {
    "namespace": "scrippsco2-fgc",
    "version": "1"
  },
  {
    "namespace": "scrippsco2-fgi",
    "version": "1"
  },
  {
    "namespace": "scrippsco2-sampling-stations",
    "version": "1"
  },
  {
    "namespace": "smart-airports-threats",
    "version": "1"
  },
  {
    "namespace": "stealth_malware",
    "version": "1"
  },
  {
    "namespace": "stix-ttp",
    "version": "1"
  },
  {
    "namespace": "targeted-threat-index",
    "version": "3"
  },
  {
    "namespace": "threatmatch",
    "version": "3"
  },
  {
    "namespace": "threats-to-dns",
    "version": "1"
  },
  {
    "namespace": "tor",
    "version": "1"
  },
  {
    "namespace": "trust",
    "version": "1"
  },
  {
    "namespace": "type",
    "version": "1"
  },
  {
    "namespace": "use-case-applicability",
    "version": "1"
  },
  {
    "namespace": "veris",
    "version": "2"
  },
  {
    "namespace": "vmray",
    "version": "1"
  },
  {
    "namespace": "vocabulaire-des-probabilites-estimatives",
    "version": "3"
  },
  {
    "namespace": "GrayZone",
    "version": "3"
  },
  {
    "namespace": "artificial-satellites",
    "version": "1"
  },
  {
    "namespace": "aviation",
    "version": "1"
  },
  {
    "namespace": "cnsd",
    "version": "20220513"
  },
  {
    "namespace": "dark-web",
    "version": "5"
  },
  {
    "namespace": "death-possibilities",
    "version": "1"
  },
  {
    "namespace": "deception",
    "version": "1"
  },
  {
    "namespace": "dga",
    "version": "2"
  },
  {
    "namespace": "diamond-model-for-influence-operations",
    "version": "1"
  },
  {
    "namespace": "exercise",
    "version": "10"
  },
  {
    "namespace": "extended-event",
    "version": "2"
  },
  {
    "namespace": "false-positive",
    "version": "7"
  },
  {
    "namespace": "financial",
    "version": "7"
  },
  {
    "namespace": "fr-classif",
    "version": "6"
  },
  {
    "namespace": "information-origin",
    "version": "2"
  },
  {
    "namespace": "interactive-cyber-training-audience",
    "version": "1"
  },
  {
    "namespace": "interactive-cyber-training-technical-setup",
    "version": "1"
  },
  {
    "namespace": "interactive-cyber-training-training-environment",
    "version": "1"
  },
  {
    "namespace": "interactive-cyber-training-training-setup",
    "version": "1"
  },
  {
    "namespace": "nis2",
    "version": "3"
  },
  {
    "namespace": "phishing",
    "version": "5"
  },
  {
    "namespace": "poison-taxonomy",
    "version": "1"
  },
  {
    "namespace": "political-spectrum",
    "version": "1"
  },
  {
    "namespace": "pyoti",
    "version": "3"
  },
  {
    "namespace": "ransomware-roles",
    "version": "1"
  },
  {
    "namespace": "rsit",
    "version": "1003"
  },
  {
    "namespace": "sentinel-threattype",
    "version": "1"
  },
  {
    "namespace": "social-engineering-attack-vectors",
    "version": "1"
  },
  {
    "namespace": "state-responsibility",
    "version": "1"
  },
  {
    "namespace": "thales_group",
    "version": "4"
  },
  {
    "namespace": "tlp",
    "version": "7"
  },
  {
    "namespace": "unified-kill-chain",
    "version": "1"
  },
  {
    "namespace": "workflow",
    "version": "11"
  },
  {
    "namespace": "misp-workflow",
    "version": "3"
  }
]
