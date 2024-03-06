import json
from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, ErrorPluginResponse, PluginResponse, SuccessPluginResponse, FailPluginResponse


class MassUserImport(BasePlugin):
    name = 'Mass User Import'
    description = 'Allow to quickly import many users'
    icon = 'fas fa-users'
    action_parameters = [
        PluginResponse.genActionParameter('payload', 'textarea', 'Users CSV', 'The CSV of the users to import', 'email,password,organisation_id,role_id'),
    ]

    def action(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        print('action')
        payload = data.get('payload', '')

        try:
            users = MassUserImport.getUsersFromPayload(payload)
        except Exception as e:
            return ErrorPluginResponse({}, [f'Invalid parameters (payload: `{payload}`)', str(e)])
        if not users:
            return ErrorPluginResponse({}, [f'Invalid parameters (payload: `{payload}`)'])

        result = MassUserImport.createUsers(server, users)
        return result


    @classmethod
    def getUsersFromPayload(cls, payload: str) -> PluginResponse:
        users = []
        for line in payload.splitlines():
            params = line.split(',') # email,password,org_id,role_id
            user = {
                'email': params[0],
                'password': params[1],
                'org_id': params[2],
                'role_id': params[3],
                'change_pw': 0,
            }
            users.append(user)
        return users


    @classmethod
    def createUsers(cls, server: Server, users: list) -> PluginResponse:
        if users is None:
            return ErrorPluginResponse({}, [f'Invalid parameters (payload: `{users}`)'])

        errors = []
        successCount = 0
        errorCount = 0
        for user in users:
            success = MassUserImport.addUser(server, user)
            if success is not True:
                errorCount += 1
                errors.append(success)
            else:
                successCount += 1

        if successCount > 0:
                successMessage = f"Successfully created {successCount} users."
                if errorCount > 0:
                    successMessage += f" {errorCount} users could not be created"
                data = {
                    'message': successMessage,
                    'data': {
                        'successes': successCount,
                        'errors': errors,
                    }
                }
                return SuccessPluginResponse(data, errors)
        else:
            failMessage = f"Count not create any users. {errorCount} Failed to be created"
            data = {
                'message': failMessage,
                'data': {
                    'successes': successCount,
                    'errors': errors,
                }
            }
            return FailPluginResponse(data, errors)

    @classmethod
    def addUser(cls, server: Server, user: dict):
        url = '/admin/users/add'
        result = mispPostRequest(server, url, data=user, rawResponse=True, nocache=True)
        data = result.json()
        if 'error' in data:
            actionResponse = data['error']
        else:
            if result.ok:
                actionResponse = True
            else:
                if 'error' in data:
                    return data['error']
                elif 'errors' in data:
                    return user['email'] + ' - ' + ', '.join(list(data['errors'].values())[0])
                actionResponse = data

        return actionResponse
