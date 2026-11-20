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

export function targetText(saved) {
    if (saved.fleet_id !== null && saved.fleet_id !== undefined) {
        return saved.fleet_name ? `Fleet ${saved.fleet_name}` : "A fleet"
    }
    if (!saved.server_ids) {
        return "No servers"
    }
    const count = saved.server_count
    return `${count} server${count === 1 ? "" : "s"}`
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

// The fleet whose servers are exactly the selection, if there is one: such a selection can be saved as the fleet
export function wholeFleet(selected, fleets) {
    if (!selected || selected.length === 0) {
        return null
    }
    const chosen = new Set(selected)
    return (fleets || []).find(fleet => fleet.servers.length === chosen.size && fleet.servers.every(server => chosen.has(server.id))) || null
}

// The servers a saved query runs on, among those listed in `fleets`
export function savedSelection(saved, fleets) {
    if (saved.fleet_id !== null && saved.fleet_id !== undefined) {
        const fleet = (fleets || []).find(entry => entry.id === saved.fleet_id)
        return fleet ? fleet.servers.map(server => server.id) : []
    }
    const known = new Set((fleets || []).flatMap(fleet => fleet.servers.map(server => server.id)))
    return (saved.server_ids || []).filter(id => known.has(id))
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

// What saving the form asks of the API. `target` is "fleet" or "servers"; DESCRIBE and SHOW TABLES take neither a
// schedule nor an expectation
export function savedBody(form, { kind, statement, selected, fleet }) {
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
        if (form.target === "fleet" && fleet) {
            body.fleet_id = fleet.id
        } else {
            body.server_ids = selected.slice()
        }
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
