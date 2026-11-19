"""Hourly and daily roll-ups of the metric samples, and their retention.

Every hour, each hour that is over and has raw rows but no hour row yet gets one, then each UTC day that is over and
has hour rows but no day row gets one, built from the hour rows. Then the rows older than their tier's retention are
deleted (settings, by default raw rows after 14 days and hour rows after 90; day rows stay as long as their server).
Re-running is harmless: a bucket that has its row is left alone.

How a bucket sums up its rows depends on the metric's kind (see metricCatalogue): the last value of a `total`, the
sum of a `delta`, and for a `gauge` the average weighted by the raw samples behind each row, with the maximum kept
in `peaks`.
"""
import time
from collections import defaultdict
from typing import Optional

from application.DBModels import db, MetricSample
from application.models.metricCatalogue import DELTA, GAUGE, METRICS, TOTAL, kindOf
import application.models.setting as settingModel

HOUR = 3600
DAY = 24 * HOUR
ROLLUPS = (('raw', 'hour', HOUR), ('hour', 'day', DAY))


def _days(setting_name: str) -> int:
    return max(settingModel.intValue(setting_name), settingModel.get(setting_name)['min'])


def retention() -> dict:
    """Seconds each tier is kept, from the settings, read on every call; None: as long as the server. Values edited
    by hand in config.json are brought back in bounds, and a coarser tier never keeps less than a finer one"""
    raw = _days('monitoring_raw_retention_days') * DAY
    hour = max(raw, _days('monitoring_hour_retention_days') * DAY)
    day = _days('monitoring_day_retention_days')
    return {
        'raw': raw,
        'hour': hour,
        'day': max(hour, day * DAY, settingModel.DAY_RETENTION_MIN_DAYS * DAY) if day else None,
    }


def _number(key: str, value: float):
    """Whole bytes; other averages keep 3 decimals"""
    value = round(value) if METRICS[key].unit == 'bytes' else round(value, 3)
    return int(value) if float(value).is_integer() else value


def summarise(rows: list) -> tuple:
    """(values, peaks, samples) of a bucket from its rows (MetricSample or objects with ts, values, peaks, samples).
    Raw rows count as one sample each; hour rows as the raw samples behind them (0 for backfilled logins)"""
    rows = sorted(rows, key=lambda row: row.ts)
    totals, sums, weighted, weights, peaks = {}, defaultdict(float), defaultdict(float), defaultdict(float), {}
    samples = 0
    for row in rows:
        weight = row.samples if row.samples is not None else 1
        samples += weight
        rowPeaks = row.peaks or {}
        for key, value in (row.values or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            kind = kindOf(key)
            if kind == TOTAL:
                totals[key] = value
            elif kind == DELTA:
                sums[key] += value
            elif kind == GAUGE:
                weighted[key] += value * max(weight, 1)
                weights[key] += max(weight, 1)
                peak = rowPeaks.get(key, value)
                peaks[key] = peak if key not in peaks else max(peaks[key], peak)
    values = dict(totals)
    values.update({key: _number(key, total) for key, total in sums.items()})
    values.update({key: _number(key, weighted[key] / weights[key]) for key in weighted})
    return values, {key: _number(key, peak) for key, peak in peaks.items()}, samples


def _bucket(size: int):
    return MetricSample.ts - MetricSample.ts % size


def missingBuckets(sourceTier: str, targetTier: str, size: int, before: int, server_ids=None) -> dict:
    """{server_id: [bucket start, …]} of the buckets that are over (start + size <= before), have source rows and
    no target row"""
    query = db.session.query(MetricSample.server_id, _bucket(size)) \
        .filter(MetricSample.tier == sourceTier, MetricSample.ts < before - before % size)
    if server_ids is not None:
        query = query.filter(MetricSample.server_id.in_(server_ids))
    candidates = set(query.distinct())
    if not candidates:
        return {}
    oldest = min(bucket for _, bucket in candidates)
    existing = set(db.session.query(MetricSample.server_id, MetricSample.ts)
                   .filter(MetricSample.tier == targetTier, MetricSample.ts >= oldest))
    missing = defaultdict(list)
    for server_id, bucket in sorted(candidates - existing):
        missing[server_id].append(bucket)
    return dict(missing)


def rollupServer(server_id: int, sourceTier: str, targetTier: str, size: int, buckets: list) -> int:
    rows = MetricSample.query.filter(MetricSample.server_id == server_id, MetricSample.tier == sourceTier,
                                     MetricSample.ts >= buckets[0], MetricSample.ts < buckets[-1] + size).all()
    byBucket = defaultdict(list)
    for row in rows:
        byBucket[row.ts - row.ts % size].append(row)
    created = 0
    for bucket in buckets:
        if not byBucket.get(bucket):
            continue
        values, peaks, samples = summarise(byBucket[bucket])
        db.session.add(MetricSample(server_id=server_id, tier=targetTier, ts=bucket, values=values,
                                    peaks=peaks or None, samples=samples))
        created += 1
    return created


def applyRetention(now: int) -> dict:
    deleted = {}
    for tier, keep in retention().items():
        if keep is None:
            continue
        deleted[tier] = MetricSample.query.filter(MetricSample.tier == tier, MetricSample.ts < now - keep) \
            .delete(synchronize_session=False)
    db.session.commit()
    return deleted


def run(now: Optional[int] = None) -> dict:
    """Roll up every server, then apply retention. A server whose hours fail is left out of the days, so that its
    day rows are not built from incomplete hours"""
    now = int(time.time()) if now is None else now
    report = {'hour': 0, 'day': 0}
    failed = set()
    for sourceTier, targetTier, size in ROLLUPS:
        for server_id, buckets in missingBuckets(sourceTier, targetTier, size, now).items():
            if server_id in failed:
                continue
            try:
                report[targetTier] += rollupServer(server_id, sourceTier, targetTier, size, buckets)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                failed.add(server_id)
                print(f'Could not roll up the {sourceTier} metrics of server {server_id}: {e}')
    report['deleted'] = applyRetention(now)
    return report
