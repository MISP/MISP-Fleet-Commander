from typing import List, Optional, Union
from requests import Response as requestsResponse
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse, ErrorPluginResponse


class ToggleObject(BasePlugin):
    name = 'Toggle Object Template'
    description = 'Allow to enable or disable the selected object template'
    icon = 'fas fa-toggle-off'

    def __init__(self):
        super().__init__()
        templates = ToggleObject.getObjectTemplates()
        self.action_parameters = [
            PluginResponse.genActionParameter(
                "enabled",
                "select",
                "Status",
                "Status `Enabled` ensure the object template state is toggled, if it's active, it will become inactive.",
                None,
                [
                    {"text": "Toggle", "value": "0"},
                ],
            ),
            PluginResponse.genActionParameter(
                "template_uuids",
                "picker",
                "Object Templates",
                "The list of object templates to have their status changed",
                None,
                templates,
            ),
        ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        state = data.get('enabled', None)
        if state is not None:
            state = True if state == '1' else False
        template_uuids = data.get("template_uuids", [])
        result = ToggleObject.toggleTemplates(server, template_uuids)
        return result

    @classmethod
    def getObjectTemplates(cls):
        return [
            {
                "text": f"{template.get('meta-category', '-')} :: {template['name']}",
                "value": template["uuid"],
                "group": f"{template.get('meta-category', '-')}",
            }
            for template in ALL_TEMPLATES
        ]

    @classmethod
    def toggleTemplates(cls, server: Server, template_uuids: list) -> PluginResponse:
        result = None
        errorCount = 0
        successCount = 0
        errors = []
        successes = []
        if template_uuids is None:
            result = ErrorPluginResponse(
                {},
                [
                    f"Invalid parameters (template: `{template_uuids}`)"
                ],
            )
            return result

        templatesOnServer = ToggleObject.fetchObjectTemplates(server)
        templateIDByUUID = {
            template['ObjectTemplate']['uuid']: template['ObjectTemplate']['id'] for template in templatesOnServer
        }

        for template_uuid in template_uuids:
            templateID = templateIDByUUID.get(template_uuid, None)
            if templateID is not None:
                success = ToggleObject.toggleTemplate(server, templateID)
            else:
                success = f"Could not find template with name or UUID `{template_uuid}`"

            if success is True:
                successCount += 1
                successes.append(template_uuid)
            else:
                errorCount += 1
                errors.append(f"{template_uuid} - {success}")

        if successCount > 0:
            successMessage = f"Successfully toggled {successCount} templates."
            if errorCount > 0:
                successMessage += f" {errorCount} templates could not be updated"
            data = {
                'message': successMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return SuccessPluginResponse(data, errors)
        else:
            failMessage = f"Count not toggle any templates. {errorCount} Failed to be updated"
            data = {
                'message': failMessage,
                'data': {
                    'successes': successes,
                    'errors': errors,
                }
            }
            return FailPluginResponse(data, errors)

    @classmethod
    def toggleTemplate(cls, server: Server, templateID: int) -> Union[bool, str]:
        url = f'/ObjectTemplates/activate'
        payload = {
            'ObjectTemplate': {
                'data': templateID
            }
        }
        result = mispPostRequest(server, url, payload, rawResponse=True, nocache=True)
        data = result.json()
        if "error" in data:
            actionResponse = result['error']
        else:
            actionResponse = True

        return actionResponse

    @classmethod
    def fetchObjectTemplates(cls, server: Server):
        url = f"objectTemplates/index/all.json"
        result = mispGetRequest(server, url, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' not in result:
            if result.status_code != 404:
                return data
        return []


ALL_TEMPLATES = [
    {
        "name": "ADS",
        "uuid": "07a7f4cf-e738-47ad-b045-34c3b382f3b4",
        "meta-category": "misc"
    },
    {
        "name": "abuseipdb",
        "uuid": "cccdaaf6-c140-461c-8d1c-aa79bbd029e0",
        "meta-category": "network",
    },
    {
        "name": "ai-chat-prompt",
        "uuid": "a78f4156-0bb7-405c-aa25-ba16a73f68e4",
        "meta-category": "misc",
    },
    {
        "name": "ail-leak",
        "uuid": "dc6a8fa2-0a43-4a0c-a5aa-b1a5336ca80e",
        "meta-category": "misc",
    },
    {
        "name": "ais",
        "uuid": "ef90551a-ff34-472c-9fba-c272c4435baa",
        "meta-category": "marine",
    },
    {
        "name": "ais-info",
        "uuid": "1f3f466d-465f-4c3a-8cce-933642c9ea83",
        "meta-category": "misc",
    },
    {
        "name": "android-app",
        "uuid": "92836f23-4730-4eae-82ac-9f00d5299735",
        "meta-category": "file",
    },
    {
        "name": "android-permission",
        "uuid": "d81003b2-5c03-4d96-ae30-e6695de1aea2",
        "meta-category": "misc",
    },
    {
        "name": "annotation",
        "uuid": "5d8dc046-15a1-4ca3-a09f-ed4ede7c4487",
        "meta-category": "misc",
    },
    {
        "name": "anonymisation",
        "uuid": "5867cffe-60ff-44f6-b097-e5f36b5de0ac",
        "meta-category": "misc",
    },
    {
        "name": "apivoid-email-verification",
        "uuid": "289492ab-4b74-49ec-add7-cd9b541f2245",
        "meta-category": "misc",
    },
    {
        "name": "artifact",
        "uuid": "0a46df3a-bd9b-472c-a1e7-6aede7094483",
        "meta-category": "file",
    },
    {
        "name": "asn",
        "uuid": "4ec55cc6-9e49-4c64-b794-03c25c1a6587",
        "meta-category": "network",
    },
    {
        "name": "attack-pattern",
        "uuid": "35928348-56be-4d7f-9752-a80927936351",
        "meta-category": "vulnerability",
    },
    {
        "name": "attack-step",
        "uuid": "F86CD6C4-B89D-454A-95C1-165D456D8A74",
        "meta-category": "misc",
    },
    {
        "name": "attacker-infra",
        "uuid": "0211496c-dbcf-465b-a147-3d965da016cd",
        "meta-category": "misc",
    },
    {
        "name": "authentication-failure-report",
        "uuid": "9b39afe0-9809-4fe0-8a0b-4cec2b140dd2",
        "meta-category": "network",
    },
    {
        "name": "authenticode-signerinfo",
        "uuid": "965cb0aa-baf1-4cc6-9070-68f5c1698c1e",
        "meta-category": "file",
    },
    {
        "name": "av-signature",
        "uuid": "4dbb56ef-4763-4c97-8696-a2bfc305cf8e",
        "meta-category": "misc",
    },
    {
        "name": "availability-impact",
        "uuid": "19b4394a-46a9-4196-a30c-080eaed06273",
        "meta-category": "misc",
    },
    {
        "name": "bank-account",
        "uuid": "b4712203-95a8-4883-80e9-b566f5df11c9",
        "meta-category": "financial",
    },
    {
        "name": "bgp-hijack",
        "uuid": "42355673-1fab-4908-8045-00bebd91c389",
        "meta-category": "network",
    },
    {
        "name": "bgp-ranking",
        "uuid": "0cf87909-e44a-4426-8ebc-a250f932ce00",
        "meta-category": "network",
    },
    {
        "name": "blog",
        "uuid": "1f165fc0-b158-498f-8bc8-6dc3d2822bb1",
        "meta-category": "misc",
    },
    {
        "name": "boleto",
        "uuid": "24979ac7-d413-4345-9c8b-69b43a739fd1",
        "meta-category": "financial",
    },
    {
        "name": "btc-transaction",
        "uuid": "B7341729-5A8A-439F-A775-6D814DA3C7B5",
        "meta-category": "financial",
    },
    {
        "name": "btc-wallet",
        "uuid": "22910C83-DD0E-4ED2-9823-45F8CAD562A4",
        "meta-category": "financial",
    },
    {
        "name": "c2-list",
        "uuid": "12456351-ceb7-4d43-9a7e-d2275d8b5785",
        "meta-category": "network",
    },
    {
        "name": "cap-alert",
        "uuid": "03b107bb-133d-4180-87ff-e3dbe731f828",
        "meta-category": "misc",
    },
    {
        "name": "cap-info",
        "uuid": "826c25e6-fdd5-4e4a-b081-be5ba3ac2c3d",
        "meta-category": "misc",
    },
    {
        "name": "cap-resource",
        "uuid": "6fddc76b-59fc-49f6-a673-52f8d15149c4",
        "meta-category": "misc",
    },
    {
        "name": "cert-pl-phishing",
        "uuid": "4c37c9af-ca71-4365-bcfb-6393c22dd88e",
        "meta-category": "network",
    },
    {
        "name": "cloth",
        "uuid": "31a49e4f-49bc-4bae-a9c7-c6058180ba6f",
        "meta-category": "misc",
    },
    {
        "name": "coin-address",
        "uuid": "d0e6997e-78da-4815-a6a1-cfc1c1cb8a46",
        "meta-category": "financial",
    },
    {
        "name": "command",
        "uuid": "21ad70d8-d397-11e9-9ea7-43b2d5f6a6e3",
        "meta-category": "misc",
    },
    {
        "name": "command-line",
        "uuid": "88ebe222-d3cc-11e9-875d-7f13f460adaf",
        "meta-category": "misc",
    },
    {
        "name": "concordia-mtmf-intrusion-set",
        "uuid": "822cc7e1-5bf9-43e5-80f7-dd0486e3ba17",
        "meta-category": "mobile",
    },
    {
        "name": "confidentiality-impact",
        "uuid": "b0027f13-56e4-4c85-9632-3cf81208429b",
        "meta-category": "misc",
    },
    {
        "name": "cookie",
        "uuid": "7755ad19-55c7-4da4-805e-197cf81bbcb8",
        "meta-category": "network",
    },
    {
        "name": "cortex",
        "uuid": "144988f3-fa00-4374-8015-c1a32092f451",
        "meta-category": "misc",
    },
    {
        "name": "cortex-taxonomy",
        "uuid": "bef7d23b-e796-4d46-803a-32e317896894",
        "meta-category": "misc",
    },
    {
        "name": "course-of-action",
        "uuid": "3d1c2c06-68a9-4394-8c8d-258d115f796f",
        "meta-category": "misc",
    },
    {
        "name": "covid19-csse-daily-report",
        "uuid": "9458bf83-2e29-4ff3-9996-0564f2d954c8",
        "meta-category": "health",
    },
    {
        "name": "covid19-dxy-live-city",
        "uuid": "9132452b-f60a-41ac-a3b9-62701b85621b",
        "meta-category": "health",
    },
    {
        "name": "covid19-dxy-live-province",
        "uuid": "40b49502-088b-44a5-80a7-0e55653f3ed4",
        "meta-category": "health",
    },
    {
        "name": "cowrie",
        "uuid": "ae085d32-6534-4d52-b3eb-063fccb753e7",
        "meta-category": "network",
    },
    {
        "name": "cpe-asset",
        "uuid": "8ea002c4-172d-45ae-8d91-1cdea825e6a9",
        "meta-category": "misc",
    },
    {
        "name": "credential",
        "uuid": "a27e98c9-9b0e-414c-8076-d201e039ca09",
        "meta-category": "misc",
    },
    {
        "name": "credit-card",
        "uuid": "2b9c57aa-daba-4330-a738-56f18743b0c7",
        "meta-category": "financial",
    },
    {
        "name": "crowdsec-ip-context",
        "uuid": "0f0a6def-a351-4d3b-9868-d732f6f4666f",
        "meta-category": "network",
    },
    {
        "name": "crowdstrike-report",
        "uuid": "805b327c-8f1b-4d76-a3ba-c8bc4964e740",
        "meta-category": "misc",
    },
    {
        "name": "crypto-material",
        "uuid": "50677f82-ec9c-4484-bb29-2519cfe56823",
        "meta-category": "misc",
    },
    {
        "name": "cryptocurrency-transaction",
        "uuid": "a4aab70f-e43a-48cb-bf82-505de8228dd6",
        "meta-category": "financial",
    },
    {
        "name": "cs-beacon-config",
        "uuid": "d17355ef-ca1f-4b5a-86cd-65d877991f54",
        "meta-category": "file",
    },
    {
        "name": "ctf-challenge",
        "uuid": "f9bb5d47-ff5b-4569-9987-4bb970639a55",
        "meta-category": "misc",
    },
    {
        "name": "cytomic-orion-file",
        "uuid": "0ad86572-ba38-4baf-9fed-1926e9ecc916",
        "meta-category": "misc",
    },
    {
        "name": "cytomic-orion-machine",
        "uuid": "e0e46343-43fd-4ce7-b447-51381402c774",
        "meta-category": "misc",
    },
    {
        "name": "dark-pattern-item",
        "uuid": "05755e29-8f5f-464d-bcff-2b4686472769",
        "meta-category": "misc",
    },
    {
        "name": "ddos",
        "uuid": "e2f124d6-f57c-4f93-99e6-8450545fa05d",
        "meta-category": "network",
    },
    {
        "name": "ddos-claim",
        "uuid": "2722ac76-1f1f-43b7-bc68-ba5465ec5c04",
        "meta-category": "network",
    },
    {
        "name": "ddos-config",
        "uuid": "e56d7f93-258e-4ba5-bd8a-463acd6d98c4",
        "meta-category": "network",
    },
    {
        "name": "device",
        "uuid": "0c64b41a-e583-4f4d-ac92-d484163b9e52",
        "meta-category": "misc",
    },
    {
        "name": "diameter-attack",
        "uuid": "a3fdce4c-8e21-4acc-ab8e-9976e9165a12",
        "meta-category": "network",
    },
    {
        "name": "diamond-event",
        "uuid": "a9618450-694d-4c73-9f76-35ea0150c19e",
        "meta-category": "internal",
    },
    {
        "name": "directory",
        "uuid": "23ac6a02-1017-4ea6-a4df-148ed563988d",
        "meta-category": "file",
    },
    {
        "name": "dkim",
        "uuid": "7f1e45a5-b050-433e-83c1-1bf8c8d9e4a5",
        "meta-category": "misc",
    },
    {
        "name": "dns-record",
        "uuid": "f023c8f0-81ab-41f3-9f5d-fa597a34a9b9",
        "meta-category": "network",
    },
    {
        "name": "url",
        "uuid": "c7771a39-afa5-4ecb-8d67-ca87ff60236d",
        "meta-category": "file",
    },
    {
        "name": "domain-crawled",
        "uuid": "bad4888d-c44e-4612-b08f-3d97c1e0014a",
        "meta-category": "network",
    },
    {
        "name": "domain-ip",
        "uuid": "43b3b146-77eb-4931-b4cc-b66c60f28734",
        "meta-category": "network",
    },
    {
        "name": "edr-report",
        "uuid": "eeeca35c-cfcb-49f9-81be-e0c31d83c116",
        "meta-category": "misc",
    },
    {
        "name": "elf",
        "uuid": "fa6534ae-ad74-4ce0-8f23-15a66c82c7fa",
        "meta-category": "file",
    },
    {
        "name": "elf-section",
        "uuid": "ca271f32-1234-4e87-b240-6b6e882de5de",
        "meta-category": "file",
    },
    {
        "name": "email",
        "uuid": "a0c666e0-fc65-4be8-b48f-3423d788b552",
        "meta-category": "network",
    },
    {
        "name": "employee",
        "uuid": "443b2f15-d7c9-4d3d-bfd2-38f099753e83",
        "meta-category": "misc",
    },
    {
        "name": "error-message",
        "uuid": "40e81601-8205-41af-8e67-33795291a448",
        "meta-category": "misc",
    },
    {
        "name": "event",
        "uuid": "3853b726-6a9c-43b3-8ffb-23839b07d5a9",
        "meta-category": "misc",
    },
    {
        "name": "exploit",
        "uuid": "611a25d5-d8aa-4dde-b9c8-c084e786ebf3",
        "meta-category": "misc",
    },
    {
        "name": "exploit-poc",
        "uuid": "e3bdeef8-78c3-48d8-9c2f-1be5e5bde93b",
        "meta-category": "vulnerability",
    },
    {
        "name": "external-impact",
        "uuid": "4ac36991-9333-4ada-8e17-bcbeb988160a",
        "meta-category": "misc",
    },
    {
        "name": "facebook-account",
        "uuid": "b9862b95-7d78-4938-a2b5-13e45c60f25a",
        "meta-category": "misc",
    },
    {
        "name": "facebook-group",
        "uuid": "165c5507-1cba-4cec-9be4-66e21b590ee6",
        "meta-category": "misc",
    },
    {
        "name": "facebook-page",
        "uuid": "e76892db-c168-4289-b957-56e3021c46b9",
        "meta-category": "misc",
    },
    {
        "name": "facebook-post",
        "uuid": "82c1fd90-85a1-4420-a315-d2a7cfae2f01",
        "meta-category": "misc",
    },
    {
        "name": "facebook-reaction",
        "uuid": "f219f784-38b8-47f4-a676-e32efd7df0c3",
        "meta-category": "misc",
    },
    {
        "name": "facial-composite",
        "uuid": "d727bc27-d1b9-4754-972c-dea305bd5976",
        "meta-category": "misc",
    },
    {
        "name": "fail2ban",
        "uuid": "32f7ded6-e774-4401-81b0-79634e82f589",
        "meta-category": "network",
    },
    {
        "name": "favicon",
        "uuid": "485892f1-a767-4e9b-b5f8-7f86d1308674",
        "meta-category": "network",
    },
    {
        "name": "file",
        "uuid": "688c46fb-5edb-40a3-8273-1af7923e2215",
        "meta-category": "file",
    },
    {
        "name": "flowintel-cm-case",
        "uuid": "19df57c7-b315-4fd2-84e5-d81ab221425e",
        "meta-category": "misc",
    },
    {
        "name": "flowintel-cm-task",
        "uuid": "2f525f6e-d3f2-4cb9-9ca0-f1160d99397d",
        "meta-category": "misc",
    },
    {
        "name": "flowintel-cm-task-note",
        "uuid": "2c6f6aba-48b6-482f-a810-81934d29be9a",
        "meta-category": "misc",
    },
    {
        "name": "forensic-case",
        "uuid": "3ea36022-ae93-455e-88b1-d43aca789cac",
        "meta-category": "misc",
    },
    {
        "name": "forensic-evidence",
        "uuid": "fe44c648-63ef-43fc-b3de-af71a2e023e4",
        "meta-category": "misc",
    },
    {
        "name": "forged-document",
        "uuid": "7e927620-b97c-4b00-98c0-8c0184d83d21",
        "meta-category": "file",
    },
    {
        "name": "ftm-Airplane",
        "uuid": "ea720b4a-8849-44a5-a150-eab87b86de2c",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Assessment",
        "uuid": "25330bcb-d629-4d81-bbb9-51cead65175d",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Asset",
        "uuid": "ece6a00c-2f42-4186-bc96-5254aec002a7",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Associate",
        "uuid": "6119ecb3-dedd-44b6-b88f-174585b0b1bf",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Audio",
        "uuid": "92acc7f9-cb98-4b60-93c0-06be77843968",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-BankAccount",
        "uuid": "c51ed099-a628-46ee-ad8f-ffed866b6b8d",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Call",
        "uuid": "4ad4661a-59bb-4171-a47b-18d9e7b6d6d7",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Company",
        "uuid": "b6da52a4-2290-47ad-b316-d31dc3274382",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Contract",
        "uuid": "8bd6b969-ea49-4252-8b03-777dd16598e1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-ContractAward",
        "uuid": "d4857edf-a2c3-479b-bc0a-ef17ec98d0b7",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-CourtCase",
        "uuid": "daa2375c-dc92-42c7-80c0-392500c69771",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-CourtCaseParty",
        "uuid": "9f00c22f-348b-48a9-996b-3ba30de851fe",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Debt",
        "uuid": "7f878885-1ebf-48ee-961a-5ded0f63d593",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Directorship",
        "uuid": "9d9b0af9-9c8c-42c4-8210-388dc3824239",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Document",
        "uuid": "63315c33-2ed0-46dd-8345-9f5f6a80942a",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Documentation",
        "uuid": "a5a0c1dd-4438-4520-875d-1e7cf4bcda7d",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-EconomicActivity",
        "uuid": "ab680ac3-7f3f-4282-883c-d3920c63c8b2",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Email",
        "uuid": "2bafc93f-b99d-4f64-aa74-3252d4ac6030",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Event",
        "uuid": "0f0a252f-a425-46c0-a46a-dabd632d6b59",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Family",
        "uuid": "d81db1ac-7479-4689-8f3e-ad2c8c2b272f",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Folder",
        "uuid": "85e30566-976d-4740-a397-40dda018b37c",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-HyperText",
        "uuid": "be7be26f-c256-4381-939c-dd6eb2675153",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Image",
        "uuid": "50a6a504-c4cc-4905-8628-9e9418f2d325",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Land",
        "uuid": "83fb4991-ce04-49d7-97c8-448e867c7f02",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-LegalEntity",
        "uuid": "53ff8f46-3cd7-4968-86d2-1faaea02f3a3",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-License",
        "uuid": "4629cf5c-60ee-4292-837a-f48874633c29",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Membership",
        "uuid": "42dbbf3a-8c60-483c-a395-44aaaefc77d1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Message",
        "uuid": "d3b31288-5b6f-4d87-a074-95e6f165af6e",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Organization",
        "uuid": "45678a45-5ac2-4fef-9bbd-bfb947463166",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Ownership",
        "uuid": "2a09b445-c638-40e1-8f52-b95c9156f4d8",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Package",
        "uuid": "f9f13fd9-797c-4e2e-aa17-0ca4a0a60f5c",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Page",
        "uuid": "2d9d7605-5105-445e-9ee8-9e39ad34c5c9",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Pages",
        "uuid": "8e567eab-d893-4a38-9dd9-73442f15ede7",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Passport",
        "uuid": "d3c9ae6a-46bf-4cb7-81c9-bc7b88f8a6e1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Payment",
        "uuid": "f4644f96-64f6-465a-be37-62bca315f791",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Person",
        "uuid": "070e1c5b-7f5a-4322-81ff-9d684172fe36",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-PlainText",
        "uuid": "8f260d94-c712-4fdd-a463-6b2487f8a80d",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-PublicBody",
        "uuid": "7b9ab6fa-f2c7-454c-8f18-893ee14eb46c",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-RealEstate",
        "uuid": "26ee8b91-7806-473e-ba06-639f61562f59",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Representation",
        "uuid": "af3ad283-a112-45a2-b72a-1eeffa7ff457",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Row",
        "uuid": "282c0f7c-be66-41be-a709-b35032016829",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Sanction",
        "uuid": "723833b9-4674-4447-9273-eb548a4f27f1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Succession",
        "uuid": "8850ae9c-847c-4ae8-ad47-5f975c13d934",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Table",
        "uuid": "5ac61342-9fa9-4f07-a578-261709633358",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-TaxRoll",
        "uuid": "92b13f53-cebf-4909-b81e-23fabc1472d0",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-UnknownLink",
        "uuid": "16a29891-df0f-42f7-b466-8b4b718acbfa",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-UserAccount",
        "uuid": "094943f5-41c5-4fad-9d61-60d82bce49b1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Vehicle",
        "uuid": "82378b01-aad3-416b-b678-7af7140f6629",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Vessel",
        "uuid": "2ee3df38-7756-4179-abea-ba8d2fbb7c6c",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Video",
        "uuid": "af4821a6-712f-49d7-8297-92eb8c3b75f1",
        "meta-category": "followthemoney",
    },
    {
        "name": "ftm-Workbook",
        "uuid": "ebedfb2a-c666-4870-9b77-baedb1c34dac",
        "meta-category": "followthemoney",
    },
    {
        "name": "game-cheat",
        "uuid": "ab31f87b-f8ac-4dfc-b610-359302b4e86b",
        "meta-category": "misc",
    },
    {
        "name": "Generalizing Persuasion Framework",
        "uuid": "dc6cdc5f-17d7-4d7b-95fe-86478990c910",
        "meta-category": "misc",
    },
    {
        "name": "geolocation",
        "uuid": "cd6f2238-ba55-4888-82c4-104e6e1acf21",
        "meta-category": "misc",
    },
    {
        "name": "git-vuln-finder",
        "uuid": "caacd757-c324-486d-a429-93b5eb6dff27",
        "meta-category": "vulnerability",
    },
    {
        "name": "github-user",
        "uuid": "4329b5e6-8e6a-4b55-8fd1-9033782017d4",
        "meta-category": "misc",
    },
    {
        "name": "gitlab-user",
        "uuid": "39ef3197-08f5-445f-b3b6-9d4d8604071c",
        "meta-category": "misc",
    },
    {
        "name": "google-safe-browsing",
        "uuid": "1f8af312-dfbb-4572-b894-dabe7c8798d8",
        "meta-category": "network",
    },
    {
        "name": "google-threat-intelligence-report",
        "uuid": "e288e533-2736-438a-8136-26cac06be1e7",
        "meta-category": "misc",
    },
    {
        "name": "greynoise-ip",
        "uuid": "6B14A94A-46E4-4B82-B24D-0DBF8E8B3FD9",
        "meta-category": "network",
    },
    {
        "name": "gtp-attack",
        "uuid": "6b3c48d2-0ca6-4608-9c36-455105439145",
        "meta-category": "network",
    },
    {
        "name": "hashlookup",
        "uuid": "18671816-2524-452e-b031-5fc0fe2ab774",
        "meta-category": "file",
    },
    {
        "name": "hhhash",
        "uuid": "4dbcde93-a4e0-4bee-913c-0988b5259d14",
        "meta-category": "misc",
    },
    {
        "name": "http-request",
        "uuid": "b4a8d163-8110-4239-bfcf-e08f3a9fdf7b",
        "meta-category": "network",
    },
    {
        "name": "identity",
        "uuid": "ae85b960-b507-4de2-a32c-9cfb8f25f990",
        "meta-category": "misc",
    },
    {
        "name": "ilr-impact",
        "uuid": "b995af48-39b2-11e9-b2ab-b77adfee75d1",
        "meta-category": "misc",
    },
    {
        "name": "ilr-notification-incident",
        "uuid": "b8ade604-39b2-11e9-b753-1fd28d3b612c",
        "meta-category": "misc",
    },
    {
        "name": "image",
        "uuid": "ca78ec03-3321-4ed3-9840-9bfd52b91d82",
        "meta-category": "file",
    },
    {
        "name": "impersonation",
        "uuid": "01833a92-d2ff-11e9-8016-d3b988153702",
        "meta-category": "misc",
    },
    {
        "name": "imsi-catcher",
        "uuid": "a64f21b1-2f1b-4298-8243-c45db2c4aa7c",
        "meta-category": "misc",
    },
    {
        "name": "incident",
        "uuid": "38597424-f9bb-4865-9b4b-819172df0334",
        "meta-category": "misc",
    },
    {
        "name": "infrastructure",
        "uuid": "39d64bd7-1264-4b2e-bdd1-31d1c4b38e6c",
        "meta-category": "misc",
    },
    {
        "name": "instant-message",
        "uuid": "5fa51a24-f40f-4696-a77e-d31e26bab5fc",
        "meta-category": "misc",
    },
    {
        "name": "instant-message-group",
        "uuid": "e26becca-2149-4bc0-b3fb-7090d43af28f",
        "meta-category": "misc",
    },
    {
        "name": "integrity-impact",
        "uuid": "604830f2-8035-4454-aa32-7f6eee1f04c6",
        "meta-category": "misc",
    },
    {
        "name": "intel471-vulnerability-intelligence",
        "uuid": "8f8ee946-1383-4139-b4da-ad8c5aceac07",
        "meta-category": "vulnerability",
    },
    {
        "name": "intelmq_event",
        "uuid": "491ac7d2-25a1-4078-8246-b04a132d003d",
        "meta-category": "network",
    },
    {
        "name": "intelmq_report",
        "uuid": "c3d34be1-904b-455b-bceb-509418392110",
        "meta-category": "network",
    },
    {
        "name": "internal-reference",
        "uuid": "a3984dc5-5f70-4776-9262-c19641c0ff6a",
        "meta-category": "misc",
    },
    {
        "name": "interpol-notice",
        "uuid": "24927972-1e4a-11e9-857e-3b2306b99911",
        "meta-category": "misc",
    },
    {
        "name": "intrusion-set",
        "uuid": "bfe96eae-e37a-4ecf-8012-1cdb478571a5",
        "meta-category": "misc",
    },
    {
        "name": "iot-device",
        "uuid": "3de3b92a-859b-431b-9c4f-1a81de1d9637",
        "meta-category": "iot",
    },
    {
        "name": "iot-firmware",
        "uuid": "8bafb8fc-d986-4a58-b22b-6b8c7c0e8b70",
        "meta-category": "iot",
    },
    {
        "name": "ip-api-address",
        "uuid": "4336f124-6264-4f72-943e-cc3797e4122b",
        "meta-category": "network",
    },
    {
        "name": "ip-port",
        "uuid": "9f8cea74-16fe-4968-a2b4-026676949ac6",
        "meta-category": "network",
    },
    {
        "name": "irc",
        "uuid": "4bbbc004-c344-4b20-8672-b41102177fc7",
        "meta-category": "network",
    },
    {
        "name": "ja3",
        "uuid": "09b45449-5d6e-492c-a68a-cb2e188cbfac",
        "meta-category": "network",
    },
    {
        "name": "ja3s",
        "uuid": "7f377f66-d128-4b97-897f-592d06ba2ff7",
        "meta-category": "network",
    },
    {
        "name": "ja4-plus",
        "uuid": "2c15c75e-e7db-4b62-8d17-633e7571818f",
        "meta-category": "network",
    },
    {
        "name": "jarm",
        "uuid": "8220ce60-ce3f-4be4-afa9-743f94ec37e0",
        "meta-category": "network",
    },
    {
        "name": "keybase-account",
        "uuid": "32c29c1c-a6c1-41e9-b1db-8cca88185ecd",
        "meta-category": "misc",
    },
    {
        "name": "language-content",
        "uuid": "dff53cb1-d98d-4898-b4d2-85bd8b44929c",
        "meta-category": "misc",
    },
    {
        "name": "leaked-document",
        "uuid": "ea145ecd-b3c2-4f57-ac11-c16e883c4247",
        "meta-category": "file",
    },
    {
        "name": "legal-entity",
        "uuid": "14f5688f-d89c-469f-9878-c48bf6c41c65",
        "meta-category": "misc",
    },
    {
        "name": "lnk",
        "uuid": "ad13533e-1853-4da0-a111-33a7ce7e6c09",
        "meta-category": "file",
    },
    {
        "name": "macho",
        "uuid": "23fb8371-c7e3-45fe-b897-fdf074f95267",
        "meta-category": "file",
    },
    {
        "name": "macho-section",
        "uuid": "fca3c534-d188-4964-9c6e-9922e1dfe66e",
        "meta-category": "file",
    },
    {
        "name": "mactime-timeline-analysis",
        "uuid": "58149b06-eabe-4937-9dac-01d63f504e14",
        "meta-category": "file",
    },
    {
        "name": "malware",
        "uuid": "e5ad1d64-4b4e-44f5-9e00-88a705a67f9d",
        "meta-category": "misc",
    },
    {
        "name": "malware-analysis",
        "uuid": "8229ee82-7218-4ff5-9eac-57961a6f0288",
        "meta-category": "misc",
    },
    {
        "name": "malware-config",
        "uuid": "8200b79b-1d8c-49a8-9a63-7710e613c059",
        "meta-category": "file",
    },
    {
        "name": "meme-image",
        "uuid": "6f6c3b61-f085-475e-93df-2e2d9c2fb0f6",
        "meta-category": "file",
    },
    {
        "name": "microblog",
        "uuid": "8ec8c911-ddbe-4f5b-895b-fbff70c42a60",
        "meta-category": "misc",
    },
    {
        "name": "monetary-impact",
        "uuid": "3376296c-c1ef-4847-979f-2bfc49aa983e",
        "meta-category": "misc",
    },
    {
        "name": "mutex",
        "uuid": "9f5c1a68-2021-4faa-b409-61c899c86466",
        "meta-category": "misc",
    },
    {
        "name": "narrative",
        "uuid": "83bea299-514a-4719-a84b-f6fd0997fac1",
        "meta-category": "misc",
    },
    {
        "name": "netflow",
        "uuid": "bf148c58-3e7e-414e-8de8-5d96379ca77e",
        "meta-category": "network",
    },
    {
        "name": "network-connection",
        "uuid": "af16764b-f8e5-4603-9de1-de34d272f80b",
        "meta-category": "network",
    },
    {
        "name": "network-profile",
        "uuid": "f0f9e287-8067-49a4-b0f8-7a0fed8d4e43",
        "meta-category": "network",
    },
    {
        "name": "network-socket",
        "uuid": "48bbfd72-ef8e-4649-b14d-41b4b5a0eba2",
        "meta-category": "network",
    },
    {
        "name": "network-traffic",
        "uuid": "16290b18-9af5-4a43-b195-75fe1eef0c35",
        "meta-category": "network",
    },
    {
        "name": "news-agency",
        "uuid": "92b3f7fd-c4bc-42af-a73b-033ace439622",
        "meta-category": "misc",
    },
    {
        "name": "news-media",
        "uuid": "691463c5-5302-4847-9bec-4c56ccfec677",
        "meta-category": "misc",
    },
    {
        "name": "open-data-security",
        "uuid": "01f9d45f-134d-4f99-9891-7d1219af5941",
        "meta-category": "misc",
    },
    {
        "name": "organization",
        "uuid": "f750e12b-127a-432c-b022-b3f9153c4e2a",
        "meta-category": "misc",
    },
    {
        "name": "original-imported-file",
        "uuid": "4cd560e9-2cfe-40a1-9964-7b2e797ecac5",
        "meta-category": "file",
    },
    {
        "name": "paloalto-threat-event",
        "uuid": "e6fa7a87-1173-43d6-86c2-b4d02af5fc74",
        "meta-category": "network",
    },
    {
        "name": "parler-account",
        "uuid": "8d5ba58e-cac3-46a6-9d1f-cf236f7e95c9",
        "meta-category": "misc",
    },
    {
        "name": "parler-comment",
        "uuid": "86db742e-b86a-40f3-945f-96ab4e305cd6",
        "meta-category": "misc",
    },
    {
        "name": "parler-post",
        "uuid": "db85b789-df44-4522-8006-b611e52da5b2",
        "meta-category": "misc",
    },
    {
        "name": "passive-dns",
        "uuid": "b77b7b1c-66ab-4a41-8da4-83810f6d2d6c",
        "meta-category": "network",
    },
    {
        "name": "passive-dns-dnsdbflex",
        "uuid": "e5066302-be0d-11eb-ab6d-2bb17990cb48",
        "meta-category": "network",
    },
    {
        "name": "passive-ssh",
        "uuid": "ec350cdf-2311-4df5-972a-a4342a2c0065",
        "meta-category": "network",
    },
    {
        "name": "paste",
        "uuid": "cedc055c-78aa-49a4-bfd7-4cc30cecef12",
        "meta-category": "misc",
    },
    {
        "name": "pcap-metadata",
        "uuid": "0784aefa-ec3a-4eca-a431-c31ed7058bd3",
        "meta-category": "network",
    },
    {
        "name": "pe",
        "uuid": "cf7adecc-d4f0-4e88-9d90-f978ee151a07",
        "meta-category": "file",
    },
    {
        "name": "pe-optional-header",
        "uuid": "ebde65ab-ce98-413d-a518-8f37bc79bcb9",
        "meta-category": "file",
    },
    {
        "name": "pe-section",
        "uuid": "198a17d2-a135-4b25-9a32-5aa4e632014a",
        "meta-category": "file",
    },
    {
        "name": "Deception PersNOna",
        "uuid": "a80828dc-07bf-4d5c-ab82-8160ee5bdd6d",
        "meta-category": "misc",
    },
    {
        "name": "person",
        "uuid": "a15b0477-e9d1-4b9c-9546-abe78a4f4248",
        "meta-category": "misc",
    },
    {
        "name": "personification",
        "uuid": "102a8696-420b-486d-806d-70a34d2f4e54",
        "meta-category": "misc",
    },
    {
        "name": "pgp-meta",
        "uuid": "4c9134c4-b3e8-4d9f-b3c0-c683e70ec1dd",
        "meta-category": "misc",
    },
    {
        "name": "phishing",
        "uuid": "2dad6f9d-d425-4217-8fda-0b0a2d815307",
        "meta-category": "network",
    },
    {
        "name": "phishing-kit",
        "uuid": "f452c16b-12fa-4f87-84a2-15a9e8ca6e7c",
        "meta-category": "network",
    },
    {
        "name": "phone",
        "uuid": "d7e4fbdd-b551-4862-bddb-a0b470a38509",
        "meta-category": "misc",
    },
    {
        "name": "phone-number",
        "uuid": "c4b5a67c-63d2-11ec-90d6-0242ac120003",
        "meta-category": "mobile",
    },
    {
        "name": "physical-impact",
        "uuid": "ae979b91-5896-46f7-ad70-4f3036d79251",
        "meta-category": "misc",
    },
    {
        "name": "postal-address",
        "uuid": "c22cdd17-d38e-42d3-a365-4febdaaaf25e",
        "meta-category": "misc",
    },
    {
        "name": "probabilistic-data-structure",
        "uuid": "026b939b-d737-4a88-8222-03b3d55df303",
        "meta-category": "file",
    },
    {
        "name": "process",
        "uuid": "02aeef94-ac23-455c-addb-731757ceafb5",
        "meta-category": "misc",
    },
    {
        "name": "publication",
        "uuid": "8a86b056-7f2c-4c1b-b04e-a6bac4443068",
        "meta-category": "misc",
    },
    {
        "name": "python-etvx-event-log",
        "uuid": "94e3aee9-cb99-4503-9bf6-7da3db5de55e",
        "meta-category": "misc",
    },
    {
        "name": "query",
        "uuid": "006539b3-f68a-4a02-a213-e600762d39b5",
        "meta-category": "misc",
    },
    {
        "name": "r2graphity",
        "uuid": "b6abe0e0-52ea-4424-ba42-761c2e027b76",
        "meta-category": "file",
    },
    {
        "name": "ransom-negotiation",
        "uuid": "FB72F951-DE2E-4B54-A570-8FC560A74B06",
        "meta-category": "financial",
    },
    {
        "name": "ransomware-group-post",
        "uuid": "52a0e179-4942-41e6-90f5-7db856fd6f39",
        "meta-category": "misc",
    },
    {
        "name": "reddit-account",
        "uuid": "6802f885-2003-494a-b234-61aadce62731",
        "meta-category": "misc",
    },
    {
        "name": "reddit-comment",
        "uuid": "0a7e5fc0-fe6a-43c7-a957-de3269c2eb6c",
        "meta-category": "misc",
    },
    {
        "name": "reddit-post",
        "uuid": "e5ed7e7f-2e21-44ff-839f-e58d9818f17f",
        "meta-category": "misc",
    },
    {
        "name": "reddit-subreddit",
        "uuid": "5a00464c-5379-4e66-ab21-d356ba426155",
        "meta-category": "misc",
    },
    {
        "name": "regexp",
        "uuid": "ceffad66-71e5-4e20-9370-1b3fb694c648",
        "meta-category": "misc",
    },
    {
        "name": "registry-key",
        "uuid": "8b3228ad-6d82-4fe6-b2ae-05426308f1d5",
        "meta-category": "file",
    },
    {
        "name": "registry-key-value",
        "uuid": "4626a273-72c1-48d3-8595-ff48ea2277f7",
        "meta-category": "file",
    },
    {
        "name": "regripper-NTUser",
        "uuid": "f9dc7b7e-8ab1-4dde-95d9-67e41b461c65",
        "meta-category": "misc",
    },
    {
        "name": "regripper-sam-hive-single-user",
        "uuid": "112efd9a-2137-4198-92ed-7c91043e2cd4",
        "meta-category": "misc",
    },
    {
        "name": "regripper-sam-hive-user-group",
        "uuid": "b924bae1-2dec-4d2d-a8c2-b03305222b7c",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-BHO",
        "uuid": "e7b46b5a-d2d2-4a05-bc25-2ac8d4683ae2",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-appInit-DLLS",
        "uuid": "7893be05-8398-451e-ab1e-5e25ea4a8859",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-application-paths",
        "uuid": "9f2d3c9b-9a82-42a7-82c2-733115d101c8",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-applications-installed",
        "uuid": "7a8fb6b4-cbbd-4de5-b893-7b0a5c4858cd",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-command-shell",
        "uuid": "a7dc3697-89ce-46dc-a64d-0b1015457978",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-software-run",
        "uuid": "4bae06d1-3996-4028-88ec-7c7d54cc1d94",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-userprofile-winlogon",
        "uuid": "df03d0e4-3e6b-4e56-951a-142eae4cad59",
        "meta-category": "misc",
    },
    {
        "name": "regripper-software-hive-windows-general-info",
        "uuid": "03200c25-4bf5-4282-9852-001a51ab20f1",
        "meta-category": "misc",
    },
    {
        "name": "regripper-system-hive-firewall-configuration",
        "uuid": "d9839b3c-c013-4ba7-b5e5-2787198b9e07",
        "meta-category": "misc",
    },
    {
        "name": "regripper-system-hive-general-configuration",
        "uuid": "5ac85401-cbf1-4d05-a85e-1784546881e4",
        "meta-category": "misc",
    },
    {
        "name": "regripper-system-hive-network-information",
        "uuid": "a5a3ba3a-ba2e-42a4-be45-b36809ae56f0",
        "meta-category": "misc",
    },
    {
        "name": "regripper-system-hive-services-drivers",
        "uuid": "78cdae45-2061-4b49-b1d6-71f562094a73",
        "meta-category": "misc",
    },
    {
        "name": "report",
        "uuid": "70a68471-df22-4e3f-aa1a-5a3be19f82df",
        "meta-category": "misc",
    },
    {
        "name": "research-scanner",
        "uuid": "d690e956-fc8a-11e8-8eb2-f2801f1b9fd1",
        "meta-category": "network",
    },
    {
        "name": "risk-assessment-report",
        "uuid": "72989321-6866-40c6-a9b5-4c5869ec2a76",
        "meta-category": "misc",
    },
    {
        "name": "rogue-dns",
        "uuid": "b7e7859b-6872-4fd2-ac49-f66ccb904505",
        "meta-category": "network",
    },
    {
        "name": "rtir",
        "uuid": "7534ee19-0a1f-4f46-a197-e6e73e457943",
        "meta-category": "misc",
    },
    {
        "name": "sandbox-report",
        "uuid": "4d3fffd2-cd07-4357-96e0-a51c988faaef",
        "meta-category": "misc",
    },
    {
        "name": "sb-signature",
        "uuid": "984c5c39-be7f-4e1e-b034-d3213bac51cb",
        "meta-category": "misc",
    },
    {
        "name": "scan-result",
        "uuid": "ebe2a359-8f5b-4a45-8106-d1678935b4c4",
        "meta-category": "network",
    },
    {
        "name": "scheduled-event",
        "uuid": "40ba0098-cfd8-4b54-b5a8-9adcdf47533d",
        "meta-category": "misc",
    },
    {
        "name": "scheduled-task",
        "uuid": "076f9362-23f7-4326-b370-a98e47531a44",
        "meta-category": "misc",
    },
    {
        "name": "scrippsco2-c13-daily",
        "uuid": "5f71a99e-4a56-45b5-b7d6-19949d22409a",
        "meta-category": "climate",
    },
    {
        "name": "scrippsco2-c13-monthly",
        "uuid": "812125c7-47de-4503-8bbc-19067d3a1c38",
        "meta-category": "climate",
    },
    {
        "name": "scrippsco2-co2-daily",
        "uuid": "0779baca-06b9-491e-9ab7-ccc3e1538fd3",
        "meta-category": "climate",
    },
    {
        "name": "scrippsco2-co2-monthly",
        "uuid": "3350fc46-7120-4fb1-b5b3-c931465c9b2a",
        "meta-category": "climate",
    },
    {
        "name": "scrippsco2-o18-daily",
        "uuid": "8b6878a7-577d-4845-b165-ead6e58bec04",
        "meta-category": "climate",
    },
    {
        "name": "scrippsco2-o18-monthly",
        "uuid": "86bd588b-cd0c-486a-8ea0-17fd95312fa0",
        "meta-category": "climate",
    },
    {
        "name": "script",
        "uuid": "6bce7d01-dbec-4054-b3c2-3655a19382e2",
        "meta-category": "misc",
    },
    {
        "name": "security-playbook",
        "uuid": "48894c92-447b-4abe-b093-360c4d823e9d",
        "meta-category": "misc",
    },
    {
        "name": "shadowserver-malware-url-report",
        "uuid": "0211496c-dbcf-465b-a147-3d965da016cc",
        "meta-category": "misc",
    },
    {
        "name": "shadowserver-scan-http-proxy",
        "uuid": "ad0c83d5-56bf-4300-8743-ed2b4caf6206",
        "meta-category": "misc",
    },
    {
        "name": "shell-commands",
        "uuid": "fee65efa-eb64-4516-8611-1db76c589f79",
        "meta-category": "misc",
    },
    {
        "name": "shodan-report",
        "uuid": "10b03d93-3694-4a79-9cd1-4a273746303a",
        "meta-category": "network",
    },
    {
        "name": "short-message-service",
        "uuid": "4851a3dc-e1a6-43ac-9d97-f0d13a099fd2",
        "meta-category": "misc",
    },
    {
        "name": "shortened-link",
        "uuid": "361c0ae8-68bd-11e8-adc0-fa7ae01bbebc",
        "meta-category": "network",
    },
    {
        "name": "sigma",
        "uuid": "aa21a3cd-ab2c-442a-9999-a5e6626591ec",
        "meta-category": "misc",
    },
    {
        "name": "sigmf-archive",
        "uuid": "5985d34d-3657-4828-9788-470175bcc3b1",
        "meta-category": "misc",
    },
    {
        "name": "sigmf-expanded-recording",
        "uuid": "f1c2c4e1-d3bf-46b1-b34d-f5e9544a4795",
        "meta-category": "misc",
    },
    {
        "name": "sigmf-recording",
        "uuid": "0ca64648-38ca-4e48-99ce-2e655cdac02c",
        "meta-category": "misc",
    },
    {
        "name": "social-media-group",
        "uuid": "c4939ec4-ab53-4c35-9a98-3d4d4caf5b6c",
        "meta-category": "misc",
    },
    {
        "name": "software",
        "uuid": "b1b5dc0e-73fe-443c-8d9d-0e208de3951e",
        "meta-category": "misc",
    },
    {
        "name": "spearphishing-attachment",
        "uuid": "5dfcd9a9-d10c-48ae-9ba4-13c2428a994a",
        "meta-category": "network",
    },
    {
        "name": "spearphishing-link",
        "uuid": "4e758e53-6c84-47b0-a19b-362f587059e2",
        "meta-category": "network",
    },
    {
        "name": "splunk",
        "uuid": "fd9b7bf8-df7b-4df9-bcd8-28591edcaab8",
        "meta-category": "misc",
    },
    {
        "name": "ss7-attack",
        "uuid": "f3493d8b-a7ab-48d0-a775-046c4d64d782",
        "meta-category": "network",
    },
    {
        "name": "ssh-authorized-keys",
        "uuid": "d1db3e4d-c932-4d8b-a915-4cff088cb678",
        "meta-category": "network",
    },
    {
        "name": "stairwell",
        "uuid": "113d31ab-6eea-46df-976c-e955c369acd2",
        "meta-category": "file",
    },
    {
        "name": "stix2-pattern",
        "uuid": "0c5bd072-7c3e-4d45-86f7-a8104d9143b9",
        "meta-category": "misc",
    },
    {
        "name": "stock",
        "uuid": "dd3e00b2-977e-4cf4-9d12-0b009a00a721",
        "meta-category": "misc",
    },
    {
        "name": "submarine",
        "uuid": "c8e0c039-0ada-486a-b446-2686709e1e28",
        "meta-category": "misc",
    },
    {
        "name": "suricata",
        "uuid": "3c177337-fb80-405a-a6c1-1b2ddea8684a",
        "meta-category": "network",
    },
    {
        "name": "target-system",
        "uuid": "3110944f-eca0-4c94-9d61-a84d022228a4",
        "meta-category": "internal",
    },
    {
        "name": "task",
        "uuid": "384734e7-8710-4ab0-901a-6f0e73a551e6",
        "meta-category": "misc",
    },
    {
        "name": "tattoo",
        "uuid": "747976fc-d637-4730-8b64-93f7f2814506",
        "meta-category": "misc",
    },
    {
        "name": "telegram-account",
        "uuid": "06f02ecf-5afb-42c5-9cb0-b362e222f52c",
        "meta-category": "misc",
    },
    {
        "name": "telegram-bot",
        "uuid": "e2cb6c8f-45fa-429d-9cdb-05298ab21f46",
        "meta-category": "misc",
    },
    {
        "name": "temporal-event",
        "uuid": "d79f2d25-2937-44d3-a6d4-2f36f2505448",
        "meta-category": "misc",
    },
    {
        "name": "thaicert-group-cards",
        "uuid": "f42db88d-1889-4c2f-a903-971cf8e65174",
        "meta-category": "misc",
    },
    {
        "name": "threatgrid-report",
        "uuid": "23b3576b-2e68-4a86-a103-68820daef1d5",
        "meta-category": "misc",
    },
    {
        "name": "timecode",
        "uuid": "60141eac-71d2-4173-930d-91dba8106c40",
        "meta-category": "misc",
    },
    {
        "name": "timesketch-timeline",
        "uuid": "06db0221-cbc0-4ffc-ad98-7f34549310f1",
        "meta-category": "misc",
    },
    {
        "name": "timesketch_message",
        "uuid": "ef27fb19-7e71-43e0-b6f6-6f03ab67666f",
        "meta-category": "misc",
    },
    {
        "name": "timestamp",
        "uuid": "c8c91e23-4221-4533-8bf7-64e12b05f265",
        "meta-category": "misc",
    },
    {
        "name": "tor-hiddenservice",
        "uuid": "cbac07d6-fbe9-43b8-8d91-d515812ce330",
        "meta-category": "misc",
    },
    {
        "name": "tor-node",
        "uuid": "a5fde1c8-318e-4658-a3ea-85ea000bdd33",
        "meta-category": "misc",
    },
    {
        "name": "traceability-impact",
        "uuid": "1dd26500-6246-4750-ad47-94ae4e200d8f",
        "meta-category": "misc",
    },
    {
        "name": "tracking-id",
        "uuid": "3681c62a-2c75-48d8-99f2-6a3444ce2393",
        "meta-category": "network",
    },
    {
        "name": "transaction",
        "uuid": "a47fa26a-01b6-4747-a394-5144e34456dc",
        "meta-category": "financial",
    },
    {
        "name": "translation",
        "uuid": "a43b54fa-dac9-11e9-9b0d-97296aceae1a",
        "meta-category": "misc",
    },
    {
        "name": "transport-ticket",
        "uuid": "8d6bd699-86f8-477c-aac3-a7f273c19266",
        "meta-category": "misc",
    },
    {
        "name": "trustar_report",
        "uuid": "8ff46cf1-db04-4453-ba46-d004e1ef6b7a",
        "meta-category": "network",
    },
    {
        "name": "tsk-chats",
        "uuid": "6b71f231-c502-467f-bc67-1423cd5bf800",
        "meta-category": "misc",
    },
    {
        "name": "tsk-web-bookmark",
        "uuid": "7d9a88a8-9934-4caa-a85b-f76bc97d5373",
        "meta-category": "misc",
    },
    {
        "name": "tsk-web-cookie",
        "uuid": "40d23a4f-43be-4c9e-8328-382a2188eb1d",
        "meta-category": "misc",
    },
    {
        "name": "tsk-web-downloads",
        "uuid": "ab9603a1-9dcc-48e8-a51c-b8bccc7bcc26",
        "meta-category": "file",
    },
    {
        "name": "tsk-web-history",
        "uuid": "e1325e52-e52e-49b1-89ad-d503c127c698",
        "meta-category": "misc",
    },
    {
        "name": "tsk-web-search-query",
        "uuid": "16b3f8d0-fd09-4812-a42c-b5aeff2d4c2e",
        "meta-category": "misc",
    },
    {
        "name": "twitter-account",
        "uuid": "8066563f-881e-4f6a-9d6c-a9d15b8658bb",
        "meta-category": "misc",
    },
    {
        "name": "twitter-list",
        "uuid": "7ae81d5c-d9d8-4812-88a7-5f14fba241da",
        "meta-category": "misc",
    },
    {
        "name": "twitter-post",
        "uuid": "d1214031-ce1b-4a35-bd33-644c707bda2e",
        "meta-category": "misc",
    },
    {
        "name": "typosquatting-finder",
        "uuid": "3414fbe7-6f8c-4ed5-bc51-9a11a3a29822",
        "meta-category": "network",
    },
    {
        "name": "typosquatting-finder-result",
        "uuid": "22151d90-b39b-498c-86c7-126ddd2e1a55",
        "meta-category": "network",
    },
    {
        "name": "url",
        "uuid": "60efb77b-40b5-4c46-871b-ed1ed999fce5",
        "meta-category": "network",
    },
    {
        "name": "user-account",
        "uuid": "49606b06-22f0-4ac8-8eee-2f12ad46f3d3",
        "meta-category": "misc",
    },
    {
        "name": "user-action",
        "uuid": "699dcf9d-2fa2-4200-a5cf-1d1e124e28c1",
        "meta-category": "misc",
    },
    {
        "name": "vehicle",
        "uuid": "683c076c-f695-4ff2-8efa-e98a418049f4",
        "meta-category": "misc",
    },
    {
        "name": "victim",
        "uuid": "a8806e40-39ad-435f-be02-ac2a13d6fc7d",
        "meta-category": "misc",
    },
    {
        "name": "virustotal-graph",
        "uuid": "9b421055-b1bb-4c33-9ead-7fa3f39e2232",
        "meta-category": "misc",
    },
    {
        "name": "virustotal-report",
        "uuid": "d7dd0154-e04f-4c34-a2fb-79f3a3a52aa4",
        "meta-category": "misc",
    },
    {
        "name": "virustotal-submission",
        "uuid": "473d289b-f1d4-4f02-a4fe-3b69f534ed45",
        "meta-category": "misc",
    },
    {
        "name": "vulnerability",
        "uuid": "81650945-f186-437b-8945-9f31715d32da",
        "meta-category": "vulnerability",
    },
    {
        "name": "weakness",
        "uuid": "b8713fc0-d7a2-4b27-a182-38ed47966802",
        "meta-category": "vulnerability",
    },
    {
        "name": "whois",
        "uuid": "429faea1-34ff-47af-8a00-7c62d3be5a6a",
        "meta-category": "network",
    },
    {
        "name": "windows-service",
        "uuid": "7598cc63-7ba3-4d0a-91c0-b875c6013035",
        "meta-category": "misc",
    },
    {
        "name": "x-header",
        "uuid": "9a7028df-e238-45e8-893c-8e67d273fb61",
        "meta-category": "network",
    },
    {
        "name": "x509",
        "uuid": "d1ab756a-26b5-4349-9f43-765630f0911c",
        "meta-category": "network",
    },
    {
        "name": "yabin",
        "uuid": "35b4dd03-4fa9-4e0e-97d8-a2867b11c956",
        "meta-category": "file",
    },
    {
        "name": "yara",
        "uuid": "b5acf82e-ecca-4868-82fe-9dbdf4d808c3",
        "meta-category": "misc",
    },
    {
        "name": "youtube-channel",
        "uuid": "cb9f492b-9930-4388-98e1-5d0cdcfa51df",
        "meta-category": "misc",
    },
    {
        "name": "youtube-comment",
        "uuid": "218bc1ae-c5ee-452b-895d-a26e0beaa550",
        "meta-category": "misc",
    },
    {
        "name": "youtube-playlist",
        "uuid": "5a5e7441-c048-4e4b-bab7-642a91d30935",
        "meta-category": "misc",
    },
    {
        "name": "youtube-video",
        "uuid": "2bd68462-a509-4320-b5c6-760a57fd1a80",
        "meta-category": "misc",
    },
]
