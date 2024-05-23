from typing import List, Optional, Union
from application.DBModels import Server
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse


class HtmlPlugin(BasePlugin):
    name = 'Html Plugin'
    description = 'Display raw html'
    icon = 'fab fa-html5'
    component = 'htmlElement'
    html = '<b>change me</b>'
    abstract_class = True

    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return SuccessPluginResponse({'html': self.html}, None, self.component)

    def index(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return self.view(server, data)
