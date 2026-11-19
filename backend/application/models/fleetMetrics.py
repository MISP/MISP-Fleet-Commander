"""Usage metrics of a fleet: its servers' figures summed per hour or per day, and each server's own figures side by
side.

Raw samples don't line up across servers (each one is collected at its own time), hour and day buckets do: the fleet
series use hours up to 30 days and days beyond. Logins add up as they are. Counts (events, users) and the levels that
add up (database size, queued jobs, API requests) carry each server's last value forward until its next one, so that
a server missing an hour doesn't make the fleet dip; a server whose history starts inside the range joins the sum
there. What doesn't add up across servers (see metricCatalogue.FLEET_SUMMED) is only given per server.
"""
import time
from collections import defaultdict
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import func

from application.DBModels import db, MetricSample, MetricState
from application.models import metricCatalogue as catalogue
from application.models import metricSeries

FLEET_TIERS = {'24h': 'hour', '7d': 'hour', '30d': 'hour', '90d': 'day', '1y': 'day'}
# The per-server change over the range, from its first bucket to its last
GROWING = frozenset([metric.key for metric in catalogue.CATALOGUE if metric.kind == catalogue.TOTAL]
                    + ['db_size_bytes'])
# The gauges whose highest value over the range is given per server: what tells a struggling machine apart
PEAK_KEYS = ('load_1', 'memory_used_pct', 'disk_used_pct')
# Up to this many keys, the stored rows are read key by key in SQLite instead of decoding their whole JSON in Python.
# Measured on 51 servers × 30 days of hours: 1 key 130 ms, 2 keys 160 ms, whole rows 370 ms, 16 keys 590 ms
EXTRACT_UP_TO = 4


def parseRequest(rangeName: Optional[str], metrics: Optional[str]) -> tuple:
    """(range, tier, keys). Raises metricSeries.SeriesRequestError with a message for the user"""
    rangeName, _, keys = metricSeries.parseRequest(rangeName, None, metrics)
    return rangeName, FLEET_TIERS[rangeName], keys


# Stored values are JSON numbers; `type()` rather than isinstance keeps booleans out, and is quicker over the tens of
# thousands of buckets of a big fleet
NUMBERS = (int, float)


def _keysOfKind(keys: list, kind: str) -> list:
    return [key for key in keys if catalogue.METRICS[key].kind == kind]


def _rounded(value: float):
    value = round(value, 3)
    return int(value) if float(value).is_integer() else value


def _extracted(column, key: str):
    return func.json_extract(column, f'$.{key}')


def _storedRows(server_ids: list, tier: str, since: int, keys: list) -> dict:
    """{server_id: rows of `tier` from `since`}, with the values of `keys` and the peaks of PEAK_KEYS"""
    rows = defaultdict(list)
    if not server_ids:
        return rows
    peakKeys = [key for key in PEAK_KEYS if key in keys]
    extract = len(keys) <= EXTRACT_UP_TO
    columns = [MetricSample.server_id, MetricSample.ts]
    columns += [_extracted(MetricSample.values, key) for key in keys] if extract else [MetricSample.values]
    columns += [_extracted(MetricSample.peaks, key) for key in peakKeys]
    peaksAt = 2 + (len(keys) if extract else 1)
    query = (db.session.query(*columns)
             .filter(MetricSample.server_id.in_(server_ids), MetricSample.tier == tier, MetricSample.ts >= since)
             .order_by(MetricSample.ts))
    for row in query:
        if extract:
            values = {key: row[2 + index] for index, key in enumerate(keys) if row[2 + index] is not None}
        else:
            values = row[2]
        peaks = {key: row[peaksAt + index] for index, key in enumerate(peakKeys) if row[peaksAt + index] is not None}
        rows[row[0]].append(SimpleNamespace(ts=row[1], values=values, peaks=peaks))
    return rows


def timelines(server_ids: list, tier: str, since: int, keys: list) -> tuple:
    """({server_id: buckets of `tier` from `since` up to now}, the start of the bucket still in progress or None).
    Buckets have `ts`, `values` (at least `keys`) and `peaks` (at least those of PEAK_KEYS); those the roll-up has
    not written yet are summed up on the fly"""
    size = metricSeries.BUCKET_SIZES[tier]
    stored = _storedRows(server_ids, tier, since, keys)
    pendingSince = {server_id: stored[server_id][-1].ts + size if stored[server_id] else since
                    for server_id in server_ids}
    pending = metricSeries.pendingBucketsOf(tier, pendingSince)
    lines = {server_id: stored[server_id] + pending.get(server_id, []) for server_id in server_ids}
    newest = max((buckets[-1].ts for buckets in pending.values() if buckets), default=None)
    return lines, newest


def sums(lines: dict, keys: list) -> tuple:
    """({key: [[ts, fleet value]]}, [[ts, servers with a bucket]]) over the buckets of every server"""
    summed = [key for key in keys if key in catalogue.FLEET_SUMMED]
    deltas = _keysOfKind(summed, catalogue.DELTA)
    levels = [key for key in summed if key not in deltas]
    byServer = {server_id: {bucket.ts: bucket for bucket in buckets} for server_id, buckets in lines.items()}
    # Each server's last value of the levels, and their running sum over the servers that have one
    carried = {server_id: {} for server_id in lines}
    running = {}
    totals = {key: [] for key in summed}
    reporting = []
    for ts in sorted({ts for buckets in byServer.values() for ts in buckets}):
        added, present = {}, 0
        for server_id, buckets in byServer.items():
            bucket = buckets.get(ts)
            if bucket is None:
                continue
            present += 1
            values, last = bucket.values or {}, carried[server_id]
            for key in levels:
                value = values.get(key)
                if type(value) in NUMBERS:
                    running[key] = running.get(key, 0) + value - last.get(key, 0)
                    last[key] = value
            for key in deltas:
                value = values.get(key)
                if type(value) in NUMBERS:
                    added[key] = added.get(key, 0) + value
        reporting.append([ts, present])
        for key, value in added.items():
            totals[key].append([ts, _rounded(value)])
        for key, value in running.items():
            totals[key].append([ts, _rounded(value)])
    return totals, reporting


def serverFigures(buckets: list, keys: list) -> dict:
    """What a server did over the range: sums of its deltas, change of what grows (from two buckets on), highest
    load, memory and disk"""
    deltas, gauges = _keysOfKind(keys, catalogue.DELTA), [key for key in PEAK_KEYS if key in keys]
    growing = [key for key in keys if key in GROWING]
    first, last, seen, added, peaks = {}, {}, defaultdict(int), {}, {}
    for bucket in buckets:
        values = bucket.values or {}
        for key in deltas:
            value = values.get(key)
            if type(value) in NUMBERS:
                added[key] = added.get(key, 0) + value
        for key in growing:
            value = values.get(key)
            if type(value) in NUMBERS:
                first.setdefault(key, value)
                last[key] = value
                seen[key] += 1
        if gauges:
            bucketPeaks = bucket.peaks or {}
            for key in gauges:
                value = values.get(key)
                if type(value) in NUMBERS:
                    peak = bucketPeaks.get(key, value)
                    if key not in peaks or peak > peaks[key]:
                        peaks[key] = peak
    return {
        'sums': {key: _rounded(value) for key, value in added.items()},
        'change': {key: _rounded(last[key] - first[key]) for key in last if seen[key] > 1},
        'peaks': {key: _rounded(value) for key, value in peaks.items()},
        'since': buckets[0].ts if buckets else None,
    }


def fleetSeries(fleet, rangeName: str, tier: str, keys: list, settings: dict, now: Optional[int] = None) -> dict:
    """The answer of `GET /fleets/metrics/<id>`; `settings` holds `enabled` and `interval` (seconds)"""
    now = int(time.time()) if now is None else now
    start = now - metricSeries.RANGES[rangeName]
    size = metricSeries.BUCKET_SIZES[tier]
    first = start - start % size
    servers = sorted(fleet.servers, key=lambda server: (server.name or '').lower())
    serverIds = [server.id for server in servers]
    lines, newestPending = timelines(serverIds, tier, first, keys)
    totals, reporting = sums(lines, keys)
    latest = metricSeries.latestSamples(serverIds)
    states = {state.server_id: state for state in
              MetricState.query.filter(MetricState.server_id.in_(serverIds))} if serverIds else {}
    perServer = []
    for server in servers:
        state, sample = states.get(server.id), latest.get(server.id)
        perServer.append({
            'id': server.id,
            'name': server.name,
            'latest': None if sample is None else {
                'ts': sample.ts, 'values': {key: value for key, value in sample.values.items() if key in keys},
            },
            **serverFigures(lines[server.id], keys),
            'state': {
                'enabled': bool(settings['enabled']),
                'fleet_monitored': bool(fleet.is_monitored),
                'has_authkey': bool(server.authkey),
                'interval_s': settings['interval'],
                'last_attempt': state.last_attempt if state else None,
                'last_success': state.last_success if state else None,
                'last_error': state.last_error if state else None,
            },
        })
    return {
        'fleet_id': fleet.id,
        'range': rangeName,
        'tier': tier,
        'from': start,
        'to': now,
        'interval_s': size,
        'partial_since': newestPending if newestPending == now - now % size else None,
        'totals': totals,
        'reporting': reporting,
        'latest_ts': max((sample.ts for sample in latest.values()), default=None),
        'servers': perServer,
        'state': {
            'enabled': bool(settings['enabled']),
            'fleet_monitored': bool(fleet.is_monitored),
            'interval_s': settings['interval'],
            'servers': len(servers),
        },
        'metrics': {key: {'label': catalogue.METRICS[key].label, 'group': catalogue.METRICS[key].group,
                          'kind': catalogue.METRICS[key].kind, 'unit': catalogue.METRICS[key].unit,
                          'summed': key in catalogue.FLEET_SUMMED} for key in keys},
    }
