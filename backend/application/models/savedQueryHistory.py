"""The history of saved queries: the number each server answered to a saved query over time (a COUNT, or the rows a
SELECT returned), never the rows themselves.

Each answer kept by `savedQueries.recordRun` is written twice: a `raw` row timed when the server answered, and the
row of its UTC day, rebuilt from that day's raw rows (last answer, lowest, highest, how many). The day row is
therefore always current, and nothing is left to roll up. Answers that are not numbers (a server without complex
queries, query errors, timeouts) write nothing: they are gaps in the history, and health reports them.

Charts read one tier per range, like the Usage tabs: every answer up to 7 days, hours made from the raw rows for 30
days (while raw rows cover them), days beyond. Raw rows are kept `query_history_raw_days`, day rows
`query_history_day_days` (0: as long as the saved query); `trim` applies both, every hour.
"""
import time
from collections import defaultdict
from typing import Iterable, List, Optional

from application.DBModels import SavedQuerySample, db
from application.models import setting as settingModel
from application.models.metricSeries import DEFAULT_RANGE, RANGES

HOUR = 3600
DAY = 24 * HOUR
# Ranges drawn from every answer; the next ones use hours, then days
RAW_SPAN = 7 * DAY
HOUR_SPAN = 30 * DAY
# The gap a query run by hand may leave between two points of one line
UNSCHEDULED_INTERVAL = DAY


class HistoryRequestError(ValueError):
    pass


def _days(setting_name: str) -> int:
    return max(settingModel.intValue(setting_name), settingModel.get(setting_name)['min'])


def retention() -> dict:
    """Seconds each tier is kept, read from the settings on every call; None: as long as the saved query. Values
    edited by hand in config.json are brought back in bounds: day rows never go before raw rows, nor under a year"""
    raw = _days('query_history_raw_days') * DAY
    day = _days('query_history_day_days')
    return {
        'raw': raw,
        'day': max(raw, day * DAY, settingModel.DAY_RETENTION_MIN_DAYS * DAY) if day else None,
    }


# Writing

def record(savedId: int, serverId: int, ts: int, value: int, more: bool = False) -> None:
    """Keep one answer, then rebuild its day. Recording the same answer again changes nothing. The caller commits"""
    raw = SavedQuerySample.query.filter_by(saved_query_id=savedId, server_id=serverId, tier='raw', ts=ts).first()
    if raw is None:
        raw = SavedQuerySample(saved_query_id=savedId, server_id=serverId, tier='raw', ts=ts)
        db.session.add(raw)
    raw.value, raw.more, raw.samples = value, bool(more), 1
    db.session.flush()
    rebuildDay(savedId, serverId, ts - ts % DAY)


def rebuildDay(savedId: int, serverId: int, dayStart: int) -> Optional[SavedQuerySample]:
    rows = SavedQuerySample.query.filter(
        SavedQuerySample.saved_query_id == savedId, SavedQuerySample.server_id == serverId,
        SavedQuerySample.tier == 'raw', SavedQuerySample.ts >= dayStart, SavedQuerySample.ts < dayStart + DAY,
    ).order_by(SavedQuerySample.ts).all()
    day = SavedQuerySample.query.filter_by(saved_query_id=savedId, server_id=serverId, tier='day',
                                           ts=dayStart).first()
    if not rows:
        return day
    if day is None:
        day = SavedQuerySample(saved_query_id=savedId, server_id=serverId, tier='day', ts=dayStart)
        db.session.add(day)
    summary = summarise(rows)
    day.value, day.low, day.high = summary['value'], summary['low'], summary['high']
    day.samples, day.more = summary['samples'], summary['more']
    return day


def summarise(rows: Iterable) -> dict:
    """Rows of one bucket, oldest first, summed up: the last answer, the lowest, the highest, how many, any capped"""
    rows = list(rows)
    values = [row.value for row in rows]
    return {
        'value': values[-1],
        'low': min(row.low if row.low is not None else row.value for row in rows),
        'high': max(row.high if row.high is not None else row.value for row in rows),
        'samples': sum(row.samples or 1 for row in rows),
        'more': any(row.more for row in rows),
    }


def drop(savedId: int, serverIds: Optional[List[int]] = None) -> int:
    """Forget the history of a saved query, or of some of its servers. The caller commits"""
    query = SavedQuerySample.query.filter(SavedQuerySample.saved_query_id == savedId)
    if serverIds is not None:
        query = query.filter(SavedQuerySample.server_id.in_(serverIds))
    return query.delete(synchronize_session=False)


def trim(now: Optional[int] = None) -> dict:
    """Delete the rows older than their tier's retention"""
    now = int(time.time()) if now is None else now
    deleted = {}
    for tier, keep in retention().items():
        if keep is None:
            continue
        deleted[tier] = SavedQuerySample.query.filter(SavedQuerySample.tier == tier,
                                                      SavedQuerySample.ts < now - keep) \
            .delete(synchronize_session=False)
    db.session.commit()
    return deleted


# Reading

def parseRange(rangeName: Optional[str]) -> str:
    rangeName = rangeName or DEFAULT_RANGE
    if rangeName not in RANGES:
        raise HistoryRequestError(f"Unknown range `{rangeName}`: use one of {', '.join(RANGES)}")
    return rangeName


def tierFor(rangeName: str, rawKept: Optional[int] = None) -> str:
    span = RANGES[rangeName]
    rawKept = retention()['raw'] if rawKept is None else rawKept
    if span <= RAW_SPAN:
        return 'raw'
    if span <= HOUR_SPAN and rawKept >= span:
        return 'hour'
    return 'day'


def _rows(savedId: int, serverIds: List[int], tier: str, since: int) -> dict:
    """{server_id: rows of `tier` from `since`, oldest first}"""
    rows = defaultdict(list)
    if not serverIds:
        return rows
    for row in SavedQuerySample.query.filter(
            SavedQuerySample.saved_query_id == savedId, SavedQuerySample.server_id.in_(serverIds),
            SavedQuerySample.tier == tier, SavedQuerySample.ts >= since).order_by(SavedQuerySample.ts):
        rows[row.server_id].append(row)
    return rows


def _hours(rows: list) -> list:
    """Raw rows summed up per hour, as day rows are per day"""
    byHour = defaultdict(list)
    for row in rows:
        byHour[row.ts - row.ts % HOUR].append(row)
    return [dict(summarise(byHour[start]), ts=start) for start in sorted(byHour)]


def series(savedId: int, servers: list, scheduleMinutes: Optional[int], rangeName: str,
           now: Optional[int] = None) -> dict:
    """Each server's points over the range: `points` [[ts, value]], and for hours and days `lows` and `highs` (the
    band from the lowest to the highest answer), `capped` the times a SELECT found more rows than its LIMIT"""
    now = int(time.time()) if now is None else now
    keep = retention()
    tier = tierFor(rangeName, keep['raw'])
    start = now - RANGES[rangeName]
    serverIds = [server.id for server in servers]
    if tier == 'raw':
        interval = (scheduleMinutes or 0) * 60 or UNSCHEDULED_INTERVAL
        byServer = {serverId: [{'ts': row.ts, 'value': row.value, 'more': row.more} for row in rows]
                    for serverId, rows in _rows(savedId, serverIds, 'raw', start).items()}
    elif tier == 'hour':
        interval = HOUR
        byServer = {serverId: _hours(rows) for serverId, rows in _rows(savedId, serverIds, 'raw', start).items()}
    else:
        interval = DAY
        byServer = {serverId: [{'ts': row.ts, 'value': row.value, 'low': row.low, 'high': row.high,
                                'samples': row.samples, 'more': row.more} for row in rows]
                    for serverId, rows in _rows(savedId, serverIds, 'day', start - start % DAY).items()}
    current = now - now % interval if tier != 'raw' else None
    partialSince = None
    entries = []
    for server in servers:
        points = byServer.get(server.id, [])
        if current is not None and points and points[-1]['ts'] == current:
            partialSince = current
        entries.append({
            'server_id': server.id,
            'server_name': server.name,
            'points': [[point['ts'], point['value']] for point in points],
            'lows': [[point['ts'], point['low']] for point in points if tier != 'raw'],
            'highs': [[point['ts'], point['high']] for point in points if tier != 'raw'],
            'capped': [point['ts'] for point in points if point['more']],
        })
    return {
        'range': rangeName,
        'tier': tier,
        'from': start,
        'to': now,
        'interval_s': interval,
        'partial_since': partialSince,
        'servers': entries,
        'retention': {'raw_days': keep['raw'] // DAY, 'day_days': None if keep['day'] is None else keep['day'] // DAY},
    }


def _lastBefore(savedId: int, serverId: int, before: int, source: str) -> Optional[SavedQuerySample]:
    """The server's last answer before `before`: a raw row, or for hours whose raw rows were trimmed, the last day
    that ended by then (its `value` is that day's last answer)"""
    base = SavedQuerySample.query.filter(SavedQuerySample.saved_query_id == savedId,
                                         SavedQuerySample.server_id == serverId)
    if source == 'raw':
        row = base.filter(SavedQuerySample.tier == 'raw', SavedQuerySample.ts < before) \
            .order_by(SavedQuerySample.ts.desc()).first()
        if row is not None:
            return row
    return base.filter(SavedQuerySample.tier == 'day', SavedQuerySample.ts <= before - DAY) \
        .order_by(SavedQuerySample.ts.desc()).first()


def lastAnswers(savedId: int, serverIds: List[int]) -> dict:
    """{server_id: its last answer kept}: the last raw row, or once raw rows were trimmed, the last day row (its `ts`
    the start of that day, its `value` that day's last answer). Servers without any answer kept are left out"""
    found = {}
    for serverId in serverIds:
        base = SavedQuerySample.query.filter(SavedQuerySample.saved_query_id == savedId,
                                             SavedQuerySample.server_id == serverId)
        row = base.filter(SavedQuerySample.tier == 'raw').order_by(SavedQuerySample.ts.desc()).first() \
            or base.filter(SavedQuerySample.tier == 'day').order_by(SavedQuerySample.ts.desc()).first()
        if row is not None:
            found[serverId] = row
    return found


def total(savedId: int, servers: list, rangeName: str, now: Optional[int] = None) -> dict:
    """The servers' answers summed, as a fleet's usage totals are: per hour up to 30 days (while raw rows cover them),
    per day beyond. In each bucket, each server's last answer, carried forward until its next one, its last answer
    before the range included; a server joins the sum at its first answer. `reporting` gives how many servers each
    point sums, `capped` the points holding a SELECT's answer at its LIMIT (the fleet has at least that many)"""
    now = int(time.time()) if now is None else now
    size = DAY if tierFor(rangeName) == 'day' else HOUR
    source = 'day' if size == DAY else 'raw'
    start = now - RANGES[rangeName]
    first = start - start % size
    current = now - now % size
    serverIds = [server.id for server in servers]
    lastByBucket = {}
    for serverId, rows in _rows(savedId, serverIds, source, first).items():
        # Oldest first: the last answer of each bucket stays
        lastByBucket[serverId] = {row.ts - row.ts % size: (row.value, bool(row.more)) for row in rows}
    carried = {}
    for serverId in serverIds:
        row = _lastBefore(savedId, serverId, first, source)
        if row is not None:
            carried[serverId] = (row.value, bool(row.more))
    points, reporting, capped = [], [], []
    for bucket in range(first, current + 1, size):
        for serverId in serverIds:
            answer = lastByBucket.get(serverId, {}).get(bucket)
            if answer is not None:
                carried[serverId] = answer
        if not carried:
            continue
        points.append([bucket, sum(value for value, _ in carried.values())])
        reporting.append([bucket, len(carried)])
        if any(more for _, more in carried.values()):
            capped.append(bucket)
    return {
        'tier': 'day' if size == DAY else 'hour',
        'interval_s': size,
        'from': start,
        'to': now,
        'partial_since': current if points and points[-1][0] == current else None,
        'points': points,
        'reporting': reporting,
        'capped': capped,
        'servers': len(serverIds),
    }
