#!/usr/bin/env python3
"""Jobs: writes sent to one or more servers, recorded with one result per server. The jobs table is the record of
who changed what on which server, so what it stores is redacted (no credentials) and bounded in size"""

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from application.DBModels import JOB_KINDS, JOB_RESULT_FINAL_STATUSES, Fleet, Job, JobResult, Server, User, db

REDACTED = '***'
RESPONSE_MAX_BYTES = 64 * 1024
SUMMARY_MAX_LENGTH = 1024
TITLE_MAX_LENGTH = 255

# Credential words, matched against names lowercased and stripped of separators (`api_key`, `Auth-Key`, `authkey`)
CREDENTIAL_WORDS = r'password|passwd|authkey|apikey|token|secret|secretkey|accesskey|salt|encryptionkey|privatekey'
# Field names: anywhere in the name, so that `password_confirm` or `access_token_value` are covered
SENSITIVE_KEY = re.compile(CREDENTIAL_WORDS)
# Setting names: the last segment must end with the word, so that `Security.password_policy_length` stays readable
# while `MISP.redis_password` or `Security.salt` do not
SENSITIVE_SETTING = re.compile(rf'(?:{CREDENTIAL_WORDS})$')
# A `{"setting": "MISP.redis_password", "value": "…"}` pair carries the secret in `value`: the name sits beside it
VALUE_NAMING_KEYS = ('setting', 'setting_name', 'name', 'key')


def normalisedName(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


def isSensitiveKey(key: Any) -> bool:
    return isinstance(key, str) and SENSITIVE_KEY.search(normalisedName(key)) is not None


def isSensitiveSetting(name: Any) -> bool:
    return isinstance(name, str) and SENSITIVE_SETTING.search(normalisedName(name.rsplit('.', 1)[-1])) is not None


def redact(data: Any) -> Any:
    """A copy of `data` where values of credential-looking keys are replaced by `***`, at any depth. A key holding
    an object or a list is redacted inside instead: MISP wraps records in their model name (`{"AuthKey": {"id": 9,
    "authkey": "…"}}`), and the record itself is worth keeping"""
    if isinstance(data, dict):
        valueIsSensitive = any(isSensitiveSetting(data.get(key)) for key in VALUE_NAMING_KEYS)
        redacted = {}
        for key, value in data.items():
            if isinstance(value, (dict, list, tuple)):
                redacted[key] = redact(value)
            elif isSensitiveKey(key) or (key == 'value' and valueIsSensitive):
                redacted[key] = REDACTED if value not in (None, '') else value
            else:
                redacted[key] = redact(value)
        return redacted
    if isinstance(data, (list, tuple)):
        return [redact(item) for item in data]
    return data


def redactValue(name: Optional[str], value: Any) -> Any:
    """Redact the value of a MISP setting, e.g. its value before a job changed it"""
    if isSensitiveSetting(name) and value not in (None, ''):
        return REDACTED
    return redact(value)


def boundedResponse(response: Any, max_bytes: int = RESPONSE_MAX_BYTES):
    """(response, truncated): the redacted response, or the start of its JSON text when that is larger than
    `max_bytes`. Values JSON cannot represent are stored as text"""
    if response is None:
        return None, False
    redacted = redact(response)
    text = json.dumps(redacted, default=str)
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return json.loads(text), False
    return encoded[:max_bytes].decode('utf-8', errors='ignore'), True


def finalStatus(succeeded: int, failed: int, cancelled: bool = False) -> str:
    """The status of a job whose units are over. Skipped units count as neither success nor failure"""
    if cancelled:
        return 'cancelled'
    if failed == 0:
        return 'done'
    if succeeded == 0:
        return 'failed'
    return 'partial'


@dataclass
class UnitResult:
    """The outcome of one job unit (the job's write on one server), as the unit executors return it"""
    ok: bool
    http_status: Optional[int] = None
    summary: str = ''
    response: Any = None
    before: Any = None
    skipped: bool = False

    @property
    def status(self) -> str:
        if self.skipped:
            return 'skipped'
        return 'ok' if self.ok else 'error'


def create(user: User, kind: str, servers: Iterable[Server], params: Optional[dict] = None, title: str = '',
           fleet: Optional[Fleet] = None, commit: bool = True) -> Job:
    """A queued job with one pending result per server. `params` are stored twice: redacted for display, and as
    given, encrypted, for the runner and for retries"""
    if kind not in JOB_KINDS:
        raise ValueError(f'Unknown job kind `{kind}`')
    servers = list(servers)
    job = Job(
        user_id=user.id,
        user_email=user.email,
        fleet_id=fleet.id if fleet is not None else None,
        fleet_name=fleet.name if fleet is not None else '',
        kind=kind,
        title=(title or '')[:TITLE_MAX_LENGTH],
        params=redact(params or {}),
        status='queued',
        total=len(servers),
        created=time.time(),
    )
    job.secret_params = params or {}
    for server in servers:
        job.results.append(JobResult(server_id=server.id, server_name=server.name, server_url=server.url,
                                     status='pending'))
    db.session.add(job)
    if commit:
        db.session.commit()
    return job


def start(job: Job, commit: bool = True) -> Job:
    job.status = 'running'
    job.started = time.time()
    if commit:
        db.session.commit()
    return job


def recordResult(result: JobResult, status: str, http_status: Optional[int] = None, summary: str = '',
                 response: Any = None, before: Any = None, started: Optional[float] = None,
                 finished: Optional[float] = None, commit: bool = True) -> JobResult:
    """Record the outcome of a pending result and update its job's counters. `before` should already be redacted
    with `redactValue` when it is a named value; it is redacted again as a whole"""
    if status not in JOB_RESULT_FINAL_STATUSES:
        raise ValueError(f'Unknown job result status `{status}`')
    if result.status != 'pending':
        raise ValueError(f'The result of job {result.job_id} on server {result.server_name} is already recorded')
    storedResponse, truncated = boundedResponse(response)
    result.status = status
    result.http_status = http_status
    result.summary = (summary or '')[:SUMMARY_MAX_LENGTH]
    result.response = storedResponse
    result.response_truncated = truncated
    result.before = redact(before)
    result.started = started
    result.finished = finished if finished is not None else time.time()
    job = result.job
    if status == 'ok':
        job.succeeded = (job.succeeded or 0) + 1
    elif status == 'error':
        job.failed = (job.failed or 0) + 1
    if commit:
        db.session.commit()
    return result


def recordUnit(result: JobResult, unit: UnitResult, started: Optional[float] = None,
               finished: Optional[float] = None, commit: bool = True) -> JobResult:
    return recordResult(result, unit.status, http_status=unit.http_status, summary=unit.summary,
                        response=unit.response, before=unit.before, started=started, finished=finished,
                        commit=commit)


def finish(job: Job, cancelled: bool = False, commit: bool = True) -> Job:
    job.status = finalStatus(job.succeeded or 0, job.failed or 0, cancelled)
    job.finished = time.time()
    if commit:
        db.session.commit()
    return job


def serializeResult(result: JobResult) -> dict:
    return {
        'id': result.id,
        'job_id': result.job_id,
        'server_id': result.server_id,
        'server_name': result.server_name,
        'server_url': result.server_url,
        'status': result.status,
        'http_status': result.http_status,
        'summary': result.summary,
        'response': result.response,
        'response_truncated': bool(result.response_truncated),
        'before': result.before,
        'started': result.started,
        'finished': result.finished,
    }


def serializeJob(job: Job, withResults: bool = False) -> dict:
    """Never includes the encrypted parameters: `params` is the redacted copy"""
    serialized = {
        'id': job.id,
        'user_id': job.user_id,
        'user_email': job.user_email,
        'fleet_id': job.fleet_id,
        'fleet_name': job.fleet_name,
        'kind': job.kind,
        'title': job.title,
        'params': job.params,
        'status': job.status,
        'total': job.total,
        'succeeded': job.succeeded,
        'failed': job.failed,
        'created': job.created,
        'started': job.started,
        'finished': job.finished,
    }
    if withResults:
        serialized['results'] = [serializeResult(result) for result in job.results]
        serialized['done'] = sum(1 for result in job.results if result.status != 'pending')
    return serialized


def purge(retention_days: int, now: Optional[float] = None) -> int:
    """Delete the jobs created more than `retention_days` ago, with their results. Returns how many jobs went"""
    cutoff = (now if now is not None else time.time()) - retention_days * 86400
    oldJobIds = db.session.query(Job.id).filter(Job.created < cutoff)
    JobResult.query.filter(JobResult.job_id.in_(oldJobIds.scalar_subquery())).delete(synchronize_session=False)
    count = Job.query.filter(Job.created < cutoff).delete(synchronize_session=False)
    db.session.commit()
    return count
