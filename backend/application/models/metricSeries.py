"""Reading the stored metrics of a server: series over a range, the latest sample, and how the collection stands.

A range is served from one tier: raw samples for the last day, hourly buckets up to a month, daily ones beyond, so
that a series stays around 1000 points or fewer. Hour and day series run up to now: the buckets the hourly roll-up
has not written yet are summed up on the fly from the finer rows.
"""
import time
from collections import defaultdict
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import func

from application.DBModels import db, MetricSample, MetricState
from application.models import metricCatalogue as catalogue
from application.models.metricRollups import DAY, HOUR, retention, summarise

RANGES = {'24h': DAY, '7d': 7 * DAY, '30d': 30 * DAY, '90d': 90 * DAY, '1y': 365 * DAY}
DEFAULT_RANGE = '7d'
DEFAULT_TIERS = {'24h': 'raw', '7d': 'hour', '30d': 'hour', '90d': 'day', '1y': 'day'}
TIERS = ('raw', 'hour', 'day')
BUCKET_SIZES = {'hour': HOUR, 'day': DAY}


class SeriesRequestError(ValueError):
    pass


def parseRequest(rangeName: Optional[str], tier: Optional[str], metrics: Optional[str]) -> tuple:
    """(range, tier, keys) from the query string. Raises SeriesRequestError with a message for the user"""
    rangeName = rangeName or DEFAULT_RANGE
    if rangeName not in RANGES:
        raise SeriesRequestError(f"Unknown range `{rangeName}`: use one of {', '.join(RANGES)}")
    tier = tier or DEFAULT_TIERS[rangeName]
    if tier not in TIERS:
        raise SeriesRequestError(f"Unknown tier `{tier}`: use one of {', '.join(TIERS)}")
    # Beyond its retention, a tier has nothing more to show
    maxSpan = retention()[tier]
    if maxSpan is not None and RANGES[rangeName] > maxSpan:
        raise SeriesRequestError(f"The {tier} tier only covers {maxSpan // DAY} days: ask for a shorter range")
    if metrics:
        keys = [key.strip() for key in metrics.split(',') if key.strip()]
        unknown = [key for key in keys if key not in catalogue.METRICS]
        if unknown:
            raise SeriesRequestError(f"Unknown metric `{unknown[0]}`")
        keys = list(dict.fromkeys(keys))
    else:
        keys = [metric.key for metric in catalogue.CATALOGUE]
    return rangeName, tier, keys


def _rows(server_id: int, tier: str, since: int) -> list:
    return MetricSample.query.filter(MetricSample.server_id == server_id, MetricSample.tier == tier,
                                     MetricSample.ts >= since).order_by(MetricSample.ts).all()


def _lastBucketEnd(server_id: int, tier: str, size: int) -> Optional[int]:
    last = db.session.query(func.max(MetricSample.ts)).filter(MetricSample.server_id == server_id,
                                                              MetricSample.tier == tier).scalar()
    return None if last is None else last + size


def pendingBuckets(server_id: int, tier: str, since: int) -> list:
    """Buckets of `tier` from `since` that the roll-up has not written yet, summed up from the finer rows: raw rows
    for hours; for days, the hour rows plus the raw rows of the hours not rolled up yet"""
    size = BUCKET_SIZES[tier]
    if tier == 'hour':
        finer = _rows(server_id, 'raw', since)
    else:
        finer = _rows(server_id, 'hour', since)
        rawSince = max(since, _lastBucketEnd(server_id, 'hour', HOUR) or since)
        finer += _rows(server_id, 'raw', rawSince)
    byBucket = defaultdict(list)
    for row in finer:
        byBucket[row.ts - row.ts % size].append(row)
    buckets = []
    for bucket in sorted(byBucket):
        values, peaks, samples = summarise(byBucket[bucket])
        buckets.append(SimpleNamespace(ts=bucket, values=values, peaks=peaks, samples=samples))
    return buckets


def latestSample(server_id: int) -> Optional[MetricSample]:
    return MetricSample.query.filter_by(server_id=server_id, tier='raw').order_by(MetricSample.ts.desc()).first()


def collectionState(server, settings: dict) -> dict:
    state = db.session.get(MetricState, server.id)
    return {
        'enabled': bool(settings['enabled']),
        'fleet_monitored': bool(server.fleet.is_monitored) if server.fleet is not None else False,
        'has_authkey': bool(server.authkey),
        'interval_s': settings['interval'],
        'last_attempt': state.last_attempt if state else None,
        'last_success': state.last_success if state else None,
        'last_error': state.last_error if state else None,
    }


def series(server, rangeName: str, tier: str, keys: list, settings: dict, now: Optional[int] = None) -> dict:
    """The answer of `GET /servers/metrics/<id>`; `settings` holds `enabled` and `interval` (seconds)"""
    now = int(time.time()) if now is None else now
    start = now - RANGES[rangeName]
    partialSince = None
    if tier == 'raw':
        points = _rows(server.id, 'raw', start)
        interval = settings['interval']
    else:
        interval = BUCKET_SIZES[tier]
        first = start - start % interval
        points = _rows(server.id, tier, first)
        pending = pendingBuckets(server.id, tier, points[-1].ts + interval if points else first)
        points += pending
        if pending and pending[-1].ts == now - now % interval:
            partialSince = pending[-1].ts
    gauges = [key for key in keys if catalogue.METRICS[key].kind == catalogue.GAUGE]
    latest = latestSample(server.id)
    return {
        'server_id': server.id,
        'range': rangeName,
        'tier': tier,
        'from': start,
        'to': now,
        'interval_s': interval,
        'partial_since': partialSince,
        'series': {key: [[point.ts, point.values[key]] for point in points if key in (point.values or {})]
                   for key in keys},
        'peaks': {} if tier == 'raw' else {
            key: [[point.ts, point.peaks[key]] for point in points if key in (point.peaks or {})] for key in gauges
        },
        'latest': None if latest is None else {
            'ts': latest.ts, 'values': {key: value for key, value in latest.values.items() if key in keys},
        },
        'state': collectionState(server, settings),
        'metrics': {key: {'label': catalogue.METRICS[key].label, 'group': catalogue.METRICS[key].group,
                          'kind': catalogue.METRICS[key].kind, 'unit': catalogue.METRICS[key].unit} for key in keys},
    }
