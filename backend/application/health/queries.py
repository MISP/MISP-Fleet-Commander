"""Saved queries watched on a schedule: what each server last answered, checked against what the saved query
expects (see `models.savedQueries`).

A server whose answer does not meet the expectation gets an issue of the saved query's severity. A server where the
last run could not check it (no complex queries, mistakes MISP found in the query, no permission, too slow…) gets an
`info` issue of its own id, so that acknowledging one never hides the other. Saved queries run by hand only, or
without an expectation, raise nothing: a run by hand is a moment, not a watch.
"""

from application.health.engine import Finding, rule


def checksFor(ctx, server) -> list:
    """The saved queries of the server's owner watched on this server, read once per owner and evaluation"""
    userId = getattr(server, "user_id", None)
    if userId is None:
        return []
    cache = ctx.saved_queries
    if userId not in cache:
        from application.models.savedQueries import healthChecks
        cache[userId] = healthChecks(userId)
    return cache[userId].get(server.id, [])


def evidenceOf(check: dict) -> dict:
    result = check["result"]
    return {"saved_query_id": check["id"], "name": check["name"], "statement": check["statement"],
            "comparator": check["comparator"], "expected": check["expected"], "outcome": result["outcome"],
            "value": result["value"], "more": result["more"], "checked_at": result["checked_at"],
            "job_id": result["job_id"]}


def unmetFinding(check: dict) -> Finding:
    from application.models.savedQueries import expectationText, foundText
    expected = expectationText(check["kind"], check["comparator"], check["expected"])
    found = foundText(check["result"])
    detail = check["description"] or f"Runs {oneLine(check['statement'])}"
    return Finding(
        check["severity"],
        f"Saved query “{check['name']}”: expected {expected}, {found}",
        f"{detail.rstrip('.')}.",
        subject=str(check["id"]),
        evidence=evidenceOf(check),
        action={"kind": "open_saved_query", "saved_query_id": check["id"]},
    )


def uncheckedFinding(check: dict) -> Finding:
    message = check["result"]["message"] or f"It ended as `{check['result']['outcome']}`"
    message = message[:1].upper() + message[1:]  # mispql's messages start in lower case
    return Finding(
        "info",
        f"Saved query “{check['name']}” could not run",
        f"{message.rstrip('.')}. Its expectation is not checked on this server.",
        subject=f"{check['id']}:unchecked",
        evidence=evidenceOf(check),
        action={"kind": "open_saved_query", "saved_query_id": check["id"]},
    )


def oneLine(statement: str) -> str:
    from application.models.fleetQueries import title
    return title(statement)


@rule("saved_query", "queries")
def savedQuery(state, ctx):
    from application.models.savedQueries import UNCHECKED, UNMET, aims, judge
    server = state.server
    for check in checksFor(ctx, server):
        if not aims(check, server):
            continue
        verdict = judge(check["comparator"], check["expected"], check["result"])
        if verdict == UNMET:
            yield unmetFinding(check)
        elif verdict == UNCHECKED:
            yield uncheckedFinding(check)
