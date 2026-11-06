"""Health-rules engine: turns what is known about a server (its latest snapshot and connection test) into issues.

Health is computed on read and never stored. The only state kept is when each issue was first seen. Issue IDs are
stable (`{rule}:{server_id}[:{subject}]`), so acknowledgements, history or alerting can be keyed on them.

Rules are plain functions registered with `@rule(...)`. They receive a `ServerState` and a `Context` and yield
`Finding`s; the engine turns findings into `Issue`s. Other modules add rules the same way, without touching the engine.
"""

from dataclasses import asdict, dataclass, field
import time
from typing import Callable, Iterable, List, Optional

from application import redisModel

SEVERITIES = ("critical", "warning", "info")
SEVERITY_RANK = {severity: rank for rank, severity in enumerate(SEVERITIES)}
CATEGORIES = ("availability", "version", "workers", "sync", "services", "config", "freshness", "users")

DEFAULT_WORKER_WARNING_THRESHOLD = 10
DEFAULT_WORKER_DANGER_THRESHOLD = 100
DEFAULT_CONNECTION_TEST_INTERVAL = 5 * 60
DEFAULT_FULL_REFRESH_INTERVAL = 30 * 60


@dataclass
class Finding:
    """What a rule reports. `subject` distinguishes several findings of one rule on one server (a queue, a sync link)"""
    severity: str
    title: str
    detail: str = ""
    subject: Optional[str] = None
    evidence: dict = field(default_factory=dict)
    action: Optional[dict] = None


@dataclass
class Issue:
    id: str
    rule: str
    severity: str
    category: str
    server_id: int
    fleet_id: Optional[int]
    title: str
    detail: str = ""
    subject: Optional[str] = None
    evidence: dict = field(default_factory=dict)
    action: Optional[dict] = None
    first_seen: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Context:
    """Everything rules need besides the server's own data. Built once per evaluation, shared by all servers"""
    now: int
    worker_warning_threshold: int = DEFAULT_WORKER_WARNING_THRESHOLD
    worker_danger_threshold: int = DEFAULT_WORKER_DANGER_THRESHOLD
    latest_release: Optional[str] = None
    connection_test_interval: int = DEFAULT_CONNECTION_TEST_INTERVAL
    full_refresh_interval: int = DEFAULT_FULL_REFRESH_INTERVAL

    @classmethod
    def for_user(cls, user, now: Optional[int] = None, latest_release: Optional[str] = None) -> "Context":
        """Thresholds from the user's settings (the same ones the fleet table uses), intervals from the instance
        settings and the latest MISP release from GitHub (cached)"""
        import application.models.setting as settingModel
        import application.models.userSettings as userSettingsModel
        from application.health.versions import latest_release as lookupLatestRelease

        def userNumber(name, default):
            setting = userSettingsModel.getForUser(user.id, name) if user is not None else None
            try:
                return int(setting.value) if setting is not None and setting.value not in (None, "") else default
            except (TypeError, ValueError):
                return default

        def instanceMinutes(name, default):
            try:
                return int(settingModel.getRefreshValue(name)) * 60
            except (TypeError, ValueError, AttributeError):
                return default

        return cls(
            now=int(time.time()) if now is None else now,
            worker_warning_threshold=userNumber("UI.server_index.worker_warning_threshold", DEFAULT_WORKER_WARNING_THRESHOLD),
            worker_danger_threshold=userNumber("UI.server_index.worker_danger_threshold", DEFAULT_WORKER_DANGER_THRESHOLD),
            latest_release=latest_release if latest_release is not None else lookupLatestRelease(),
            connection_test_interval=instanceMinutes("health_connection_test_interval", DEFAULT_CONNECTION_TEST_INTERVAL),
            full_refresh_interval=instanceMinutes("health_full_refresh_interval", DEFAULT_FULL_REFRESH_INTERVAL),
        )


class ServerState:
    """A server with its latest snapshot (`server-info`) and connection test (`server-status`), plus helpers that
    tolerate missing or failed sections"""

    def __init__(self, server, snapshot: Optional[dict], status: Optional[dict]):
        self.server = server
        self.snapshot = snapshot if isinstance(snapshot, dict) else None
        self.status = status if isinstance(status, dict) else None

    @property
    def query_result(self) -> dict:
        result = (self.snapshot or {}).get("query_result")
        return result if isinstance(result, dict) else {}

    def section(self, name: str):
        """A snapshot section, or None when it is missing or holds an error instead of data"""
        value = self.query_result.get(name)
        return None if section_error(value) is not None else value

    @property
    def server_settings(self) -> dict:
        settings = self.section("serverSettings")
        return settings if isinstance(settings, dict) else {}

    @property
    def final_settings(self) -> dict:
        """`finalSettings` as {setting name: value}"""
        entries = self.server_settings.get("finalSettings")
        if not isinstance(entries, list):
            return {}
        return {entry["setting"]: entry.get("value") for entry in entries if isinstance(entry, dict) and "setting" in entry}


def section_error(value) -> Optional[str]:
    """Why a snapshot section holds no usable data (a fetch error or an HTTP error answer), or None"""
    if isinstance(value, dict):
        if "error" in value:
            return str(value["error"])
        statusCode = value.get("_status_code")
        if isinstance(statusCode, int) and statusCode >= 400:
            return str(value.get("message") or value.get("name") or f"HTTP {statusCode}")
    return None


@dataclass
class Rule:
    name: str
    category: str
    evaluate: Callable[[ServerState, Context], Iterable[Finding]]
    requires_reachable: bool = True


RULES: List[Rule] = []


def rule(name: str, category: str, requires_reachable: bool = True):
    """Register a rule. Rules with `requires_reachable` (the default) read the snapshot's content; they are skipped
    while the server fails its connection test, so that one root cause is reported once and old data does not
    produce misleading issues"""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category `{category}`")

    def decorator(fn):
        if any(registered.name == name for registered in RULES):
            raise ValueError(f"Rule `{name}` is already registered")
        RULES.append(Rule(name=name, category=category, evaluate=fn, requires_reachable=requires_reachable))
        return fn
    return decorator


def issue_id(rule_name: str, server_id: int, subject: Optional[str] = None) -> str:
    return f"{rule_name}:{server_id}" if subject is None else f"{rule_name}:{server_id}:{subject}"


def _runRules(rules: Iterable[Rule], state: ServerState, ctx: Context) -> List[Issue]:
    issues = []
    for registered in rules:
        try:
            findings = list(registered.evaluate(state, ctx) or [])
        except Exception as e:  # A broken rule must not hide the other issues
            print(f"Health rule `{registered.name}` failed on server {state.server.id}: {e}")
            continue
        for finding in findings:
            if finding.severity not in SEVERITY_RANK:
                raise ValueError(f"Rule `{registered.name}` returned an unknown severity `{finding.severity}`")
            subject = None if finding.subject is None else str(finding.subject)
            issues.append(Issue(
                id=issue_id(registered.name, state.server.id, subject),
                rule=registered.name,
                severity=finding.severity,
                category=registered.category,
                server_id=state.server.id,
                fleet_id=getattr(state.server, "fleet_id", None),
                title=finding.title,
                detail=finding.detail,
                subject=subject,
                evidence=finding.evidence,
                action=finding.action,
            ))
    return issues


def evaluate_state(state: ServerState, ctx: Context) -> List[Issue]:
    """Run every rule on one server, without touching first-seen tracking"""
    ensure_rules_loaded()
    issues = _runRules([registered for registered in RULES if not registered.requires_reachable], state, ctx)
    unreachable = any(issue.category == "availability" and issue.severity == "critical" for issue in issues)
    if not unreachable:
        issues += _runRules([registered for registered in RULES if registered.requires_reachable], state, ctx)
    return sort_issues(issues)


def evaluate_server(server, ctx: Context, snapshot: Optional[dict] = None, status: Optional[dict] = None,
                    track_first_seen: bool = True) -> List[Issue]:
    """Issues of one server. Its snapshot and connection test are read from Redis unless given"""
    if snapshot is None:
        snapshot = redisModel.getServerInfo(server.uuid)
    if status is None:
        status = redisModel.getServerStatus(server.uuid)
    issues = evaluate_state(ServerState(server, snapshot, status), ctx)
    if track_first_seen:
        attach_first_seen(server.id, issues, ctx.now)
    return sort_issues(issues)


def evaluate_servers(servers: Iterable, ctx: Context) -> List[Issue]:
    issues = []
    for server in servers:
        issues.extend(evaluate_server(server, ctx))
    return sort_issues(issues)


def sort_issues(issues: List[Issue]) -> List[Issue]:
    """Most severe first, then oldest first"""
    return sorted(issues, key=lambda issue: (SEVERITY_RANK[issue.severity],
                                             issue.first_seen if issue.first_seen is not None else float("inf"),
                                             issue.server_id, issue.id))


def worst_severity(issues: Iterable[Issue]) -> Optional[str]:
    ranks = [SEVERITY_RANK[issue.severity] for issue in issues]
    return SEVERITIES[min(ranks)] if ranks else None


def attach_first_seen(server_id: int, issues: List[Issue], now: int) -> None:
    """Record when each current issue appeared and forget the ones that cleared, so that an issue that clears and
    comes back starts a new "since"."""
    firstSeen = redisModel.syncHealthFirstSeen(server_id, [issue.id for issue in issues], now)
    for issue in issues:
        issue.first_seen = firstSeen.get(issue.id, now)


_rulesLoaded = False


def ensure_rules_loaded():
    global _rulesLoaded
    if not _rulesLoaded:
        import application.health.rules  # noqa: F401  (registers the built-in rules)
        _rulesLoaded = True
