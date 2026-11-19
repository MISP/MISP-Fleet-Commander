"""Health of a user's servers: issues from the health engine, acknowledgements, and live updates over socket.io.

Health is computed on read (from the snapshots and connection tests in Redis). An acknowledgement hides one
occurrence of an issue: it applies while `until` has not passed and the issue keeps the first-seen time it had when
it was acknowledged, so an issue that clears and comes back is shown again.
"""

import time
from typing import Dict, Iterable, List, Optional

from application.DBModels import Fleet, HealthAck, Server, User, db
from application.health import CATEGORIES, SEVERITIES, Context, evaluate_server, sort_issues

MAX_NOTE_LENGTH = 500
# Issues a bulk acknowledgement takes at once: a baseline drifting on every server stays well below
MAX_BULK_ISSUES = 10_000


class HealthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def issueServerId(issue_id) -> Optional[int]:
    """The server an issue ID (`{rule}:{server_id}[:{subject}]`) is about"""
    if not isinstance(issue_id, str):
        return None
    parts = issue_id.split(":", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


def ackApplies(ack: Optional[HealthAck], issue, now: int) -> bool:
    return ack is not None and ack.issue_first_seen == issue.first_seen and (ack.until is None or ack.until > now)


def serializeAck(ack: HealthAck) -> dict:
    return {"until": ack.until, "note": ack.note, "created": ack.created}


def serializeIssue(issue, server, ack: Optional[HealthAck], now: int) -> dict:
    data = issue.to_dict()
    data["server_name"] = server.name
    data["server_url"] = server.url
    data["fleet_name"] = server.fleet.name if server.fleet is not None else None
    data["ack"] = serializeAck(ack) if ackApplies(ack, issue, now) else None
    return data


def acksByIssue(user_id: int, server_ids: Iterable[int]) -> Dict[str, HealthAck]:
    server_ids = list(server_ids)
    if not server_ids:
        return {}
    acks = HealthAck.query.filter(HealthAck.user_id == user_id, HealthAck.server_id.in_(server_ids)).all()
    return {ack.issue_id: ack for ack in acks}


def evaluateServers(user, servers: List[Server], ctx: Optional[Context] = None,
                    snapshotTimes: Optional[Dict[int, Optional[int]]] = None) -> List[dict]:
    """Every current issue of the given servers (all owned by `user`), acknowledged or not, most severe first.
    `snapshotTimes`, when given, receives the time of each server's snapshot (None without one): reading a snapshot
    again for it would decode it a second time"""
    from application import redisModel
    ctx = ctx or Context.for_user(user)
    acks = acksByIssue(user.id, [server.id for server in servers])
    serverByID = {server.id: server for server in servers}
    issues = []
    for server in servers:
        snapshot = redisModel.getServerInfo(server.uuid)
        if snapshotTimes is not None:
            snapshotTimes[server.id] = snapshotTimestamp(snapshot)
        issues.extend(evaluate_server(server, ctx, snapshot=snapshot))
    return [serializeIssue(issue, serverByID[issue.server_id], acks.get(issue.id), ctx.now)
            for issue in sort_issues(issues)]


def parseChoices(value: Optional[str], allowed, name: str) -> Optional[set]:
    """A comma-separated filter, e.g. `severity=critical,warning`"""
    if value is None or value.strip() == "":
        return None
    choices = {choice.strip() for choice in value.split(",") if choice.strip()}
    unknown = choices - set(allowed)
    if unknown:
        raise HealthError(f"Unknown {name}: {', '.join(sorted(unknown))}. Expected: {', '.join(allowed)}")
    return choices


def ownedServers(user, fleet_id: Optional[int] = None, server_id: Optional[int] = None) -> List[Server]:
    if fleet_id is not None and Fleet.query.filter_by(id=fleet_id, user_id=user.id).first() is None:
        raise HealthError("Unknown fleet", 404)
    q = Server.query.filter_by(user_id=user.id)
    if fleet_id is not None:
        q = q.filter_by(fleet_id=fleet_id)
    if server_id is not None:
        q = q.filter_by(id=server_id)
        if q.first() is None:
            raise HealthError("Unknown server", 404)
    return q.all()


def issuesForUser(user, fleet_id=None, server_id=None, severity=None, category=None, include_acked=False) -> List[dict]:
    severities = parseChoices(severity, SEVERITIES, "severity")
    categories = parseChoices(category, CATEGORIES, "category")
    issues = evaluateServers(user, ownedServers(user, fleet_id, server_id))
    return [
        issue for issue in issues
        if (include_acked or issue["ack"] is None)
        and (severities is None or issue["severity"] in severities)
        and (categories is None or issue["category"] in categories)
    ]


def emptyCounts() -> dict:
    return {severity: 0 for severity in SEVERITIES}


def summaryForUser(user) -> dict:
    """Counts of the issues that are not acknowledged: in total, per fleet, and the worst severity of each server
    (listed with its name and fleet, so that healthy servers can be shown too)"""
    ctx = Context.for_user(user)
    servers = ownedServers(user)
    snapshotTimes = {}
    issues = evaluateServers(user, servers, ctx, snapshotTimes)
    fleetIDs = [fleet_id for (fleet_id,) in db.session.query(Fleet.id).filter_by(user_id=user.id).all()]

    totals = emptyCounts()
    fleets = {fleet_id: emptyCounts() for fleet_id in fleetIDs}
    issuesByServer = {server.id: [] for server in servers}
    acknowledged = 0
    for issue in issues:
        if issue["ack"] is not None:
            acknowledged += 1
            continue
        totals[issue["severity"]] += 1
        fleets.setdefault(issue["fleet_id"], emptyCounts())[issue["severity"]] += 1
        issuesByServer[issue["server_id"]].append(issue)

    refreshTimes = [ts for ts in snapshotTimes.values() if ts is not None]
    return {
        "totals": totals,
        "acknowledged": acknowledged,
        "fleets": fleets,
        "servers": {server.id: {"name": server.name, "fleet_id": server.fleet_id,
                                "worst": worstSeverity(issuesByServer[server.id])} for server in servers},
        "server_count": len(servers),
        "oldest_refresh": min(refreshTimes) if refreshTimes else None,
        "newest_refresh": max(refreshTimes) if refreshTimes else None,
        "evaluated_at": ctx.now,
    }


def worstSeverity(issues: List[dict]) -> Optional[str]:
    ranks = [SEVERITIES.index(issue["severity"]) for issue in issues]
    return SEVERITIES[min(ranks)] if ranks else None


def snapshotTimestamp(snapshot) -> Optional[int]:
    timestamp = snapshot.get("timestamp") if isinstance(snapshot, dict) else None
    return timestamp if isinstance(timestamp, int) else None


def currentIssue(user, issue_id: str):
    """The server and the current issue behind an issue ID, for one of the user's servers"""
    server_id = issueServerId(issue_id)
    server = Server.query.filter_by(id=server_id, user_id=user.id).first() if server_id is not None else None
    if server is None:
        raise HealthError("Unknown issue", 404)
    for issue in evaluate_server(server, Context.for_user(user)):
        if issue.id == issue_id:
            return server, issue
    raise HealthError("This issue is not current: it may have cleared since", 404)


def validAckFields(until, note, now: int) -> str:
    """Check an acknowledgement's `until` and `note`; return the note to store"""
    if until is not None:
        if isinstance(until, bool) or not isinstance(until, int):
            raise HealthError("`until` must be a UNIX timestamp")
        if until <= now:
            raise HealthError("`until` must be in the future")
    note = "" if note is None else note
    if not isinstance(note, str):
        raise HealthError("`note` must be text")
    if len(note) > MAX_NOTE_LENGTH:
        raise HealthError(f"`note` must be at most {MAX_NOTE_LENGTH} characters long")
    return note.strip()


def saveAck(user, server, issue, ack: Optional[HealthAck], until, note: str, now: int) -> HealthAck:
    """Create or update the user's acknowledgement of `issue` (not committed)"""
    if ack is None:
        ack = HealthAck(user_id=user.id, server_id=server.id, issue_id=issue.id)
        db.session.add(ack)
    ack.issue_first_seen = issue.first_seen
    ack.until = until
    ack.note = note
    ack.created = now
    return ack


def acknowledge(user, issue_id, until=None, note=None) -> dict:
    now = int(time.time())
    note = validAckFields(until, note, now)
    server, issue = currentIssue(user, issue_id)

    ack = saveAck(user, server, issue, HealthAck.query.filter_by(user_id=user.id, issue_id=issue_id).first(),
                  until, note, now)
    db.session.commit()
    publishServerHealth(server)
    return serializeIssue(issue, server, ack, now)


def unacknowledge(user, issue_id: str) -> None:
    ack = HealthAck.query.filter_by(user_id=user.id, issue_id=issue_id).first()
    if ack is None:
        raise HealthError("This issue is not acknowledged", 404)
    server = Server.query.get(ack.server_id)
    db.session.delete(ack)
    db.session.commit()
    if server is not None:
        publishServerHealth(server)


def validIssueIds(issue_ids) -> List[str]:
    """The issue IDs of a bulk request, without duplicates, in the order given"""
    if not isinstance(issue_ids, list) or not issue_ids or not all(isinstance(i, str) for i in issue_ids):
        raise HealthError("`issue_ids` must be a non-empty list of issue IDs")
    unique = list(dict.fromkeys(issue_ids))
    if len(unique) > MAX_BULK_ISSUES:
        raise HealthError(f"At most {MAX_BULK_ISSUES} issues can be changed at once")
    return unique


def ownedServersOf(user, issue_ids: List[str]) -> Dict[int, Server]:
    """The user's servers that the given issue IDs are about, by ID"""
    server_ids = {issueServerId(issue_id) for issue_id in issue_ids} - {None}
    if not server_ids:
        return {}
    servers = Server.query.filter(Server.user_id == user.id, Server.id.in_(server_ids)).all()
    return {server.id: server for server in servers}


def acknowledgeMany(user, issue_ids, until=None, note=None) -> dict:
    """Acknowledge several current issues at once, with the same `until` and `note`. Issues that are unknown, someone
    else's or no longer current are skipped: some clearing meanwhile is expected. Each server is evaluated once and
    its health published once"""
    now = int(time.time())
    note = validAckFields(until, note, now)
    issue_ids = validIssueIds(issue_ids)
    servers = ownedServersOf(user, issue_ids)
    ctx = Context.for_user(user)
    current = {}  # issue ID -> current issue, for the servers asked about
    for server in servers.values():
        for issue in evaluate_server(server, ctx):
            current[issue.id] = issue
    acks = acksByIssue(user.id, servers.keys())

    acknowledged, skipped, touched = [], [], {}
    for issue_id in issue_ids:
        server = servers.get(issueServerId(issue_id))
        if server is None:
            skipped.append({"issue_id": issue_id, "message": "Unknown issue"})
            continue
        issue = current.get(issue_id)
        if issue is None:
            skipped.append({"issue_id": issue_id, "message": "This issue is not current: it may have cleared since"})
            continue
        ack = saveAck(user, server, issue, acks.get(issue_id), until, note, now)
        acknowledged.append(serializeIssue(issue, server, ack, now))
        touched[server.id] = server
    if touched:
        db.session.commit()
        for server in touched.values():
            publishServerHealth(server)
    return {"acknowledged": acknowledged, "skipped": skipped}


def unacknowledgeMany(user, issue_ids) -> dict:
    """Remove several acknowledgements at once. Issues that are not acknowledged are skipped"""
    issue_ids = validIssueIds(issue_ids)
    servers = ownedServersOf(user, issue_ids)
    acks = acksByIssue(user.id, servers.keys())

    unacknowledged, skipped, touched = [], [], {}
    for issue_id in issue_ids:
        ack = acks.get(issue_id)
        if ack is None:
            skipped.append({"issue_id": issue_id, "message": "This issue is not acknowledged"})
            continue
        db.session.delete(ack)
        unacknowledged.append(issue_id)
        touched[ack.server_id] = servers[ack.server_id]
    if touched:
        db.session.commit()
        for server in touched.values():
            publishServerHealth(server)
    return {"unacknowledged": unacknowledged, "skipped": skipped}


def healthPayload(server, issues: List[dict]) -> dict:
    return {"server_id": server.id, "fleet_id": server.fleet_id, "issues": issues}


def publishServerHealth(server) -> None:
    """Re-evaluate a server and send its issues (acknowledged ones included, flagged by `ack`) to its owner. Called
    whenever the server's snapshot or connection test changes. Never raises: health must not break a refresh"""
    try:
        from application.controllers.websocket import socketEmitter
        owner = User.query.get(server.user_id)
        if owner is None:
            return
        socketEmitter.health_updated(server, healthPayload(server, evaluateServers(owner, [server])))
    except Exception as e:
        print(f"Could not publish the health of server {getattr(server, 'id', server)}: {e}")


def publishServerRemoved(server) -> None:
    """A deleted server has no issues left"""
    try:
        from application.controllers.websocket import socketEmitter
        socketEmitter.health_updated(server, healthPayload(server, []))
    except Exception as e:
        print(f"Could not publish the removal of server {getattr(server, 'id', server)}: {e}")
