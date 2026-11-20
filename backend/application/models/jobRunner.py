#!/usr/bin/env python3
"""Runs jobs: each pending server unit in a thread pool, results recorded and sent to the job's owner as they come.
Units only talk to MISP; every database write happens in the runner's thread"""

import concurrent.futures
import time
from typing import Optional

from flask import current_app

import application
import application.models.jobs as jobModel
from application.DBModels import Job, JobResult, Server, User, db
from application.models.jobUnits import execute
from application.models.jobs import UnitResult

DEFAULT_MAX_CONCURRENCY = 5
CANCEL_FLAG_TTL = 7 * 86400  # A flag outlives any job; it is removed when the job ends


def cancelKey(job_id: str) -> str:
    return f'job-cancel:{job_id}'


def requestCancel(job_id: str) -> None:
    """Units not started yet are recorded as cancelled; units already running finish"""
    application.redisClient.set(cancelKey(job_id), 1, ex=CANCEL_FLAG_TTL)


def cancelRequested(job_id: str) -> bool:
    return application.redisClient.exists(cancelKey(job_id)) > 0


def clearCancel(job_id: str) -> None:
    application.redisClient.delete(cancelKey(job_id))


def progressPayload(job: Job, result: JobResult) -> dict:
    done = sum(1 for row in job.results if row.status != 'pending')
    return {
        'job_id': job.id,
        'done': done,
        'total': job.total,
        'succeeded': job.succeeded,
        'failed': job.failed,
        'result': jobModel.serializeResult(result),
    }


def safeEmit(emit, *args) -> None:
    """Socket problems must never stop a job or lose its results"""
    if emit is None:
        return
    try:
        emit(*args)
    except Exception:
        current_app.logger.exception('Could not send a job update')


def runUnit(app, kind: str, job_id: str, result_id: int, server_id: int, params: dict):
    """In a pool thread: (result_id, UnitResult or None when cancelled, started, finished). The server is loaded in a
    session of the thread's own, so that units never share the runner's session"""
    with app.app_context():
        if cancelRequested(job_id):
            return result_id, None, None, None
        server = db.session.get(Server, server_id)
        started = time.time()
        if server is None:
            unit = UnitResult(False, skipped=True, summary='The server was deleted')
        else:
            unit = execute(kind, server, params, job_id=job_id)
        return result_id, unit, started, time.time()


def run(job_id: str, emitter=None, max_concurrency: Optional[int] = None) -> Optional[Job]:
    """Run a queued job to its end. Returns None when there is nothing to run (unknown job, or not queued: a task
    delivered twice does not run the job twice)"""
    job = db.session.get(Job, job_id)
    if job is None or job.status != 'queued':
        return None
    concurrency = max(1, int(max_concurrency or DEFAULT_MAX_CONCURRENCY))
    kind = job.kind
    params = job.secret_params
    pending = [row for row in job.results if row.status == 'pending']
    rowsById = {row.id: row for row in pending}
    jobModel.start(job)

    onProgress = getattr(emitter, 'job_progress', None)
    onDone = getattr(emitter, 'job_done', None)
    safeEmit(getattr(emitter, 'job_started', None), job)
    app = current_app._get_current_object()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {}
        for row in pending:
            if row.server_id is None:  # The server was deleted after the job was created
                jobModel.recordResult(row, 'skipped', summary='The server was deleted')
                safeEmit(onProgress, job, progressPayload(job, row))
                continue
            future = pool.submit(runUnit, app, kind, job.id, row.id, row.server_id, params)
            futures[future] = row.id
        for future in concurrent.futures.as_completed(futures):
            row = rowsById[futures[future]]
            try:
                _, unit, started, finished = future.result()
            except Exception as e:  # runUnit itself failed (database, Redis): the unit did not run
                current_app.logger.exception(f'Job {job.id}: unit on server {row.server_id} failed to run')
                unit, started, finished = UnitResult(False, summary=f'Could not run: {e}'), None, None
            if unit is None:
                jobModel.recordResult(row, 'cancelled', summary='Cancelled before it started')
            else:
                jobModel.recordUnit(row, unit, started=started, finished=finished)
            safeEmit(onProgress, job, progressPayload(job, row))

    # Cancelled only if a server was left out: a cancel arriving once every server had started changes nothing
    jobModel.finish(job, cancelled=any(row.status == 'cancelled' for row in job.results))
    clearCancel(job.id)
    safeEmit(onDone, job)
    return job


def runInline(user: User, kind: str, server: Server, params: dict, title: str = '', emitter=None) -> UnitResult:
    """Run a single-server write now, in the caller's thread, and record it as a one-server job. Recording is best
    effort: a failure to record is logged and never hides the outcome of the write"""
    started = time.time()
    unit = execute(kind, server, params)
    finished = time.time()
    try:
        job = jobModel.create(user, kind, [server], params=params, title=title, fleet=server.fleet, commit=False)
        job.status = 'running'
        job.started = started
        jobModel.recordUnit(job.results[0], unit, started=started, finished=finished, commit=False)
        jobModel.finish(job)
        safeEmit(getattr(emitter, 'job_done', None), job)
    except Exception:
        db.session.rollback()
        current_app.logger.exception(f'Could not record the `{kind}` job on server {server.id}')
    return unit
