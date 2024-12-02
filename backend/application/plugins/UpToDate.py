from datetime import timedelta
from typing import List, Optional, Union
from requests_cache import CachedSession
from application.DBModels import Server
from application.controllers.utils import mispGetRequest, mispPostRequest
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse, FailPluginResponse
from requests import Response


requestGithubSession = CachedSession(cache_name='github_cache', expire_after=timedelta(minutes=10))

class UpToDate(BasePlugin):
    name = 'Up-To-Date'
    description = 'Check if the server is up-to-date based on the latest GitHub release'
    icon = 'far fa-arrow-alt-circle-up'
    githubURL = "https://api.github.com/repos/MISP/MISP/releases/latest"
    quickActionName = 'Run Updates'
    quickActionIcon = 'arrow-up'
    quickActionVariant = 'outline-primary'

    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        upToDateStatus = UpToDate.getStatus(server)
        upToDate = upToDateStatus['up_to_date']
        data = {
            "component": "badge",
            "variant": "success" if upToDate else "danger",
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
        if 'error' in testConnection:
            return '?'
        current_version = testConnection['version']
        return current_version

    @classmethod
    def queryGithub(cls) -> str:
        github_version_r = requestGithubSession.get(cls.githubURL)
        # if github_version_r == 200:
        #     github_version = github_version_r.json()['tag_name']
        # else:
        #     github_version = '?'
        try:
            github_version = github_version_r.json()['tag_name']
        except:
            github_version = '?'
        return github_version

    @classmethod
    def tokenizeMISPVersion(cls, versionString: str) -> dict:
        version = {}
        if versionString == '?':
            version = {
                "major": '?',
                "minor": '?',
                "patch": '?',
            }
        else:
            if versionString.startswith("v"):
                versionString = versionString[1:]
            arr = versionString.split(".")
            version = {
                "major": arr[0],
                "minor": arr[1],
                "patch": arr[2]
            }
        return version

    @classmethod
    def getStatus(cls, server: Server) -> dict:
        current = cls.queryVersion(server)
        currentTokenized = cls.tokenizeMISPVersion(current)
        github = cls.queryGithub()
        githubTokenized = cls.tokenizeMISPVersion(github)
        data = {
            "current": current,
            "current_tokenized": currentTokenized,
            "github": github,
            "github_tokenized": githubTokenized,
            "up_to_date": UpToDate.isUpToDate(githubTokenized, currentTokenized)
        }
        return data

    @classmethod
    def isUpToDate(cls, github_version: dict, current_version: dict) -> bool:
        return github_version['major'] == current_version['major'] and \
            github_version['minor'] == current_version['minor'] and \
            github_version['patch'] == current_version['patch']

    @classmethod
    def doUpdate(cls, server: Server) -> Union[dict, Response]:
        # return mispPostRequest(server, '/servers/update', rawResponse=True, nocache=True)
        return mispGetRequest(server, '/servers/getVersion', rawResponse=True, nocache=True)
