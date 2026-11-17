// What the Organisation tab of Remote administration says about each organisation of a server: how it stands in
// the fleet, what needs attention, and why sync relies on it. Plain functions over the API's answers

// Names compared across servers: case and runs of whitespace do not matter (same rule as the backend)
export function normalisedName(name) {
    return String(name || "").trim().split(/\s+/).join(" ").toLowerCase()
}

// Names that are probably the same organisation entered twice on one server ("ACME Corp." / "acme corp")
export function duplicateKey(name) {
    return String(name || "")
        .normalize("NFKD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "")
}

export const FLEET_STATES = {
    same: { label: "Same", icon: "fa-check", tone: "ok", text: "Same UUID and name" },
    renamed: { label: "Other name", icon: "fa-exchange-alt", tone: "warning", text: "Same UUID, other name" },
    other_uuid: { label: "Other UUID", icon: "fa-not-equal", tone: "warning", text: "Same name, other UUID" },
    missing: { label: "Missing", icon: "fa-minus", tone: "muted", text: "Not on that server" },
    unknown: { label: "Unknown", icon: "fa-question", tone: "muted", text: "Its organisations could not be listed" },
}

// The fleet column of one organisation: where it is, and the worst finding. `comparison` is the fleet answer
// (null while it loads); `serverNames` maps server ID → name
export function fleetStanding(org, comparison, serverNames = {}) {
    if (!comparison) {
        return null
    }
    const entry = (comparison.organisations || {})[org.uuid] || { same: [], renamed: [], other_uuid: [] }
    const name = id => serverNames[id] || `Server #${id}`
    const rows = []
    const placed = new Set()
    entry.same.forEach((id) => {
        placed.add(id)
        rows.push({ id, name: name(id), state: "same" })
    })
    entry.renamed.forEach(([id, theirName]) => {
        placed.add(id)
        rows.push({ id, name: name(id), state: "renamed", detail: theirName })
    })
    entry.other_uuid.forEach(([id, theirUuid]) => {
        placed.add(id)
        rows.push({ id, name: name(id), state: "other_uuid", detail: theirUuid })
    })
    const missing = (comparison.compared || []).filter(server => !placed.has(server.id))
    missing.forEach(server => rows.push({ id: server.id, name: name(server.id), state: "missing" }))
    ;(comparison.unavailable || []).forEach(server => rows.push({
        id: server.id, name: name(server.id), state: "unknown", detail: server.error,
    }))
    const order = ["renamed", "other_uuid", "missing", "unknown", "same"]
    rows.sort((a, b) => order.indexOf(a.state) - order.indexOf(b.state) || a.name.localeCompare(b.name))
    const known = 1 + (comparison.compared || []).length
    const present = 1 + entry.same.length + entry.renamed.length
    const mismatches = entry.renamed.length + entry.other_uuid.length
    let tone = "partial"
    if (mismatches > 0) {
        tone = "warning"
    } else if (present === known) {
        tone = "ok"
    }
    return {
        rows,
        present,
        known,
        unknown: (comparison.unavailable || []).length,
        missingIds: missing.map(server => server.id),
        mismatches,
        tone,
        // Sorting the column: mismatches first, then the least present
        rank: (mismatches > 0 ? 0 : 1) * 10000 + present,
    }
}

// user counts by organisation ID, from the server's user list
export function usersByOrganisation(users) {
    const counts = {}
    ;(users || []).forEach((user) => {
        const id = user && user.Organisation ? Number(user.Organisation.id) : null
        if (id !== null && !Number.isNaN(id)) {
            counts[id] = (counts[id] || 0) + 1
        }
    })
    return counts
}

export function userCountOf(org, counts) {
    if (org.user_count !== null && org.user_count !== undefined) {
        return org.user_count
    }
    return counts ? counts[org.id] || 0 : null
}

// Organisations of the server sharing a duplicate key with another one: id → the other names
export function nearDuplicates(organisations) {
    const groups = {}
    organisations.forEach((org) => {
        const key = duplicateKey(org.name)
        if (key) {
            (groups[key] = groups[key] || []).push(org)
        }
    })
    const result = {}
    Object.values(groups).forEach((group) => {
        if (group.length > 1) {
            group.forEach((org) => {
                result[org.id] = group.filter(other => other.id !== org.id).map(other => other.name)
            })
        }
    })
    return result
}

// Why sync relies on each organisation, indexed once for the whole table: the remote organisation of one of the
// server's sync connections (by UUID), the organisation of the user another fleet server logs in as, and how many
// users have the sync permission (by organisation ID)
export function syncIndex({ outgoing = [], incoming = [], users = [], serverNames = {} } = {}) {
    const byUuid = {}
    const byId = {}
    const syncUsers = {}
    const add = (index, key, reason) => { (index[key] = index[key] || []).push(reason) }
    outgoing.forEach((link) => {
        const destination = link.destination || {}
        const remoteOrg = destination.RemoteOrg || {}
        if (remoteOrg.uuid) {
            add(byUuid, remoteOrg.uuid.toLowerCase(), (destination.Server && destination.Server.name) || "a remote server")
        }
    })
    const orgOfEmail = {}
    users.forEach((user) => {
        if (!user || !user.Organisation) {
            return
        }
        const orgID = Number(user.Organisation.id)
        if (user.User && user.User.email) {
            orgOfEmail[user.User.email.toLowerCase()] = orgID
        }
        const permSync = user.Role && user.Role.perm_sync
        if (permSync === true || permSync === 1 || permSync === "1") {
            syncUsers[orgID] = (syncUsers[orgID] || 0) + 1
        }
    })
    incoming.forEach((link) => {
        const connectionUser = (link.destination && link.destination.connectionUser) || {}
        const orgID = connectionUser.email ? orgOfEmail[connectionUser.email.toLowerCase()] : undefined
        if (orgID !== undefined) {
            const source = (link.source && (serverNames[link.source.id] || link.source.name)) || "Another server"
            add(byId, orgID, { code: "sync_user", text: `${source} syncs as ${connectionUser.email}` })
        }
    })
    return { byUuid, byId, syncUsers }
}

// "a", "a and b", "a, b and c"
export function listText(items) {
    return items.length <= 1 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`
}

export function syncReasonsFrom(index, org) {
    const remotes = index.byUuid[org.uuid] || []
    const reasons = remotes.length === 0 ? [] : [{
        code: "remote_org",
        text: `Represents ${listText(remotes)} in this server's sync connection${remotes.length === 1 ? "" : "s"}`,
    }]
    reasons.push(...(index.byId[org.id] || []))
    const count = index.syncUsers[org.id] || 0
    if (count > 0 && !reasons.some(reason => reason.code === "sync_user")) {
        reasons.push({ code: "sync_permission", text: `${count} user${count === 1 ? " has" : "s have"} the sync permission` })
    }
    return reasons
}

export function syncReasons(org, context) {
    return syncReasonsFrom(syncIndex(context), org)
}

// What needs attention, most important first
export function attentionFlags(org, { standing = null, userCount = null, duplicates = [] } = {}) {
    const flags = []
    if (standing) {
        standing.rows.filter(row => row.state === "renamed").forEach(row => flags.push({
            code: "renamed", tone: "warning", text: `Named “${row.detail}” on ${row.name}`,
        }))
        standing.rows.filter(row => row.state === "other_uuid").forEach(row => flags.push({
            code: "other_uuid", tone: "warning", text: `Another UUID on ${row.name}`,
        }))
    }
    if (org.local && userCount === 0) {
        flags.push({ code: "no_users", tone: "info", text: "Local, without users" })
    }
    duplicates.forEach(name => flags.push({ code: "duplicate", tone: "info", text: `Looks like “${name}”` }))
    return flags
}

export function matchesSearch(org, query) {
    const needle = String(query || "").trim().toLowerCase()
    if (needle === "") {
        return true
    }
    return [org.name, org.uuid, org.type, org.sector, org.nationality, org.description]
        .some(value => String(value || "").toLowerCase().includes(needle))
}

// The baseline rule matching an organisation: name always, the other fields as chosen
export function baselineRule(org, { checkType, checkNationality, checkSector, checkLocal } = {}) {
    const expected = { name: org.name }
    if (checkType && org.type) {
        expected.type = org.type
    }
    if (checkNationality && org.nationality) {
        expected.nationality = org.nationality
    }
    if (checkSector && org.sector) {
        expected.sector = org.sector
    }
    if (checkLocal) {
        expected.local = !!org.local
    }
    return { type: "organisation", key: org.uuid, expected }
}

// The fields of the edit form that changed, as the API takes them
export function changedFields(org, form) {
    const changes = {}
    ;["name", "uuid", "type", "nationality", "sector", "description", "contacts"].forEach((field) => {
        const value = String(form[field] || "").trim()
        const before = String(org[field] || "").trim()
        if (field === "uuid" ? value.toLowerCase() !== before.toLowerCase() : value !== before) {
            changes[field] = value
        }
    })
    if (!!form.local !== !!org.local) {
        changes.local = !!form.local
    }
    const domains = domainLines(form.restricted_to_domain)
    if (domains.join("\n") !== (org.restricted_to_domain || []).join("\n")) {
        changes.restricted_to_domain = domains
    }
    return changes
}

export function domainLines(text) {
    return String(text || "").split(/[\n,]/).map(domain => domain.trim()).filter(domain => domain !== "")
}

export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
