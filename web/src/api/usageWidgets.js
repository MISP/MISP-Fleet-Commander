import common from "./common"

// Widgets of a fleet's Usage tab: saved queries followed there. Every call returns a promise of the answer's data; a
// failure rejects with a message. `serverId`, where taken: the server of the fleet the tab is limited to (null: all)

function data(response) {
    return response.data
}

function message(error) {
    return new Promise((resolve, reject) => {
        common.handleError(error, reject)
    })
}

function get(url, params) {
    return common.getClient().get(url, { params }).then(data).catch(message)
}

// A change whose refusals are part of the answer: resolves `{ ok: true, ...data }`, or `{ ok: false, message, field }`
// on a 400, 404 or 409
function refusable(method, url, body, params) {
    return common.getClient().request({
        method,
        url,
        data: body,
        params,
        validateStatus: status => (status >= 200 && status < 300) || [400, 404, 409].includes(status),
    }).then((response) => {
        if (response.status >= 400) {
            return Object.assign({ ok: false }, response.data)
        }
        return Object.assign({ ok: true }, response.data)
    }).catch(message)
}

function base(fleetId) {
    return `/fleets/${encodeURIComponent(fleetId)}/widgets`
}

function serverParams(serverId) {
    return serverId === null || serverId === undefined ? {} : { server_id: serverId }
}

export default {
    // `{ widgets: [{ id, kind, display, position, saved_query, servers, problem }], max }`
    list(fleetId, serverId = null) {
        return get(base(fleetId), serverParams(serverId))
    },
    // `{ saved: [{ id, name, kind, schedule_minutes, expectation_text, fleet_servers, aims_at_fleet, added }],
    // fleet_servers }`
    candidates(fleetId) {
        return get(`${base(fleetId)}/candidates`)
    },
    add(fleetId, savedQueryId, display, serverId = null) {
        return refusable("post", base(fleetId), { saved_query_id: savedQueryId, display }, serverParams(serverId))
    },
    setDisplay(fleetId, widgetId, display, serverId = null) {
        return refusable("put", `${base(fleetId)}/${encodeURIComponent(widgetId)}`, { display }, serverParams(serverId))
    },
    reorder(fleetId, ids) {
        return refusable("put", `${base(fleetId)}/order`, { ids })
    },
    remove(fleetId, widgetId) {
        return refusable("delete", `${base(fleetId)}/${encodeURIComponent(widgetId)}`)
    },
    // The saved query's history on the fleet's servers (as `/queries/saved/<id>/history`), and `total`
    history(fleetId, widgetId, range, serverId = null) {
        return get(`${base(fleetId)}/${encodeURIComponent(widgetId)}/history`, { range, ...serverParams(serverId) })
    },
}
