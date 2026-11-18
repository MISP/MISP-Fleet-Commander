"""Today's most expensive endpoints of a MISP, read live from its benchmarking (not stored).

MISP keeps, per day and endpoint, the total and the per-request average of the time, SQL time and memory spent.
Both are fetched for the current UTC day (MISP counts days in its own timezone, so the day can be off around
midnight) and normalised to seconds and bytes. The queue workers (`Shell::/default`, …) are left out: their figure
is how long the worker process ran, not a cost. Background jobs (`Shell::Event/updateGalaxies`, …) stay.
"""
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from typing import Optional

from application.redisModel import KEY_SERVER_BENCHMARKS, redisClient
from application.models.utils import asyncFetcher

FIELDS = ('time', 'sql_time', 'memory')
TOP = 5
CACHE_SECONDS = 5 * 60
REQUEST_TIMEOUT = 30
WORKER_RE = re.compile(r'^Shell::/[^/]*$')
UNITS = {
    's': ('s', 1), 'ms': ('s', 0.001), 'us': ('s', 0.000001), 'µs': ('s', 0.000001),
    'b': ('bytes', 1), 'kb': ('bytes', 1024), 'mb': ('bytes', 1024 ** 2), 'gb': ('bytes', 1024 ** 3),
}
FIELD_UNITS = {'time': 's', 'sql_time': 's', 'memory': 'bytes'}


def benchmarkUrl(field: str, day: str, average: bool) -> str:
    return f'/benchmarks/index/scope:endpoint/field:{field}/days[]:{day}' + ('/average:1' if average else '')


def normalise(row) -> Optional[tuple]:
    """(value, unit) of a benchmark row in seconds or bytes, or None"""
    if not isinstance(row, dict):
        return None
    try:
        value = float(row.get('value'))
    except (TypeError, ValueError):
        return None
    unit, factor = UNITS.get(str(row.get('unit') or '').strip().lower(), (row.get('unit'), 1))
    value *= factor
    return (int(round(value)) if unit == 'bytes' else round(value, 4)), unit


def topEndpoints(field: str, totals: list, averages: list) -> dict:
    """{unit, top: [{endpoint, job, total, average}]}: the endpoints that cost the most over the day"""
    averageOf = {}
    for row in averages:
        normalised = normalise(row)
        if normalised is not None:
            averageOf[str(row.get('key'))] = normalised[0]
    entries, unit = [], FIELD_UNITS[field]
    for row in totals:
        normalised = normalise(row)
        key = str(row.get('key')) if isinstance(row, dict) else ''
        if normalised is None or not key or WORKER_RE.match(key):
            continue
        total, unit = normalised
        entries.append({'endpoint': key, 'job': key.startswith('Shell::'), 'total': total,
                        'average': averageOf.get(key)})
    entries.sort(key=lambda entry: entry['total'], reverse=True)
    return {'unit': unit, 'top': entries[:TOP]}


def benchmarkError(answer) -> Optional[str]:
    if isinstance(answer, list):
        return None
    if not isinstance(answer, dict):
        return 'Unexpected answer from MISP'
    status = answer.get('_status_code')
    if status in (401, 403, 405):
        return 'MISP refused to show its benchmarks: the API key needs site admin rights'
    if status == 404:
        return 'This MISP does not offer its benchmarks through the API'
    if 'error' in answer:
        return str(answer['error'])
    return 'Unexpected answer from MISP'


def fetchBenchmarks(server, now: Optional[int] = None) -> dict:
    now = int(time.time()) if now is None else now
    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    result = {'server_id': server.id, 'date': day, 'timestamp': now}
    if not server.authkey:
        return {**result, 'error': 'No API key configured'}
    urls = [benchmarkUrl(field, day, average) for field in FIELDS for average in (False, True)]
    answers = asyncio.run(asyncFetcher(server, urls, timeout=REQUEST_TIMEOUT))
    for answer in answers:
        error = benchmarkError(answer)
        if error is not None:
            return {**result, 'error': error}
    result['fields'] = {field: topEndpoints(field, answers[2 * index], answers[2 * index + 1])
                        for index, field in enumerate(FIELDS)}
    if not any(answers[2 * index] for index in range(len(FIELDS))):
        result['note'] = (f'No benchmark for {day}: benchmarking may be off on this MISP, or nothing was timed yet '
                          'today')
    return result


def getBenchmarks(server, refresh: bool = False) -> dict:
    """The server's benchmarks, cached for 5 minutes. Errors are not cached, so the next look tries again"""
    key = f'{KEY_SERVER_BENCHMARKS}:{server.id}'
    if not refresh:
        cached = redisClient.get(key)
        if cached is not None:
            return {**json.loads(cached), 'cached': True}
    benchmarks = fetchBenchmarks(server)
    if 'error' not in benchmarks:
        redisClient.set(key, json.dumps(benchmarks), ex=CACHE_SECONDS)
    return {**benchmarks, 'cached': False}
