from typing import List, Optional, Union
from application.DBModels import Server
from application.controllers.utils import mispGetRequest
from application.health.versions import GITHUB_LATEST_RELEASE_URL, how_far_behind, latest_release, parse_version
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse
from requests import Response


class UpToDate(BasePlugin):
    name = 'Up-To-Date'
    description = 'Check if the server is up-to-date based on the latest GitHub release'
    icon = 'far fa-arrow-alt-circle-up'
    githubURL = GITHUB_LATEST_RELEASE_URL
    quickActionName = 'Run Updates'
    quickActionIcon = 'arrow-up'
    quickActionVariant = 'outline-primary'

    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        upToDateStatus = UpToDate.getStatus(server)
        upToDate = upToDateStatus['up_to_date']
        data = {
            "component": "badge",
            "variant": "secondary" if upToDate is None else ("success" if upToDate else "danger"),
            "text": upToDateStatus['current'],
            "title": f"Latest release {upToDateStatus['github']}"
        }
        return SuccessPluginResponse(data, None, 'bootstrapElement')

    def index(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return self.view(server, data)

    def quickAction(self, server: Server, data: Optional[dict] = {}) -> Union[PluginResponse, List[PluginResponse]]:
        updateResult = UpToDate.doUpdate(server)
        if 'error' in updateResult:
            return FailPluginResponse({}, updateResult['error'])
        data = updateResult.json()
        data['message'] = f"Server `{server.name}` updated"
        return SuccessPluginResponse(data, None, None, updateResult)


    @classmethod
    def queryVersion(cls, server: Server) -> str:
        testConnection = mispGetRequest(server, '/servers/getVersion')
        if not isinstance(testConnection, dict) or 'error' in testConnection or not testConnection.get('version'):
            return '?'
        return testConnection['version']

    @classmethod
    def queryGithub(cls) -> str:
        return latest_release() or '?'

    @classmethod
    def tokenizeMISPVersion(cls, versionString: str) -> dict:
        version = parse_version(versionString)
        if version is None:
            return {"major": '?', "minor": '?', "patch": '?'}
        return {"major": str(version[0]), "minor": str(version[1]), "patch": str(version[2])}

    @classmethod
    def getStatus(cls, server: Server) -> dict:
        current = cls.queryVersion(server)
        github = cls.queryGithub()
        data = {
            "current": current,
            "current_tokenized": cls.tokenizeMISPVersion(current),
            "github": github,
            "github_tokenized": cls.tokenizeMISPVersion(github),
            "up_to_date": cls.isUpToDate(github, current),
        }
        return data

    @classmethod
    def isUpToDate(cls, github_version: str, current_version: str) -> Optional[bool]:
        """None when either version is unknown. A server newer than the latest release is up to date"""
        current, latest = parse_version(current_version), parse_version(github_version)
        if current is None or latest is None:
            return None
        return how_far_behind(current, latest) is None

    @classmethod
    def doUpdate(cls, server: Server) -> Union[dict, Response]:
        # return mispPostRequest(server, '/servers/update', rawResponse=True, nocache=True)
        return mispGetRequest(server, '/servers/getVersion', rawResponse=True, nocache=True)
