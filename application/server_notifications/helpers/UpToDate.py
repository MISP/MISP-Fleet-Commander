from .baseNotificationHelper import baseNotificationHelper, Severity
from application.controllers.utils import mispGetRequest, mispPostRequest
import requests

class UpToDate(baseNotificationHelper):
    name = "Up To Date"
    githubURL = "https://api.github.com/repos/MISP/MISP/releases/latest"

    def query(self):
        testConnection = mispGetRequest(self.server, '/servers/getVersion')
        if 'error' in testConnection:
            return []
        current_version = testConnection['version']
        github_version = requests.get(self.githubURL).json()['tag_name']
        parsed_current_version = UpToDate._tokenizeMISPVersion(current_version)
        parsed_github_version = UpToDate._tokenizeMISPVersion(github_version)
        data = {
            "github_version": github_version,
            "current_version": current_version,
            "parsed_github_version": parsed_github_version,
            "parsed_current_version": parsed_current_version,
            "update_available": UpToDate._canBeUpdated(parsed_github_version, parsed_current_version)
        }
        if not data['update_available']:
            return None

        return {
            "title": self._getTitle(data),
            "severity": self._getSeverity(data),
            "data": data
        }

    def _getTitle(self, data):
        if data['update_available']:
            return f"Update {data['github_version']} is available. (current version {data['current_version']}"
        else:
            return f"Version {data['current_version']} is update-to-date"

    def _getSeverity(self, data):
        if data['update_available']:
            return Severity.LOW
        else:
            return Severity.NA


    def _canBeUpdated(github_version, current_version):
        if github_version['major'] != current_version['major']:
            return False  # update for major version should be done manually
        elif github_version['minor'] != current_version['minor']:
            return False  # update for major version should be done manually
        elif github_version['patch'] > current_version['patch']:
            return True
        else:
            return False
        return False

    def _tokenizeMISPVersion(versionString):
        version = {}
        if versionString.startswith("v"):
            versionString = versionString[1:]
        arr = versionString.split(".")
        version = {
            "major": arr[0],
            "minor": arr[1],
            "patch": arr[2]
        }
        return version