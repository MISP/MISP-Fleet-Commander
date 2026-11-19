"""The stored usage metrics in the Prometheus text format (version 0.0.4), served by `GET /metrics`.

A scrape never queries MISP: it serves what the last collection of each server stored. The servers are those of the
requester's monitored fleets that have been collected at least once, and only while monitoring is enabled, so that
their series end in Prometheus when MFC stops collecting them rather than repeating old values.

Gauges come from the server's latest sample. A metric missing from it (its request failed) is left out rather than
taken from an older sample. `misp_last_sample_timestamp_seconds` says how old the sample is, and `misp_up` whether
the last collection read anything. Logins are counters, from the running totals kept since the first collection
(which counts the past days of MISP logs). They appear once MISP's logs have been read.

Names follow the catalogue keys, adapted to Prometheus conventions: percentages are ratios from 0 to 1
(`memory_used_pct` → `misp_memory_used_ratio`) and the worker queues are one metric with a `queue` label.
"""
import math
from dataclasses import dataclass
from typing import Optional

from application import redisModel
from application.DBModels import db, Fleet, MetricState, Server
import application.models.metricCatalogue as catalogue
import application.models.metricSeries as metricSeries
import application.models.metrics as metricModel

CONTENT_TYPE = 'text/plain; version=0.0.4; charset=utf-8'
GAUGE, COUNTER = 'gauge', 'counter'
# Logins are counted since the first collection, which also counts the MISP logs of the previous days
COUNTERS = (
    ('misp_logins_total', 'Successful logins on the MISP server', 'logins_total'),
    ('misp_failed_logins_total', 'Failed logins on the MISP server', 'failed_logins_total'),
)


@dataclass(frozen=True)
class Exposed:
    """How a catalogue metric is exposed: its name, help text, extra labels and the factor applied to its value"""
    name: str
    help: str
    labels: tuple = ()
    scale: float = 1


def exposedAs(metric: catalogue.Metric) -> Exposed:
    if metric.key.startswith('queue_'):
        return Exposed('misp_queue_jobs', 'Jobs waiting in a MISP worker queue',
                       (('queue', metric.key.removeprefix('queue_')),))
    if metric.unit == 'percent':
        return Exposed(f"misp_{metric.key.removesuffix('_pct')}_ratio", f'{metric.label} (0 to 1)', scale=0.01)
    if metric.kind == catalogue.TOTAL:
        return Exposed(f'misp_{metric.key}', f'{metric.label} on the MISP server')
    unit = {'bytes': ' (bytes)'}.get(metric.unit, '')
    return Exposed(f'misp_{metric.key}', f'{metric.label}{unit}')


GAUGES = [(metric.key, exposedAs(metric)) for metric in catalogue.CATALOGUE if metric.kind != catalogue.DELTA]


def escapeLabelValue(value) -> str:
    return str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def escapeHelp(text: str) -> str:
    return text.replace('\\', '\\\\').replace('\n', '\\n')


def formatValue(value) -> str:
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    value = float(value)
    if math.isnan(value):
        return 'NaN'
    if math.isinf(value):
        return '+Inf' if value > 0 else '-Inf'
    return repr(value)


def formatLabels(labels) -> str:
    return '{' + ','.join(f'{name}="{escapeLabelValue(value)}"' for name, value in labels) + '}'


class Exposition:
    """Samples gathered per metric family, written family by family as the format requires"""

    def __init__(self):
        self.families = {}

    def add(self, name: str, kind: str, help: str, labels, value):
        family = self.families.setdefault(name, {'kind': kind, 'help': help, 'samples': []})
        family['samples'].append((tuple(labels), value))

    def render(self) -> str:
        lines = []
        for name, family in self.families.items():
            lines.append(f"# HELP {name} {escapeHelp(family['help'])}")
            lines.append(f"# TYPE {name} {family['kind']}")
            lines.extend(f'{name}{formatLabels(labels) if labels else ""} {formatValue(value)}'
                         for labels, value in family['samples'])
        return '\n'.join(lines) + '\n'


def scrapedServers(user) -> list:
    """(server, fleet, state) of the user's servers that MFC collects metrics of, ordered by server id"""
    return (db.session.query(Server, Fleet, MetricState)
            .join(Fleet, Server.fleet_id == Fleet.id)
            .join(MetricState, MetricState.server_id == Server.id)
            .filter(Server.user_id == user.id, Fleet.is_monitored.is_(True))
            .order_by(Server.id)
            .all())


def latestSamples(server_ids: list) -> dict:
    """server id → values of its newest raw sample"""
    return {server_id: row.values or {} for server_id, row in metricSeries.latestSamples(server_ids).items()}


def mispVersion(server) -> Optional[str]:
    status = redisModel.getServerStatus(server.uuid) or {}
    version = status.get('version')
    return version if isinstance(version, str) and version else None


def exposition(user) -> str:
    enabled = bool(metricModel.monitoringSettings()['enabled'])
    out = Exposition()
    out.add('mfc_monitoring_enabled', GAUGE, 'Whether MISP Fleet Commander collects usage metrics', (), int(enabled))
    servers = scrapedServers(user) if enabled else []
    samples = latestSamples([server.id for server, _, _ in servers])
    labels = {server.id: (('server', server.name), ('server_id', server.id), ('fleet', fleet.name))
              for server, fleet, _ in servers}

    for server, _, state in servers:
        up = state.last_success is not None and state.last_success >= (state.last_attempt or 0)
        out.add('misp_up', GAUGE, 'Whether the last metric collection of the MISP server read anything',
                labels[server.id], int(up))
        if state.last_success is not None:
            out.add('misp_last_sample_timestamp_seconds', GAUGE, 'When the latest usage sample was collected',
                    labels[server.id], state.last_success)
        version = mispVersion(server)
        if version is not None:
            out.add('misp_info', GAUGE, 'The MISP version of the server',
                    labels[server.id] + (('version', version),), 1)

    for key, exposed in GAUGES:
        for server, _, _ in servers:
            value = samples.get(server.id, {}).get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if exposed.scale != 1:
                value = round(value * exposed.scale, 6)
            out.add(exposed.name, GAUGE, exposed.help, labels[server.id] + exposed.labels, value)

    for name, help, field in COUNTERS:
        for server, _, state in servers:
            # Not before the first read of the logs: a counter appearing at 0 and then jumping to the backfilled
            # total would count the past days as new logins in `increase()`
            if state.logins_read_at is None:
                continue
            out.add(name, COUNTER, help, labels[server.id], getattr(state, field) or 0)

    return out.render()
