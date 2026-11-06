"""Built-in health rules. Thresholds mirror the colours of the fleet table's status cells, unless noted.

Actions tell the UI what to offer next to an issue:
- `{"kind": "test_connection"}` / `{"kind": "refresh"}`: run a connection test / a full refresh of the server;
- `{"kind": "edit_server"}`: open the server's edit form (URL, API key);
- `{"kind": "open_tab", "target": "diagnostic" | "connections" | "profile"}`: open the server at that tab.
"""

from application.health.engine import Finding, rule, section_error
from application.health.versions import format_version, how_far_behind, parse_version

SLOW_LATENCY_SECONDS = 2
# Queues shown in the fleet table, in its order. The `update` queue has no backlog thresholds there
WORKER_QUEUES = ("cache", "default", "prio", "update", "email")
QUEUES_WITHOUT_BACKLOG = ("update",)
SNAPSHOT_SECTIONS = {
    "serverSettings": "diagnostics",
    "serverUser": "the API user",
    "connectedServers": "the sync connections",
    "serverUsage": "usage statistics",
}
PROXY_OK = ("", "OK", "not configured (so not tested)")
ZMQ_STATUS = {
    0: "OK",
    1: "Not enabled",
    2: "Python library not installed correctly",
    3: "ZMQ script not running",
}
MODULE_STATUS = {
    0: "OK",
    1: "System not enabled",
    2: "No modules found",
}

TEST_CONNECTION = {"kind": "test_connection"}
REFRESH = {"kind": "refresh"}
EDIT_SERVER = {"kind": "edit_server"}


def openTab(target):
    return {"kind": "open_tab", "target": target}


def humanDuration(seconds: int) -> str:
    seconds = max(int(seconds), 0)
    if seconds < 90:
        return f"{seconds}s"
    if seconds < 90 * 60:
        return f"{round(seconds / 60)} min"
    if seconds < 36 * 3600:
        return f"{round(seconds / 3600)} h"
    return f"{round(seconds / 86400)} days"


def isAuthFailure(status) -> bool:
    return isinstance(status, dict) and status.get("_status_code") in (401, 403)


# --- Availability: from the connection test (`/servers/getVersion`) ------------------------------------------------

@rule("auth_failed", "availability", requires_reachable=False)
def authFailed(state, ctx):
    if not state.server.authkey:
        yield Finding("critical", "No API key configured", "MISP cannot be queried without an API key.",
                      action=EDIT_SERVER)
    elif isAuthFailure(state.status):
        status = state.status
        detail = status.get("message") or status.get("name") or status.get("error") or ""
        yield Finding("critical", "Authentication failed", str(detail),
                      evidence={"status_code": status.get("_status_code")}, action=EDIT_SERVER)


@rule("unreachable", "availability", requires_reachable=False)
def unreachable(state, ctx):
    status = state.status
    if status is None or not state.server.authkey or isAuthFailure(status):
        return
    if status.get("error") is not None or not status.get("version"):
        detail = status.get("error") or status.get("message") or "The connection test returned no version"
        yield Finding("critical", "Unreachable", str(detail),
                      evidence={"status_code": status.get("_status_code"), "tested_at": status.get("timestamp")},
                      action=TEST_CONNECTION)


@rule("slow", "availability", requires_reachable=False)
def slow(state, ctx):
    status = state.status
    if status is None or not status.get("version") or status.get("error") is not None:
        return
    latency = status.get("_latency")
    if isinstance(latency, (int, float)) and latency >= SLOW_LATENCY_SECONDS:
        yield Finding("warning", "Slow to answer", f"The connection test took {latency:.1f}s.",
                      evidence={"latency": round(latency, 3)}, action=TEST_CONNECTION)


# --- Freshness ------------------------------------------------------------------------------------------------------

@rule("stale", "freshness", requires_reachable=False)
def stale(state, ctx):
    snapshotTimestamp = (state.snapshot or {}).get("timestamp")
    if not isinstance(snapshotTimestamp, (int, float)):
        yield Finding("warning", "Never refreshed", "No data has been collected from this server yet.",
                      subject="snapshot", action=REFRESH)
    else:
        age = ctx.now - int(snapshotTimestamp)
        if age > 2 * ctx.full_refresh_interval:
            yield Finding("warning", "Data is out of date", f"Last refreshed {humanDuration(age)} ago.",
                          subject="snapshot", evidence={"refreshed_at": int(snapshotTimestamp), "age": age},
                          action=REFRESH)

    statusTimestamp = (state.status or {}).get("timestamp")
    if not isinstance(statusTimestamp, (int, float)):
        yield Finding("warning", "Connection never tested", "", subject="connection", action=TEST_CONNECTION)
    else:
        age = ctx.now - int(statusTimestamp)
        if age > 2 * ctx.connection_test_interval:
            yield Finding("warning", "Connection test is out of date", f"Last tested {humanDuration(age)} ago.",
                          subject="connection", evidence={"tested_at": int(statusTimestamp), "age": age},
                          action=TEST_CONNECTION)


# --- Snapshot content -----------------------------------------------------------------------------------------------

@rule("fetch_error", "availability")
def fetchError(state, ctx):
    for section, label in SNAPSHOT_SECTIONS.items():
        error = section_error(state.query_result.get(section))
        if error is not None:
            yield Finding("warning", f"Could not fetch {label}", error, subject=section,
                          evidence={"section": section}, action=REFRESH)


@rule("outdated", "version")
def outdated(state, ctx):
    snapshotVersion = state.server_settings.get("version")
    snapshotVersion = snapshotVersion if isinstance(snapshotVersion, dict) else {}
    currentText = (state.status or {}).get("version") or snapshotVersion.get("current")
    # GitHub's latest release, or the one MISP itself reports when GitHub cannot be reached from here
    latestText = ctx.latest_release or snapshotVersion.get("newest")
    current, latest = parse_version(currentText), parse_version(latestText)
    behind = how_far_behind(current, latest)
    if behind is None:
        return
    severity = "warning" if behind == "patch" else "critical"
    yield Finding(severity, "Outdated MISP", f"Running {format_version(current)}, latest release is {format_version(latest)}.",
                  evidence={"current": format_version(current), "latest": format_version(latest), "behind": behind},
                  action=openTab("diagnostic"))


@rule("background_jobs_disabled", "workers")
def backgroundJobsDisabled(state, ctx):
    if state.final_settings.get("MISP.background_jobs") is False:
        yield Finding("critical", "Background jobs disabled", "MISP.background_jobs is off: jobs run in the web "
                      "requests and scheduled tasks do not run.", action=openTab("diagnostic"))


def queueCounts(queue):
    workers = queue.get("workers") if isinstance(queue, dict) else None
    workers = list(workers.values()) if isinstance(workers, dict) else (workers if isinstance(workers, list) else [])
    dead = sum(1 for worker in workers if not (isinstance(worker, dict) and worker.get("ok")))
    return len(workers), dead


def workerQueues(state):
    """The worker queues to check, or None when the snapshot has no worker data or background jobs are off"""
    if state.final_settings.get("MISP.background_jobs") is False:
        return None
    workers = state.server_settings.get("workers")
    return workers if isinstance(workers, dict) else None


@rule("workers_none", "workers")
def workersNone(state, ctx):
    workers = workerQueues(state)
    if workers is None:
        return
    present = [name for name in WORKER_QUEUES if name in workers]
    if not present:
        yield Finding("critical", "No worker running", "Background jobs are enabled but no worker is running.",
                      action=openTab("diagnostic"))
        return
    for name in WORKER_QUEUES:
        total, _ = queueCounts(workers.get(name))
        if total == 0:
            yield Finding("critical", f"No `{name}` worker running", "", subject=name,
                          evidence={"queue": name, "job_count": (workers.get(name) or {}).get("jobCount")},
                          action=openTab("diagnostic"))


@rule("workers_dead", "workers")
def workersDead(state, ctx):
    workers = workerQueues(state)
    if workers is None:
        return
    for name in WORKER_QUEUES:
        total, dead = queueCounts(workers.get(name))
        if total > 0 and dead > 0:
            severity = "critical" if dead == total else "warning"
            yield Finding(severity, f"Dead `{name}` workers", f"{dead} of {total} workers are not running.",
                          subject=name, evidence={"queue": name, "dead": dead, "total": total},
                          action=openTab("diagnostic"))


@rule("jobs_backlog", "workers")
def jobsBacklog(state, ctx):
    workers = workerQueues(state)
    if workers is None:
        return
    for name in WORKER_QUEUES:
        if name in QUEUES_WITHOUT_BACKLOG:
            continue
        queue = workers.get(name)
        total, dead = queueCounts(queue)
        if total == 0 or dead > 0:  # Already reported as missing or dead workers
            continue
        try:
            jobCount = int(queue.get("jobCount") or 0)
        except (TypeError, ValueError):
            continue
        if jobCount > ctx.worker_danger_threshold:
            severity = "critical"
        elif jobCount > ctx.worker_warning_threshold:
            severity = "warning"
        else:
            continue
        yield Finding(severity, f"`{name}` queue backlog", f"{jobCount} jobs waiting.", subject=name,
                      evidence={"queue": name, "job_count": jobCount, "warning_threshold": ctx.worker_warning_threshold,
                                "danger_threshold": ctx.worker_danger_threshold},
                      action=openTab("diagnostic"))


@rule("zmq", "services")
def zmq(state, ctx):
    """Unlike the fleet table, which shows any non-zero status in red, ZeroMQ being disabled is not an issue"""
    status = state.server_settings.get("zmqStatus")
    if not isinstance(status, int) or status in (0, 1):
        return
    yield Finding("warning", "ZeroMQ not working", ZMQ_STATUS.get(status, f"Unknown status code {status}"),
                  evidence={"status": status}, action=openTab("diagnostic"))


@rule("proxy", "services")
def proxy(state, ctx):
    status = state.server_settings.get("proxyStatus")
    if not isinstance(status, str) or status in PROXY_OK:
        return
    yield Finding("warning", "Proxy not working", status, evidence={"status": status}, action=openTab("diagnostic"))


@rule("modules", "services")
def modules(state, ctx):
    """Unlike the fleet table, a module system that is not enabled is not an issue"""
    statuses = state.server_settings.get("moduleStatus")
    if not isinstance(statuses, dict):
        return
    for name, status in statuses.items():
        code = int(status) if isinstance(status, str) and status.isdigit() else status
        if code in (0, 1):
            continue
        detail = MODULE_STATUS.get(code, f"Status {code}") if isinstance(code, int) else str(status)
        yield Finding("info", f"{name} modules unavailable", detail, subject=name,
                      evidence={"module": name, "status": status}, action=openTab("diagnostic"))


@rule("sync_link", "sync")
def syncLink(state, ctx):
    """Basic version: the colour of each sync connection's test, as in the connection summary"""
    links = state.section("connectedServers")
    if not isinstance(links, list):
        return
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get("Server"), dict):
            continue
        status = (link.get("connectionTest") or {}).get("status")
        if not isinstance(status, dict):
            continue  # Not tested yet
        color = status.get("color")
        if color not in ("warning", "danger"):
            continue
        remote = link["Server"]
        name = remote.get("name") or remote.get("url") or f"#{remote.get('id')}"
        yield Finding("critical" if color == "danger" else "warning", f"Sync link to {name}",
                      status.get("message") or "", subject=remote.get("id"),
                      evidence={"remote_id": remote.get("id"), "remote_name": remote.get("name"),
                                "remote_url": remote.get("url"), "message": status.get("message")},
                      action=openTab("connections"))
