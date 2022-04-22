from application.plugins.server_administration import loadAvailableHelpers


class AdministrationManager:
    def __init__(self, server):
        self.helpers = loadAvailableHelpers()
        self.server = server
        self._registerServer()

    def _registerServer(self):
        for helper in self.helpers:
            helperInstance = helper['instance']
            helperInstance.setServer(self.server)

    def getAvailableHelpers(self):
        return self.helpers

    def getHelperByName(self, name):
        for helper in self.helpers:
            if name == helper['filename']:
                return helper
        return None

    def getHelperInstanceByName(self, name):
        helper = self.getHelperByName(name)
        if helper is not None:
            return helper['instance']
        return None

    def queryAll(self):
        results = []
        for helper in self.helpers:
            helperInstance = helper['instance']
            result = helperInstance.queryHelper()
            results += result
        return results
