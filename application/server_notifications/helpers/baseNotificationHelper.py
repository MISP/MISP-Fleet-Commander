import time

def feature_enabled(method):
    method.feature_enabled = False
    return method

class Severity:
    NA = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class baseNotificationHelper:
    name = 'base'
    def __init__(self):
        self.server = None

    def setServer(self, server):
        self.server = server

    @classmethod
    @feature_enabled
    def query(self):
        pass
    
    @classmethod
    @feature_enabled
    def accept(self):
        pass

    @classmethod
    @feature_enabled
    def process(self):
        pass

    @classmethod
    @feature_enabled
    def delete(self):
        pass

    def queryHelper(self):
        queryResult = self.query()
        results = []
        if type(queryResult) != list:
            queryResult = [queryResult]
        for qr in queryResult:
            if qr is None:
                continue
            data = qr['data'] if 'data' in qr else qr
            severity = qr['severity'] if 'severity' in qr else Severity.NA
            title = qr['title'] if 'title' in qr else ''
            results.append({
                "timestamp": int(time.time()),
                "origin": self.name,
                "severity": severity,
                "title": title,
                "data": data
            })
        return results


    def introspection(self):
        return {
            'query': getattr(self.query, 'feature_enabled', True),
            'accept': getattr(self.accept, 'feature_enabled', True),
            'process': getattr(self.process, 'feature_enabled', True),
            'delete': getattr(self.delete, 'feature_enabled', True),
        }
