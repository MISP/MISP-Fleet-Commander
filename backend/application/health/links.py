"""Health of one sync link: a server's connection to a remote MISP, as tested by MISP (`/servers/testConnection`) and
described by the remote user (`/servers/getRemoteUser`).

`classify_link` reads a connection of the `connectedServers` snapshot section (`Server` plus the parsed
`connectionTest` and `connectionUser`) and returns its level with the reasons for it:
- `broken`: the link does not work for what it is configured to do;
- `degraded`: it works, but with a limitation or on an outdated remote;
- `unknown`: there is no test result (never tested, or the test did not complete);
- `ok`: none of the above.

Independently of the level, a link whose every sync direction and caching are off is `disabled`: it is configured but
not used, often a leftover.
"""

from typing import Optional

from application.health.versions import format_version, how_far_behind, parse_version

LEVELS = ("broken", "degraded", "unknown", "ok")
LEVEL_RANK = {level: rank for rank, level in enumerate(LEVELS)}

# Everything a link can do. When all of them are off, the link is not used
USAGE_FLAGS = ("push", "pull", "push_sightings", "push_galaxy_clusters", "pull_galaxy_clusters", "push_analyst_data",
               "pull_analyst_data", "push_collections", "pull_collections", "caching_enabled")

# Same codes as the connection test parser. Snapshots taken before the parser kept MISP's raw status code only have
# the message, so the code is recovered from it
STATUS_MESSAGES = {
    "Server unreachable": 2,
    "Unexpected error": 3,
    "Authentication failed": 4,
    "Password change required": 5,
    "Terms not accepted": 6,
    "Remote user is not a sync user": 7,
    "Syncing sightings only": 8,
}
STATUS_NOT_SYNC_USER = 7
STATUS_SIGHTINGS_ONLY = 8
POST_FAILURES = (8, 9, 10)
POST_FAILURE_MESSAGES = ("Could not POST message", "Invalid body", "Invalid headers")
# How request errors start (see `asyncFetcher`), for snapshots taken before the parser flagged them as `test_error`
REQUEST_ERROR_PREFIXES = ("Timeout Exception", "Connection Error", "Unhandled Exception")


def is_enabled(flag) -> bool:
    if isinstance(flag, str):
        return flag.strip().lower() in ("1", "true")
    return bool(flag)


def _reason(level: str, code: str, message: str) -> dict:
    return {"level": level, "code": code, "message": message}


def _statusCode(status: dict) -> Optional[int]:
    code = status.get("code")
    if isinstance(code, int):
        return code
    if status.get("color") == "success":
        return 1
    return STATUS_MESSAGES.get(status.get("message"))


def _testError(test: dict, status: dict) -> Optional[str]:
    if test.get("test_error"):
        return str(test["test_error"])
    message = status.get("message")
    if "code" not in status and isinstance(message, str) and message.startswith(REQUEST_ERROR_PREFIXES):
        return message
    return None


def _postFailed(post: dict) -> bool:
    code = post.get("code")
    if code is not None:
        return code in POST_FAILURES
    return post.get("result") in POST_FAILURE_MESSAGES


def classify_link(link: dict, latest_release: Optional[str] = None) -> dict:
    """`{level, reasons, disabled, push, pull, tested_at}`. Each reason is `{level, code, message}`; the link's level
    is the worst of its reasons' (`ok` when there is none). `latest_release` (e.g. `v2.5.1`) enables the outdated
    remote check"""
    remote = link.get("Server") if isinstance(link.get("Server"), dict) else {}
    push, pull = is_enabled(remote.get("push")), is_enabled(remote.get("pull"))
    disabled = not any(is_enabled(remote.get(flag)) for flag in USAGE_FLAGS)
    test = link.get("connectionTest") if isinstance(link.get("connectionTest"), dict) else None
    status = test.get("status") if test is not None and isinstance(test.get("status"), dict) else None
    result = {"level": "ok", "reasons": [], "disabled": disabled, "push": push, "pull": pull,
              "tested_at": test.get("timestamp") if test is not None else None}
    reasons = result["reasons"]

    if status is None:
        reasons.append(_reason("unknown", "not_tested", "The link has not been tested yet"))
        return _finish(result)
    testError = _testError(test, status)
    if testError is not None:
        reasons.append(_reason("unknown", "test_failed", f"The test did not complete: {testError}"))
        return _finish(result)

    code = _statusCode(status)
    if code is None or (code not in (1, STATUS_NOT_SYNC_USER, STATUS_SIGHTINGS_ONLY)):
        reasons.append(_reason("broken", "status", status.get("message") or "Unknown test result"))
        return _finish(result)

    # The remote user: from the test's status code, or from `getRemoteUser` when it could be read
    user = link.get("connectionUser") if isinstance(link.get("connectionUser"), dict) else {}
    userKnown = bool(user.get("email"))
    notSyncUser = code == STATUS_NOT_SYNC_USER or (userKnown and not user.get("sync_flag"))
    if notSyncUser:
        who = f"Remote user {user['email']}" if userKnown else "The remote user"
        if push:
            reasons.append(_reason("broken", "no_sync_permission",
                                   f"{who} lacks the sync permission: the remote refuses pushes"))
        elif pull:
            reasons.append(_reason("degraded", "no_sync_permission",
                                   f"{who} lacks the sync permission: pulls only get what that user can see"))
    if code == STATUS_SIGHTINGS_ONLY:
        reasons.append(_reason("degraded", "sightings_only", "The remote only accepts sightings"))

    compatibility = test.get("compatibility") if isinstance(test.get("compatibility"), dict) else {}
    localVersion, remoteVersion = test.get("localVersion") or "?", test.get("remoteVersion") or "?"
    versions = f"local {localVersion}, remote {remoteVersion}"
    if compatibility.get("color") == "danger":
        reasons.append(_reason("broken", "incompatible", f"Incompatible MISP versions ({versions})"))
    elif compatibility.get("message") == "Pull only":
        if push:
            reasons.append(_reason("broken", "pull_only",
                                   f"The remote runs an older minor version, so it can only be pulled from ({versions})"))
        else:
            reasons.append(_reason("degraded", "pull_only", f"The remote can only be pulled from ({versions})"))
    elif compatibility.get("color") == "warning" and compatibility.get("message") not in ("", "Compatible", None):
        reasons.append(_reason("degraded", "compatibility", compatibility["message"]))
    elif compatibility.get("color") == "warning" or compatibility.get("mismatch") not in (None, False, "proposal"):
        # Hotfix versions differ, or major versions that MISP still syncs (`major_compatible`, e.g. 3.0 and 2.5)
        outdated = "local" if compatibility.get("newer") == "remote" else "remote"
        reasons.append(_reason("degraded", "version_mismatch",
                               f"MISP versions differ ({versions}): the {outdated} instance should be updated"))

    if push:
        post = test.get("post") if isinstance(test.get("post"), dict) else {}
        if _postFailed(post):
            reasons.append(_reason("broken", "push_test_failed", f"Push test failed: {post.get('result')}"))

    current, latest = parse_version(test.get("remoteVersion")), parse_version(latest_release)
    if how_far_behind(current, latest) is not None:
        reasons.append(_reason("degraded", "remote_outdated", f"The remote runs {format_version(current)}, "
                                                              f"the latest release is {format_version(latest)}"))
    return _finish(result)


def _finish(result: dict) -> dict:
    if result["reasons"]:
        result["level"] = min((reason["level"] for reason in result["reasons"]), key=LEVEL_RANK.__getitem__)
    return result


def latest_release_for(snapshot: Optional[dict], latest_release: Optional[str]) -> Optional[str]:
    """GitHub's latest release, or the one the server's MISP reports when GitHub cannot be reached from here"""
    if latest_release:
        return latest_release
    queryResult = (snapshot or {}).get("query_result") if isinstance(snapshot, dict) else None
    settings = (queryResult or {}).get("serverSettings") if isinstance(queryResult, dict) else None
    version = settings.get("version") if isinstance(settings, dict) else None
    return version.get("newest") if isinstance(version, dict) else None
