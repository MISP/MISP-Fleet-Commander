// Saved queries: what they hold, and how each server last answered, in words and tones. The server decides whether
// an answer meets the expectation; these only say it

// A server's state for a saved query. Not as expected takes the saved query's severity
export const STATE_META = {
    unmet: { label: "Not as expected", short: "not as expected", icon: "fa-circle-xmark" },
    unchecked: { label: "Could not run", short: "could not run", tone: "info", icon: "fa-circle-exclamation" },
    met: { label: "As expected", short: "as expected", tone: "ok", icon: "fa-circle-check" },
    answered: { label: "Answered", short: "answered", tone: "muted", icon: "fa-circle-check" },
    not_run: { label: "Not run yet", short: "not run yet", tone: "muted", icon: "fa-circle-minus" },
}
export const STATE_ORDER = ["unmet", "unchecked", "met", "answered", "not_run"]

export const SEVERITY_TONES = { critical: "critical", warning: "warning", info: "info" }

// Statements whose answer is a number, and that may run on a schedule with an expectation
export const CHECKED_KINDS = ["count", "select"]

export function stateMeta(state, severity) {
    const meta = STATE_META[state] || { label: state, short: state, tone: "muted", icon: "fa-circle" }
    return Object.assign({}, meta, { tone: meta.tone || SEVERITY_TONES[severity] || "warning" })
}

// A saved query's servers, worst state first then by name, each with its state's words and tone in `meta`
export function serversWorstFirst(servers, severity) {
    return (servers || []).map(entry => Object.assign({ meta: stateMeta(entry.state, severity) }, entry))
        .sort((a, b) => (STATE_ORDER.indexOf(a.state) - STATE_ORDER.indexOf(b.state)) || a.server_name.localeCompare(b.server_name))
}

// The states of a saved query's servers worth showing, worst first: `[{ state, count, text, tone, icon }]`
export function overviewParts(overview, severity) {
    return STATE_ORDER
        .filter(state => overview && overview[state] > 0)
        .map((state) => {
            const meta = stateMeta(state, severity)
            return { state, count: overview[state], text: `${overview[state]} ${meta.short}`, tone: meta.tone, icon: meta.icon }
        })
}

export function scheduleLabel(minutes, schedules) {
    if (minutes === null || minutes === undefined) {
        return "By hand"
    }
    const found = (schedules || []).find(entry => entry.minutes === minutes)
    return found ? found.label : `Every ${minutes} minutes`
}

const FLEETS_NAMED = 3

// Where a saved query runs, short: "Fleet Dev", "Fleets Dev, Lab", "4 fleets", "Fleet Dev + 2 servers", "3 servers"
export function targetText(saved) {
    const fleets = saved.fleets || []
    const others = fleets.length > 0 ? (saved.other_server_count || 0) : saved.server_count
    const parts = []
    if (fleets.length === 1) {
        parts.push(`Fleet ${fleets[0].name}`)
    } else if (fleets.length > 1) {
        parts.push(fleets.length > FLEETS_NAMED ? `${fleets.length} fleets` : `Fleets ${fleets.map(fleet => fleet.name).join(", ")}`)
    }
    if (others > 0 || fleets.length === 0) {
        parts.push(others > 0 ? `${others} server${others === 1 ? "" : "s"}` : "No servers")
    }
    return parts.join(" + ")
}

// What a server answered, as short as the table cell holding it allows
export function answerText(result) {
    if (!result) {
        return ""
    }
    if (result.outcome === "count") {
        return Number(result.value).toLocaleString("en-US")
    }
    if (result.outcome === "rows") {
        if (result.value === 0) {
            return "No rows"
        }
        const rows = `${Number(result.value).toLocaleString("en-US")} row${result.value === 1 ? "" : "s"}`
        return result.more ? `${rows} or more` : rows
    }
    return sentence(result.message || result.outcome)
}

// Messages from mispql start in lower case ("this MISP does not support…"): shown alone, they start a sentence
export function sentence(text) {
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

// "exactly 0", "no rows"… as the server words it; `comparators` and `rows` come from the language's `saved`
export function expectationText(kind, expectation, options) {
    if (!expectation || !expectation.comparator) {
        return ""
    }
    if (kind === "select") {
        const found = ((options && options.row_expectations) || [])
            .find(entry => entry.comparator === expectation.comparator && entry.value === expectation.value)
        if (found) {
            return found.label
        }
    }
    const comparator = ((options && options.comparators) || []).find(entry => entry.name === expectation.comparator)
    return `${comparator ? comparator.words : expectation.comparator} ${expectation.value}`
}

// Said when a run by hand starts: "“No tlp:red” is running on 3 servers. Open the run"
export function runStartedText(saved, job) {
    const total = (job && job.total) || 0
    return `“${saved.name}” is running on ${total} server${total === 1 ? "" : "s"}. Open the run.`
}

// The fleets whose servers are all in the selection: a saved query can follow them, and run on the servers they
// will have
export function wholeFleets(selected, fleets) {
    const chosen = new Set(selected || [])
    return (fleets || []).filter(fleet => fleet.servers.length > 0 && fleet.servers.every(server => chosen.has(server.id)))
}

// The selected servers that the followed fleets (IDs) do not hold: those a saved query lists on their own
export function otherServers(selected, followedIds, fleets) {
    const followed = new Set(followedIds || [])
    const covered = new Set((fleets || []).filter(fleet => followed.has(fleet.id)).flatMap(fleet => fleet.servers.map(server => server.id)))
    return (selected || []).filter(id => !covered.has(id))
}

// The servers a saved query runs on, among those listed in `fleets`: its fleets' then the ones it lists, each once
export function savedSelection(saved, fleets) {
    const followed = new Set(saved.fleet_ids || [])
    const selection = (fleets || []).filter(fleet => followed.has(fleet.id)).flatMap(fleet => fleet.servers.map(server => server.id))
    const known = new Set((fleets || []).flatMap(fleet => fleet.servers.map(server => server.id)))
    ;(saved.server_ids || []).forEach((id) => {
        if (known.has(id) && !selection.includes(id)) {
            selection.push(id)
        }
    })
    return selection
}

// The form's expectation as the API takes it, or null. `count`: `{ comparator, value }` (a comparator of "" is
// none); `select`: `rows` is "none", "no_rows" or "some_rows"
export function formExpectation(kind, form) {
    if (kind === "count") {
        if (!form.comparator) {
            return null
        }
        const value = Number(form.value)
        return { comparator: form.comparator, value: Number.isInteger(value) ? value : form.value }
    }
    if (kind === "select") {
        if (form.rows === "no_rows") {
            return { comparator: "eq", value: 0 }
        }
        if (form.rows === "some_rows") {
            return { comparator: "gt", value: 0 }
        }
    }
    return null
}

// A saved query's expectation as the form holds it
export function expectationForm(kind, expectation) {
    const form = { comparator: "", value: 0, rows: "none" }
    if (!expectation) {
        return form
    }
    if (kind === "select") {
        form.rows = expectation.comparator === "gt" ? "some_rows" : "no_rows"
        return form
    }
    return Object.assign(form, { comparator: expectation.comparator, value: expectation.value })
}

// What saving the form asks of the API. `form.follow`: the IDs of the fleets to follow, among `fleets` (those whose
// servers are all selected); the other selected servers are listed on their own. DESCRIBE and SHOW TABLES take
// neither a schedule nor an expectation
export function savedBody(form, { kind, statement, selected, fleets }) {
    const checked = CHECKED_KINDS.includes(kind)
    const body = {
        name: form.name,
        description: form.description,
        schedule_minutes: checked ? form.schedule : null,
        expectation: checked ? formExpectation(kind, form) : null,
        severity: form.severity,
    }
    if (statement !== undefined && statement !== null) {
        body.statement = statement
    }
    if (selected) {
        const whole = new Set((fleets || []).map(fleet => fleet.id))
        body.fleet_ids = (form.follow || []).filter(id => whole.has(id))
        body.server_ids = otherServers(selected, body.fleet_ids, fleets)
    }
    return body
}

// One sentence on what the saved query will do, for the form
export function consequenceText({ kind, schedule, expectation, severity, schedules, options }) {
    if (!CHECKED_KINDS.includes(kind)) {
        return "Kept to run again by hand: DESCRIBE and SHOW TABLES don't run on a schedule."
    }
    const when = schedule ? scheduleLabel(schedule, schedules).toLowerCase() : null
    if (!expectation) {
        return when ? `Runs ${when}; each server's answer is kept, without raising issues.` : "Kept to run again by hand."
    }
    const expected = expectationText(kind, expectation, options)
    if (!when) {
        return `Run by hand, each server shows whether it answered ${expected}. Only scheduled runs raise issues.`
    }
    let offender = `A server whose count is not ${expected}`
    if (kind === "select") {
        offender = expectation.comparator === "eq" ? "A server that finds rows" : "A server that finds none"
    }
    const as = severity === "info" ? "info" : `a ${severity} issue`
    return `Runs ${when}. ${offender} shows on Needs attention as ${as}; one that can't run it, as info.`
}
