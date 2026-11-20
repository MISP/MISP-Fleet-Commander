"""Fleet queries: one MispQL statement run on many servers, each server's answer read by mispql

A run is a job of kind `mispql_query`, one unit per server on the job runner's pool. The statement is checked here
before any job exists, and each unit compiles it again. mispql builds the requests and reads the answers; MFC sends
them itself, with the server's stored key and settings.

A MISP without complex queries drops a search's `query` without a word and answers as if there were no WHERE. So a
unit asks `GET /attributes/queryDescribe` right before any search, with the same key, and searches only after a 200
listing the tables. That holds for a run, a retry, and anything else that runs this unit.

What a unit keeps:
- its summary (outcome, counts, located errors, a DESCRIBE answer, the tables answering) in the job's result, in
  the database: the record of who asked what of which server;
- the rows it brought back, in Redis only, for a while (`query_rows_ttl_minutes`). Rows are flattened as mispql
  flattens them, and only the asked columns are kept when the statement lists them.
"""
import base64
import json
import re
import time
import zlib
from dataclasses import dataclass
from typing import List, Optional

import mispql
from mispql.compiler import compile_statement
from mispql.errors import position
from mispql.parser import parse

from application import redisModel
from application.controllers.utils import mispRawRequest, sizeText
from application.models import queryCapability
from application.models import setting as settingModel
from application.models.jobs import UnitResult

KIND = 'mispql_query'
MAX_STATEMENT_LENGTH = 100_000

# What a statement is, by its plan. USE, SHOW DATABASES and WHOAMI are about mispql's own connections: here the
# server picker chooses where a statement goes
STATEMENT_KINDS = {
    mispql.SearchPlan: 'select',
    mispql.CountPlan: 'count',
    mispql.DescribePlan: 'describe',
    mispql.ShowTablesPlan: 'show_tables',
}
NOT_RUN_HERE = {mispql.UsePlan: 'USE', mispql.ShowDatabasesPlan: 'SHOW DATABASES', mispql.WhoamiPlan: 'WHOAMI'}
# Statements that search, and so are sent only to a server that has just shown it runs complex queries
SEARCHES = ('select', 'count')

# Outcomes of a unit. Answers are a success; a server without complex queries is skipped: it was not asked anything
ANSWERS = ('rows', 'count', 'describe', 'tables')
SKIPPED = ('not_supported',)
OUTCOMES = ANSWERS + SKIPPED + ('no_permission', 'unavailable', 'unknown', 'query_errors', 'unreachable', 'timeout',
                                'too_large', 'refused', 'bad_answer', 'invalid')

# A page of merged rows
MAX_PAGE_SIZE = 1000
# Columns a server's summary lists (in the database); its rows carry all of them
SUMMARY_COLUMNS = 200


# Checking a statement

class StatementError(Exception):
    """Mistakes in a statement, placed on its text: `errors` is a list of `located` dicts"""

    def __init__(self, errors: List[dict]):
        super().__init__(errors[0]['message'] if errors else 'Invalid statement')
        self.errors = errors


def located(text: str, message: str, start: int, end: int, **extra) -> dict:
    """A mistake as the UI places it: character offsets, and the line and column of its start (1-based)"""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    line, column = position(text, start)
    return {'message': message, 'start': start, 'end': end, 'line': line, 'column': column, **extra}


@dataclass
class Prepared:
    """A statement that may be run: its parsed node and plan, with MFC's limits applied"""
    text: str
    statement: mispql.Statement
    kind: str
    limit: Optional[int] = None
    limit_added: bool = False

    @property
    def plan(self):
        return self.statement.plan

    @property
    def table(self) -> Optional[str]:
        return getattr(self.plan, 'table', None)

    @property
    def columns(self) -> Optional[List[str]]:
        """The asked columns (aliases resolved), or None for `SELECT *`"""
        return getattr(self.plan, 'columns', None)

    def defaultColumns(self) -> Optional[List[str]]:
        """The columns shown first: the asked ones, else the table's own defaults; None when every column is"""
        if self.kind != 'select':
            return None
        if self.columns:
            return list(self.columns)
        if self.plan.output == 'flat':
            return None
        return list(mispql.TABLES[self.table].columns)

    def summary(self) -> dict:
        return {'kind': self.kind, 'table': self.table, 'limit': self.limit, 'limit_added': self.limit_added}


def maxLimit() -> int:
    return settingModel.intValue('query_max_limit')


def prepare(text, max_limit: Optional[int] = None) -> Prepared:
    """Check a statement as MFC runs it; StatementError with every mistake placed on the text otherwise:
    - one statement: SELECT, SELECT COUNT(*), DESCRIBE or SHOW TABLES;
    - no FORMAT but `table` and `flat`: MISP's own formats are not read here;
    - a SELECT asks at most `max_limit` rows of each server, and gets that LIMIT when it has none"""
    if not isinstance(text, str) or text.strip() == '':
        raise StatementError([located('', 'Write a statement', 0, 0)])
    if len(text) > MAX_STATEMENT_LENGTH:
        raise StatementError([located(text, f'A statement takes at most {MAX_STATEMENT_LENGTH} characters',
                                      MAX_STATEMENT_LENGTH, len(text))])
    try:
        nodes = parse(text)
    except mispql.MispQLError as e:
        raise StatementError([located(text, e.message, e.start, e.end)])
    if not nodes:
        raise StatementError([located(text, 'Write a statement', 0, len(text))])
    node = nodes[0]
    if len(nodes) > 1:
        raise StatementError([located(text, 'One statement at a time: run this one on its own',
                                      nodes[1].start, nodes[-1].end)])
    try:
        plan = compile_statement(node, flatten=True)
    except mispql.MispQLError as e:
        raise StatementError([located(text, e.message, e.start, e.end)])
    if type(plan) in NOT_RUN_HERE:
        raise StatementError([located(text, f'{NOT_RUN_HERE[type(plan)]} is not run here: choose the servers to '
                                            'query with the server picker', node.start, node.end)])
    prepared = Prepared(text=text, statement=mispql.Statement(node, plan), kind=STATEMENT_KINDS[type(plan)])
    if prepared.kind == 'select':
        if plan.output == 'verbatim':
            word = node.format
            raise StatementError([located(text, f'FORMAT {word.value} is MISP\'s own format, not read here: use '
                                                'FORMAT table, FORMAT flat or none. Rows can be exported as CSV or '
                                                'JSON', word.start, word.end)])
        cap = max_limit if max_limit is not None else maxLimit()
        if node.limit is None:
            # Set on the request, not written into the text: the offsets of everything else stay right
            plan.body.update(limit=cap, page=1)
            prepared.limit, prepared.limit_added = cap, True
        elif node.limit.value > cap:
            raise StatementError([located(text, f'At most {cap} rows per server: lower the LIMIT',
                                          node.limit.start, node.limit.end)])
        else:
            prepared.limit = node.limit.value
    return prepared


def describeStatement(text) -> dict:
    """What the editor shows of a statement before it is sent: its kind and table, the LIMIT each server gets, the
    columns shown first; or its mistakes"""
    try:
        prepared = prepare(text)
    except StatementError as e:
        return {'ok': False, 'errors': e.errors}
    return {'ok': True, 'errors': [], **prepared.summary(), 'columns': prepared.columns,
            'default_columns': prepared.defaultColumns()}


def title(text: str) -> str:
    """The statement on one line, cut short, as a job title stem"""
    line = re.sub(r'\s+', ' ', text).strip().rstrip(';').strip()
    return line if len(line) <= 100 else f'{line[:99]}…'


# Running it on one server

class Unanswered(Exception):
    """The server gave no answer that could be read: unreachable, too slow, or too large"""

    def __init__(self, error: dict):
        message = str(error.get('error') or 'No answer')
        super().__init__(message)
        self.message = message
        if error.get('too_large'):
            self.outcome = 'too_large'
        elif 'timed out' in message.lower():
            self.outcome = 'timeout'
        else:
            self.outcome = 'unreachable'


class Sender:
    """Sends mispql's requests to one server with its key and settings, and keeps the last answer"""

    def __init__(self, server, max_bytes: int):
        self.server = server
        self.maxBytes = max_bytes
        self.requests = 0
        self.status = None
        self.headers = {}

    def send(self, request: mispql.Request):
        self.requests += 1
        self.status, self.headers = None, {}  # no answer yet: never report an earlier request's status
        response = mispRawRequest(self.server, request.method, request.path, data=request.body,
                                  max_bytes=self.maxBytes)
        if isinstance(response, dict):
            raise Unanswered(response)
        self.status, self.headers = response.status_code, response.headers
        return response.status_code, response.headers, response.content


def maxAnswerBytes() -> int:
    return settingModel.intValue('query_max_answer_mb') * 1024 * 1024


def rowsTTL() -> int:
    return settingModel.intValue('query_rows_ttl_minutes') * 60


def run(server, params: dict, job_id: Optional[str] = None) -> UnitResult:
    """The job unit: the statement in `params` run on `server`. Never raises for anything the server answers"""
    text = params.get('statement')
    try:
        prepared = prepare(text)
    except StatementError as e:
        return outcome('invalid', e.errors[0]['message'], {'errors': e.errors})
    summary = prepared.summary()
    sender = Sender(server, maxAnswerBytes())
    try:
        if prepared.kind in SEARCHES:
            refused = supportCheck(server, sender, summary)
            if refused is not None:
                return refused
        exchange = mispql.Exchange(prepared.plan, check_support=False)  # checked just above
        while not exchange.done:
            exchange.receive(*sender.send(exchange.request))
    except Unanswered as e:
        return outcome(e.outcome, e.message, summary, sender)
    except mispql.QueryErrors as e:
        errors = locateQueryErrors(prepared, e.errors)
        noun = 'error' if len(errors) == 1 else 'errors'
        return outcome('query_errors', f"{len(errors)} {noun} in the query: {errors[0]['message']}",
                       {**summary, 'errors': errors}, sender)
    except mispql.ClientError as e:
        return outcome(refusalOutcome(e.status), str(e), summary, sender)
    return answered(prepared, exchange.result, summary, sender, server, job_id)


def supportCheck(server, sender: Sender, summary: dict) -> Optional[UnitResult]:
    """None when the server has just shown that it runs complex queries; else the unit's outcome, nothing searched.
    What it answered is also kept as the server's capability, for the UI"""
    try:
        status, _, body = sender.send(mispql.SUPPORT_CHECK)
    except Unanswered as e:
        queryCapability.remember(server, queryCapability.capability(queryCapability.UNREACHABLE, None, e.message))
        raise
    found = queryCapability.remember(server, queryCapability.classify(status, body,
                                                                      queryCapability.snapshotRole(server)))
    if found['state'] == queryCapability.SUPPORTED:
        return None
    return outcome(found['state'], found['detail'], {**summary, 'capability': found}, sender)


def refusalOutcome(status: Optional[int]) -> str:
    if status == 404:
        return 'not_supported'  # this MISP has no such table, or no complex queries at all
    if status == 403:
        return 'no_permission'
    if status == 200 or status is None:
        return 'bad_answer'
    return 'refused'


def locateQueryErrors(prepared: Prepared, errors: list) -> List[dict]:
    """MISP's errors on the statement text, through the request paths they name; the whole statement when a path
    is unknown"""
    statement, found = prepared.statement, []
    for error in errors:
        path = str(error.get('path', ''))
        start, end = prepared.plan.locate(path) or (statement.start, statement.end)
        found.append(located(prepared.text, str(error.get('message') or 'invalid query'), start, end, path=path,
                             code=error.get('code')))
    return found


def answered(prepared: Prepared, result, summary: dict, sender: Sender, server, job_id: Optional[str]) -> UnitResult:
    if prepared.kind == 'count':
        return outcome('count', f'Count: {result}', {**summary, 'count': result}, sender)
    if prepared.kind == 'describe':
        queryCapability.rememberDescribe(server.id, prepared.table,
                                         {**queryCapability.capability(queryCapability.SUPPORTED, 200, ''), **result})
        noun = 'field' if len(result['fields']) == 1 else 'fields'
        return outcome('describe', f"{len(result['fields'])} {noun}", {**summary, 'describe': result}, sender)
    if prepared.kind == 'show_tables':
        noun = 'table' if len(result) == 1 else 'tables'
        return outcome('tables', f'{len(result)} {noun}', {**summary, 'tables': result}, sender)
    flat = [mispql.flatten(row) for row in result]
    rows, columns = shapeRows(prepared, flat)
    ttl = rowsTTL()
    if job_id is not None:
        storeRows(job_id, server.id, columns, rows, sortValues(prepared, flat), ttl)
    more = prepared.limit is not None and len(rows) >= prepared.limit
    total = matchTotal(prepared, sender)
    details = {**summary, 'rows': len(rows), 'more': more, 'total': total, 'columns': columns[:SUMMARY_COLUMNS],
               'expires_at': int(time.time()) + ttl}
    return outcome('rows', rowsText(len(rows), more, total), details, sender)


def outcome(name: str, text: str, details: dict, sender: Optional[Sender] = None) -> UnitResult:
    details = {'outcome': name, **details}
    if sender is not None:
        details['requests'] = sender.requests
    return UnitResult(name in ANSWERS, http_status=sender.status if sender else None, summary=text,
                      response=details, skipped=name in SKIPPED)


def rowsText(count: int, more: bool, total: Optional[int]) -> str:
    if count == 0:
        return 'No rows'
    noun = 'row' if count == 1 else 'rows'
    if total is not None and total > count:
        return f'{count} of {total} {noun}'
    return f'{count} {noun}, more on this server' if more else f'{count} {noun}'


def matchTotal(prepared: Prepared, sender: Sender) -> Optional[int]:
    """How many rows match on the server, when it says so: only events count their matches in `X-Result-Count`
    (on attributes, a full page reports LIMIT + 1)"""
    if mispql.TABLES[prepared.table].count != 'header':
        return None
    value = next((v for k, v in (sender.headers or {}).items() if k.lower() == 'x-result-count'), None)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


# Rows

def shapeRows(prepared: Prepared, flat: list):
    """(rows, columns) from flattened rows: only the asked columns when the statement lists them (named as asked,
    matched without regard to case, as mispql's own output does). `columns` lists every column in order of
    appearance"""
    wanted = prepared.columns
    if wanted:
        projected = []
        for row in flat:
            byName = {key.lower(): value for key, value in row.items()}
            projected.append({column: byName.get(column.lower()) for column in wanted})
        return projected, list(wanted)
    seen = {}
    for row in flat:
        for key in row:
            seen.setdefault(key, None)
    return flat, list(seen)


def sortRules(plan) -> List[tuple]:
    """[(server's sort name, descending)] of the statement's ORDER BY"""
    rules = []
    for rule in (getattr(plan, 'body', None) or {}).get('order') or []:
        name, _, direction = str(rule).rpartition(' ')
        rules.append((name, direction.lower() == 'desc'))
    return rules


def sortValues(prepared: Prepared, flat: list) -> Optional[list]:
    """Each flattened row's values for the ORDER BY, read before the columns are picked: the merged view sorts by
    them even when they are not among the asked columns"""
    rules = sortRules(prepared.plan)
    if not rules:
        return None
    values = []
    for row in flat:
        byName = {key.lower(): value for key, value in row.items()}
        values.append([byName.get(name.lower()) for name, _ in rules])
    return values


def rowsKey(job_id: str, server_id: int) -> str:
    return f'{redisModel.KEY_QUERY_ROWS}:{job_id}:{server_id}'


def storeRows(job_id: str, server_id: int, columns: list, rows: list, sort: Optional[list], ttl: int) -> None:
    data = json.dumps({'columns': columns, 'rows': rows, 'sort': sort}, separators=(',', ':'), default=str)
    packed = base64.b64encode(zlib.compress(data.encode('utf-8'), 6)).decode('ascii')
    redisModel.redisClient.set(rowsKey(job_id, server_id), packed, ex=ttl)


def loadRows(job_id: str, server_id: int) -> Optional[dict]:
    """`{"columns", "rows", "sort"}` while they are kept, else None"""
    packed = redisModel.redisClient.get(rowsKey(job_id, server_id))
    if not packed:
        return None
    try:
        return json.loads(zlib.decompress(base64.b64decode(packed)).decode('utf-8'))
    except (ValueError, zlib.error, TypeError):
        return None


def rowsKept(job_id: str, server_ids: List[int]) -> set:
    """The servers whose rows are still kept"""
    if not server_ids:
        return set()
    pipe = redisModel.redisClient.pipeline()
    for server_id in server_ids:
        pipe.exists(rowsKey(job_id, server_id))
    return {server_id for server_id, kept in zip(server_ids, pipe.execute()) if kept}


NUMBER = re.compile(r'-?\d+(\.\d+)?')


def sortKey(value, descending: bool):
    """Numbers compared as numbers, even sent as text as MISP often does; empty values last either way"""
    if value is None or value == '' or value == []:
        return (-1 if descending else 3, 0)
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (int, float)):
        return (1, value)
    if isinstance(value, str):
        stripped = value.strip()
        if NUMBER.fullmatch(stripped):
            return (1, float(stripped))
        return (2, stripped.lower())
    return (2, json.dumps(value, sort_keys=True, default=str).lower())


def merge(statement: str, servers: List[dict], job_id: str) -> dict:
    """Every server's rows in one list, each with `_server_id` and `_server_name`. `servers` are `{"id", "name"}`
    in the job's order. Sorted again by the ORDER BY, servers breaking ties; else by server"""
    try:
        prepared = prepare(statement, max_limit=10 ** 9)  # the caps were checked when it ran
    except StatementError:
        prepared = None
    rules = sortRules(prepared.plan) if prepared is not None else []
    rows, sortable, columns, expired = [], [], {}, []
    for server in servers:
        stored = loadRows(job_id, server['id'])
        if stored is None:
            expired.append(server['id'])
            continue
        for column in stored.get('columns') or []:
            columns.setdefault(column, None)
        sort = stored.get('sort') or []
        for index, row in enumerate(stored.get('rows') or []):
            rows.append({'_server_id': server['id'], '_server_name': server['name'], **row})
            sortable.append(sort[index] if index < len(sort) else [])
    if rules:
        order = list(range(len(rows)))
        for position_, (_, descending) in reversed(list(enumerate(rules))):
            order.sort(key=lambda i: sortKey(valueAt(sortable[i], position_), descending), reverse=descending)
        rows = [rows[i] for i in order]
    return {'rows': rows, 'columns': list(columns), 'expired_servers': expired,
            'default_columns': prepared.defaultColumns() if prepared is not None else None}


def valueAt(values: list, index: int):
    return values[index] if index < len(values) else None
