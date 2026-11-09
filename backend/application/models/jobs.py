#!/usr/bin/env python3
"""Jobs: writes sent to one or more servers, recorded with one result per server. The jobs table is the record of
who changed what on which server, so what it stores is redacted (no credentials) and bounded in size"""

import json
import re
import time
from typing import Any, Iterable, Optional

from application.DBModels import JOB_KINDS, JOB_RESULT_STATUSES, Fleet, Job, JobResult, Server, User, db

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
    """A copy of `data` where values of credential-looking keys are replaced by `***`, at any depth"""
    if isinstance(data, dict):
        valueIsSensitive = any(isSensitiveSetting(data.get(key)) for key in VALUE_NAMING_KEYS)
        redacted = {}
        for key, value in data.items():
            if isSensitiveKey(key) or (key == 'value' and valueIsSensitive):
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


def create(user: User, kind: str, servers: Iterable[Server], params: Optional[dict] = None, title: str = '',
           fleet: Optional[Fleet] = None, commit: bool = True) -> Job:
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


def addResult(job: Job, server: Server, status: str, http_status: Optional[int] = None, summary: str = '',
              response: Any = None, before: Any = None, started: Optional[float] = None,
              finished: Optional[float] = None, commit: bool = True) -> JobResult:
    """Record the outcome of the job on one server and update the job's counters. `before` should already be
    redacted with `redactValue` when it is a named value; it is redacted again as a whole"""
    if status not in JOB_RESULT_STATUSES:
        raise ValueError(f'Unknown job result status `{status}`')
    storedResponse, truncated = boundedResponse(response)
    result = JobResult(
        job_id=job.id,
        server_id=server.id,
        server_name=server.name,
        server_url=server.url,
        status=status,
        http_status=http_status,
        summary=(summary or '')[:SUMMARY_MAX_LENGTH],
        response=storedResponse,
        response_truncated=truncated,
        before=redact(before),
        started=started,
        finished=finished if finished is not None else time.time(),
    )
    job.results.append(result)
    if status == 'ok':
        job.succeeded = (job.succeeded or 0) + 1
    elif status == 'error':
        job.failed = (job.failed or 0) + 1
    if commit:
        db.session.commit()
    return result


def finish(job: Job, cancelled: bool = False, commit: bool = True) -> Job:
    job.status = finalStatus(job.succeeded or 0, job.failed or 0, cancelled)
    job.finished = time.time()
    if commit:
        db.session.commit()
    return job


def purge(retention_days: int, now: Optional[float] = None) -> int:
    """Delete the jobs created more than `retention_days` ago, with their results. Returns how many jobs went"""
    cutoff = (now if now is not None else time.time()) - retention_days * 86400
    oldJobIds = db.session.query(Job.id).filter(Job.created < cutoff)
    JobResult.query.filter(JobResult.job_id.in_(oldJobIds.scalar_subquery())).delete(synchronize_session=False)
    count = Job.query.filter(Job.created < cutoff).delete(synchronize_session=False)
    db.session.commit()
    return count
