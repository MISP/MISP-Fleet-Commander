from typing import List, Optional, Union
from application.DBModels import Server
from application.models.plugins import BasePlugin, PluginResponse, SuccessPluginResponse


class GrafanaPanel(BasePlugin):
    name = 'Grafana Panel'
    description = 'Display a panel from Grafana using an iFrame'
    icon = 'fas fa-chart-area'
    component = 'htmlElement'
    disabled = True
    
    grafana_dashboard_URL = 'http://localhost:3000/d-solo/Th4djOs7k/misp?orgId=1'
    grafana_bucket = 'var-bucket=misp-training'
    grafana_refresh_sec = '5'
    grafana_vars = {
        'bucket': 'misp-training',
        'instance': 'misp-main',
        'netif': 'All',
        'disk': 'All',
    }
    grafana_panel_id = '140'
    grafana_theme = 'light'

    server_mapping = {
        'training-main': 'misp-main',
        'training1': 'misp-1',
        'training2': 'misp-2',
        'training3': 'misp-3',
        'training4': 'misp-4',
        'training5': 'misp-5',
        'training6': 'misp-6',
    }

    html = '''
<div style="
    width: 120px;
    height: 24px;
">
    <iframe src="{url}" width="280" height="66" frameborder="0" style="
    transform: scale(0.40);
    transform-origin: top left;
    background-color: transparent;
    "></iframe>
</div>
'''


    def view(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        url = self.buildURL(server)
        html = self.html.format(url=url)
        return SuccessPluginResponse({'html': html}, None, self.component)

    def index(self, server: Server, data: Optional[dict] = {}) -> PluginResponse:
        return self.view(server, data)

    def buildVars(self, server: Server):
        self.grafana_vars['instance'] = self.server_mapping[server.name]
        vars = []
        for k, v in self.grafana_vars.items():
            vars.append('var-{k}={v}'.format(k=k, v=v))
        return '&'.join(vars)
    
    def buildURL(self, server: Server):
        return '{base_url}&refresh={refresh}s&theme={theme}&{vars}&panelId={panel_id}'.format(
            base_url=self.grafana_dashboard_URL,
            refresh=self.grafana_refresh_sec,
            theme=self.grafana_theme,
            vars=self.buildVars(server),
            panel_id=str(self.grafana_panel_id)
        )
