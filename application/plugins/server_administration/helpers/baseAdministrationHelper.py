import time

def feature_enabled(method):
    method.feature_enabled = False
    return method


class baseAdministrationHelper:
    name = 'base'
    def __init__(self):
        self.server = None

    def setServer(self, server):
        self.server = server

    @classmethod
    @feature_enabled
    def getView(self, server, data={}):
        pass
    
    @classmethod
    @feature_enabled
    def execPlugin(self, server, data={}):
        pass
    
    def introspection(self):
        return {
            'view': getattr(self.run, 'feature_enabled', True),
            'exec': getattr(self.run, 'feature_enabled', True),
        }
