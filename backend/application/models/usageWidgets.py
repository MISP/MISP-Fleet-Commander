"""Widgets of a fleet's Usage tab: the saved queries its owner follows there, each drawn as the fleet total or server
by server, in the order they chose.

A widget draws only the fleet's servers among those its saved query runs on now, or only one of them when the tab is
limited to that server (`server_id`). It stays when its saved query changes so that nothing is left to draw (a
statement that answers no number, no server of the fleet in its target): it then says why. It goes with its fleet or
its saved query (listeners in DBModels).
"""
import time
from typing import List, Optional

from application.DBModels import Fleet, SavedQuery, Server, USAGE_WIDGET_DISPLAYS, UsageWidget, db
from application.models import fleetMetrics, metricSeries, savedQueries, savedQueryHistory
import application.models.fleets as fleetModel
from application.models.userJobs import JobError

MAX_WIDGETS = 20
KIND_SAVED_QUERY = 'saved_query'
# Why a widget has nothing to draw
NO_NUMBER, NO_SERVER = 'no_number', 'no_server'


class WidgetError(JobError):
    def __init__(self, message: str, status: int = 400, field: Optional[str] = None):
        super().__init__(message, status)
        self.field = field


def ownedFleet(user, fleetId: int) -> Fleet:
    fleet = fleetModel.getForUser(user, fleetId)
    if fleet is None:
        raise WidgetError('Unknown fleet', 404)
    return fleet


def fleetWidgets(fleet: Fleet) -> List[UsageWidget]:
    return UsageWidget.query.filter(UsageWidget.fleet_id == fleet.id) \
        .order_by(UsageWidget.position, UsageWidget.id).all()


def ownedWidget(fleet: Fleet, widgetId) -> UsageWidget:
    if isinstance(widgetId, bool) or not isinstance(widgetId, int):
        raise WidgetError('Unknown widget', 404)
    widget = UsageWidget.query.filter(UsageWidget.fleet_id == fleet.id, UsageWidget.id == widgetId).first()
    if widget is None:
        raise WidgetError('Unknown widget', 404)
    return widget


def pickedServer(fleet: Fleet, value) -> Optional[int]:
    """The ID of the one server of the fleet the tab is limited to (`server_id`), or None for all of them"""
    try:
        return fleetMetrics.parseServer(fleet, None if value is None else str(value))
    except metricSeries.SeriesRequestError as e:
        raise WidgetError(str(e), field='server_id')


def fleetServers(saved: SavedQuery, fleet: Fleet, serverId: Optional[int] = None) -> List[Server]:
    """The fleet's servers among those the saved query runs on now, in the saved query's order; only `serverId` if
    given"""
    return [server for server in savedQueries.targetServers(saved)
            if server.fleet_id == fleet.id and (serverId is None or server.id == serverId)]


def checkedDisplay(value) -> str:
    if value not in USAGE_WIDGET_DISPLAYS:
        raise WidgetError(f"Choose how to show it: {' or '.join(USAGE_WIDGET_DISPLAYS)}", field='display')
    return value


# Reading

def serialize(widget: UsageWidget, fleet: Fleet, serverId: Optional[int] = None) -> dict:
    saved = db.session.get(SavedQuery, widget.saved_query_id) if widget.saved_query_id else None
    data = {'id': widget.id, 'kind': widget.kind, 'display': widget.display, 'position': widget.position,
            'saved_query': None, 'servers': [], 'problem': None}
    if saved is None:
        return data
    kind = savedQueries.statementKind(saved.statement)
    servers = fleetServers(saved, fleet, serverId)
    data['saved_query'] = {
        'id': saved.id,
        'name': saved.name,
        'kind': kind,
        'schedule_minutes': saved.schedule_minutes,
        'expectation': ({'comparator': saved.comparator, 'value': saved.expected}
                        if saved.comparator is not None else None),
        'expectation_text': savedQueries.expectationText(kind, saved.comparator, saved.expected),
        'severity': saved.severity,
        'server_count': len(savedQueries.targetServers(saved)),
    }
    data['servers'] = savedQueries.serverStates(saved, servers)
    if kind not in savedQueries.CHECKED_KINDS:
        data['problem'] = NO_NUMBER
    elif not servers:
        data['problem'] = NO_SERVER
    return data


def listFor(user, fleetId: int, serverId=None) -> dict:
    """The fleet's widgets; with `serverId`, as drawn for that server of the fleet alone"""
    fleet = ownedFleet(user, fleetId)
    serverId = pickedServer(fleet, serverId)
    return {'widgets': [serialize(widget, fleet, serverId) for widget in fleetWidgets(fleet)], 'max': MAX_WIDGETS}


def candidates(user, fleetId: int) -> dict:
    """The user's saved queries that answer a number and run on at least one of the fleet's servers"""
    fleet = ownedFleet(user, fleetId)
    added = {widget.saved_query_id for widget in fleetWidgets(fleet)}
    found = []
    for saved in savedQueries.ownedQuery(user).order_by(db.func.lower(SavedQuery.name)).all():
        kind = savedQueries.statementKind(saved.statement)
        if kind not in savedQueries.CHECKED_KINDS:
            continue
        servers = savedQueries.targetServers(saved)
        inFleet = sum(1 for server in servers if server.fleet_id == fleet.id)
        if inFleet == 0:
            continue
        found.append({
            'id': saved.id,
            'name': saved.name,
            'description': saved.description,
            'kind': kind,
            'schedule_minutes': saved.schedule_minutes,
            'expectation_text': savedQueries.expectationText(kind, saved.comparator, saved.expected),
            'fleet_servers': inFleet,
            'server_count': len(servers),
            'aims_at_fleet': fleet.id in savedQueries.idList(saved.fleet_ids),
            'added': saved.id in added,
        })
    return {'saved': found, 'fleet_servers': Server.query.filter(Server.fleet_id == fleet.id).count()}


# Changing

def add(user, fleetId: int, body: dict, serverId=None) -> dict:
    """`serverId`: the server the tab is limited to, for the answer"""
    fleet = ownedFleet(user, fleetId)
    serverId = pickedServer(fleet, serverId)
    savedId = body.get('saved_query_id')
    try:
        saved = savedQueries.ownedSaved(user, savedId)
    except savedQueries.SavedQueryError:
        raise WidgetError('Unknown saved query', 404, field='saved_query_id')
    display = checkedDisplay(body.get('display', 'total'))
    if savedQueries.statementKind(saved.statement) not in savedQueries.CHECKED_KINDS:
        raise WidgetError('Only a SELECT or a COUNT answers a number to follow over time', field='saved_query_id')
    if not fleetServers(saved, fleet):
        raise WidgetError('It runs on none of this fleet\'s servers', field='saved_query_id')
    widgets = fleetWidgets(fleet)
    if any(widget.saved_query_id == saved.id for widget in widgets):
        raise WidgetError('It is already on this fleet\'s Usage tab', 409, field='saved_query_id')
    if len(widgets) >= MAX_WIDGETS:
        raise WidgetError(f'A fleet holds at most {MAX_WIDGETS} widgets: remove one first')
    widget = UsageWidget(fleet_id=fleet.id, kind=KIND_SAVED_QUERY, saved_query_id=saved.id, display=display,
                         position=max((item.position for item in widgets), default=-1) + 1,
                         created=int(time.time()))
    db.session.add(widget)
    db.session.commit()
    return serialize(widget, fleet, serverId)


def update(user, fleetId: int, widgetId: int, body: dict, serverId=None) -> dict:
    """`serverId`: the server the tab is limited to, for the answer"""
    fleet = ownedFleet(user, fleetId)
    serverId = pickedServer(fleet, serverId)
    widget = ownedWidget(fleet, widgetId)
    if 'display' in body:
        widget.display = checkedDisplay(body['display'])
    db.session.commit()
    return serialize(widget, fleet, serverId)


def reorder(user, fleetId: int, body: dict) -> dict:
    """`ids`: every widget of the fleet, once, in their new order"""
    fleet = ownedFleet(user, fleetId)
    ids = body.get('ids')
    widgets = {widget.id: widget for widget in fleetWidgets(fleet)}
    if (not isinstance(ids, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in ids)
            or len(ids) != len(set(ids)) or set(ids) != set(widgets)):
        raise WidgetError('Give every widget of the fleet once, in their new order', field='ids')
    for position, widgetId in enumerate(ids):
        widgets[widgetId].position = position
    db.session.commit()
    return listFor(user, fleetId)


def remove(user, fleetId: int, widgetId: int) -> None:
    widget = ownedWidget(ownedFleet(user, fleetId), widgetId)
    db.session.delete(widget)
    db.session.commit()


def history(user, fleetId: int, widgetId: int, rangeName: Optional[str], now: Optional[int] = None,
            serverId=None) -> dict:
    """The saved query's history on the fleet's servers (or only `serverId`), and their total: both displays from one
    answer"""
    fleet = ownedFleet(user, fleetId)
    serverId = pickedServer(fleet, serverId)
    widget = ownedWidget(fleet, widgetId)
    saved = db.session.get(SavedQuery, widget.saved_query_id) if widget.saved_query_id else None
    if saved is None:
        raise WidgetError('Its saved query was deleted', 404)
    servers = fleetServers(saved, fleet, serverId)
    try:
        answer = savedQueries.historyFor(user, saved.id, rangeName, now, servers=servers)
    except savedQueries.SavedQueryError as e:
        raise WidgetError(e.message, e.status, field=getattr(e, 'field', None))
    answer['widget_id'] = widget.id
    answer['total'] = savedQueryHistory.total(saved.id, servers, answer['range'], now=answer['to'])
    answer['total']['carried'] = carriedAnswers(saved, servers)
    return answer


def carriedAnswers(saved: SavedQuery, servers: List[Server]) -> List[dict]:
    """The servers whose last run gave no number (unreachable, a query error…) while an earlier answer of theirs is
    still in the total, as the total carries each server's last answer forward: oldest first"""
    silent = [entry['server_id'] for entry in savedQueries.serverStates(saved, servers)
              if entry['state'] == savedQueries.UNCHECKED]
    names = {server.id: server.name for server in servers}
    carried = [{'server_id': serverId, 'server_name': names[serverId], 'ts': row.ts, 'value': row.value,
                'more': bool(row.more)}
               for serverId, row in savedQueryHistory.lastAnswers(saved.id, silent).items()]
    return sorted(carried, key=lambda entry: (entry['ts'], entry['server_name']))
