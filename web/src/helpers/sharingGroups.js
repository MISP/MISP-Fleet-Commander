// What the Sharing groups tab of Remote administration says about each sharing group of a server: how it stands in
// the fleet, and what its forms send. Plain functions over the API's answers
import { duplicateKey, namesText, normalisedName } from "@/helpers/organisations"

export { namesText }

// The MISP instance itself among a group's servers
export const LOCAL_INSTANCE = 0

export const FLEET_STATES = {
    same: { label: "Same", icon: "fa-check", text: "Same name, flags and members" },
    differs: { label: "Differs", icon: "fa-exchange-alt", text: "Same UUID, but not the same group" },
    other_uuid: { label: "Other UUID", icon: "fa-not-equal", text: "Same name, other UUID" },
    missing: { label: "Missing", icon: "fa-minus", text: "Not on that server" },
    unknown: { label: "Unknown", icon: "fa-question", text: "Its sharing groups could not be listed" },
}

function plural(count, noun, nouns = `${noun}s`) {
    return `${count} ${count === 1 ? noun : nouns}`
}

// What differs on another server, in words. `entry`: a `differs` entry of the fleet answer (their values)
export function differenceTexts(entry, group) {
    const texts = []
    if (entry.name !== undefined) {
        texts.push(`named “${entry.name}”`)
    }
    if (entry.active !== undefined) {
        texts.push(entry.active ? "active there" : "inactive there")
    }
    if (entry.roaming !== undefined) {
        texts.push(entry.roaming ? "roaming there" : "not roaming there")
    }
    const ours = {}
    group.members.forEach((member) => { ours[member.uuid] = member.name })
    const missing = entry.members_missing || []
    if (missing.length > 0) {
        texts.push(`lacks ${plural(missing.length, "member")}: ${namesText(missing.map(uuid => ours[uuid] || uuid))}`)
    }
    const extra = entry.members_extra || []
    if (extra.length > 0) {
        texts.push(`also has ${namesText(extra.map(([, name]) => name))}`)
    }
    return texts
}

// The Fleet column of one group: where it is, and the worst finding. `comparison` is the fleet answer (null while
// it loads); `serverNames` maps server ID → name
export function fleetStanding(group, comparison, serverNames = {}) {
    if (!comparison) {
        return null
    }
    const entry = (comparison.sharing_groups || {})[group.uuid] || { same: [], differs: [], other_uuid: [] }
    const name = id => serverNames[id] || `Server #${id}`
    const rows = []
    const placed = new Set()
    entry.same.forEach((id) => {
        placed.add(id)
        rows.push({ id, name: name(id), state: "same", details: [] })
    })
    entry.differs.forEach((difference) => {
        placed.add(difference.server_id)
        rows.push({
            id: difference.server_id,
            name: name(difference.server_id),
            state: "differs",
            details: differenceTexts(difference, group),
            lacking: (difference.members_missing || []).length,
        })
    })
    entry.other_uuid.forEach(([id, theirUuid]) => {
        placed.add(id)
        rows.push({ id, name: name(id), state: "other_uuid", details: [], detail: theirUuid })
    })
    const missing = (comparison.compared || []).filter(server => !placed.has(server.id))
    missing.forEach(server => rows.push({ id: server.id, name: name(server.id), state: "missing", details: [] }))
    ;(comparison.unavailable || []).forEach(server => rows.push({
        id: server.id, name: name(server.id), state: "unknown", details: [], detail: server.error,
    }))
    const order = ["differs", "other_uuid", "missing", "unknown", "same"]
    rows.sort((a, b) => order.indexOf(a.state) - order.indexOf(b.state) || a.name.localeCompare(b.name))
    const known = 1 + (comparison.compared || []).length
    const present = 1 + entry.same.length + entry.differs.length
    const mismatches = entry.differs.length + entry.other_uuid.length
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
        // Servers where "Create or complete" would do something: missing it, lacking members, or not listed
        copyIds: rows.filter(row => row.state === "missing" || row.state === "unknown" || row.lacking > 0).map(row => row.id),
        mismatches,
        tone,
        // Sorting the column: mismatches first, then the least present
        rank: (mismatches > 0 ? 0 : 1) * 10000 + present,
    }
}

// "Roaming", "Local instance", "Local instance + 2 servers"…
export function serversSummary(group) {
    if (group.roaming) {
        return "Roaming"
    }
    const local = group.servers.some(server => server.server_id === LOCAL_INSTANCE)
    const remote = group.servers.filter(server => server.server_id !== LOCAL_INSTANCE).length
    if (remote === 0) {
        return local ? "Local instance" : "No server"
    }
    const servers = plural(remote, "server")
    return local ? `Local instance + ${servers}` : servers
}

export function extendCount(group) {
    return group.members.filter(member => member.extend).length
}

export function matchesSearch(group, query) {
    const needle = String(query || "").trim().toLowerCase()
    if (needle === "") {
        return true
    }
    const values = [group.name, group.uuid, group.description, group.releasability, group.creator && group.creator.name]
        .concat(group.members.map(member => member.name))
    return values.some(value => String(value || "").toLowerCase().includes(needle))
}

export function nameTaken(groups, name, exceptUuid = null) {
    const wanted = normalisedName(name)
    if (wanted === "") {
        return null
    }
    return groups.find(group => normalisedName(group.name) === wanted && group.uuid !== exceptUuid) || null
}

// The baseline rule matching a group: name always (and roaming, used when a fix creates it), the rest as chosen.
// Members are checked as "at least these"
export function baselineRule(group, { checkMembers = true, checkReleasability = true, checkDescription = true, checkActive = true } = {}) {
    const expected = { name: group.name, roaming: !!group.roaming }
    if (checkMembers) {
        expected.members = group.members.map(member => ({ uuid: member.uuid, name: member.name, extend: !!member.extend }))
    }
    if (checkReleasability && group.releasability) {
        expected.releasability = group.releasability
    }
    if (checkDescription && group.description) {
        expected.description = group.description
    }
    if (checkActive) {
        expected.active = !!group.active
    }
    return { type: "sharing_group", key: group.uuid, expected }
}

// The form's state from a group (edit) or empty (add). `creator`: the organisation of the server's API user, a
// member from the start of a new group (MISP's own form does the same)
export function formFrom(group, creator = null) {
    if (group) {
        return {
            name: group.name,
            description: group.description,
            releasability: group.releasability,
            active: group.active,
            roaming: group.roaming,
            members: group.members.map(member => ({ uuid: member.uuid, name: member.name, extend: member.extend })),
            servers: group.servers.map(server => ({ server_id: server.server_id, name: server.name, all_orgs: server.all_orgs })),
        }
    }
    return {
        name: "",
        description: "",
        releasability: "",
        active: true,
        roaming: false,
        members: creator && creator.uuid ? [{ uuid: creator.uuid.toLowerCase(), name: creator.name, extend: true }] : [],
        servers: [{ server_id: LOCAL_INSTANCE, name: "Local instance", all_orgs: false }],
    }
}

function memberKey(members) {
    return members.map(member => `${member.uuid}:${member.extend ? 1 : 0}`).sort().join("|")
}

function serverKey(servers) {
    return servers.map(server => `${server.server_id}:${server.all_orgs ? 1 : 0}`).sort().join("|")
}

// A server of the form as the API takes it; its name only names it in what MISP did
function serverRequest(server) {
    return { server_id: server.server_id, all_orgs: !!server.all_orgs, name: server.name }
}

// What the add request sends
export function addPayload(form) {
    const fields = { name: form.name.trim(), active: !!form.active, roaming: !!form.roaming }
    ;["description", "releasability"].forEach((field) => {
        const value = String(form[field] || "").trim()
        if (value !== "") {
            fields[field] = value
        }
    })
    fields.members = form.members.map(member => ({ uuid: member.uuid, name: member.name, extend: !!member.extend }))
    if (!form.roaming) {
        fields.servers = form.servers.map(serverRequest)
    }
    return fields
}

// What the edit request sends: the attributes that changed, and the whole member / server lists when they changed
// (servers only when the group does not roam: MISP ignores them otherwise)
export function editPayload(group, form) {
    const changes = {}
    ;["name", "description", "releasability"].forEach((field) => {
        const value = String(form[field] || "").trim()
        if (value !== String(group[field] || "").trim()) {
            changes[field] = value
        }
    })
    ;["active", "roaming"].forEach((field) => {
        if (!!form[field] !== !!group[field]) {
            changes[field] = !!form[field]
        }
    })
    if (memberKey(form.members) !== memberKey(group.members)) {
        changes.members = form.members.map(member => ({ uuid: member.uuid, name: member.name, extend: !!member.extend }))
    }
    if (!form.roaming && serverKey(form.servers) !== serverKey(group.servers)) {
        changes.servers = form.servers.map(serverRequest)
    }
    return changes
}

// How many separate changes an edit makes, for the form's footer
export function changeCount(group, changes) {
    let count = Object.keys(changes).filter(field => field !== "members" && field !== "servers").length
    if (changes.members) {
        const before = new Map(group.members.map(member => [member.uuid, member.extend]))
        const after = new Map(changes.members.map(member => [member.uuid, member.extend]))
        after.forEach((extend, uuid) => { count += before.has(uuid) && before.get(uuid) === extend ? 0 : 1 })
        before.forEach((extend, uuid) => { count += after.has(uuid) ? 0 : 1 })
    }
    if (changes.servers) {
        const before = new Map(group.servers.map(server => [server.server_id, server.all_orgs]))
        const after = new Map(changes.servers.map(server => [server.server_id, server.all_orgs]))
        after.forEach((allOrgs, id) => { count += before.has(id) && before.get(id) === allOrgs ? 0 : 1 })
        before.forEach((allOrgs, id) => { count += after.has(id) ? 0 : 1 })
    }
    return count
}

// MISP renames a new group whose name is taken: "name_<random number>". Copies made by other tools read
// "name - [2]". The names a group may have had before such renames, most stripped last ("X_2 - [3]" → "X_2", "X")
const RENAME_SUFFIX = /(?:\s*-\s*\[\d+\]|_\d+)\s*$/

export function namesBeforeRenames(name) {
    const names = []
    let current = String(name || "").trim()
    let stripped = current.replace(RENAME_SUFFIX, "").trim()
    while (stripped !== "" && stripped !== current) {
        names.push(stripped)
        current = stripped
        stripped = current.replace(RENAME_SUFFIX, "").trim()
    }
    return names
}

// Groups of the server that are probably one group twice: uuid → the other names. Same name once case, accents and
// punctuation are ignored, or a renamed copy of a group that is still there ("X_4821" next to "X"). Two renamed
// copies go together only through the group they copy: "ORG_6" and "ORG_7" alone are two groups
export function nearDuplicateGroups(groups) {
    const keys = new Set(groups.map(group => duplicateKey(group.name)).filter(key => key !== ""))
    const clusters = {}
    groups.forEach((group) => {
        let key = duplicateKey(group.name)
        namesBeforeRenames(group.name).forEach((name) => {
            const before = duplicateKey(name)
            if (keys.has(before)) {
                key = before
            }
        })
        if (key) {
            (clusters[key] = clusters[key] || []).push(group)
        }
    })
    const result = {}
    Object.values(clusters).forEach((same) => {
        if (same.length > 1) {
            same.forEach((group) => {
                result[group.uuid] = same.filter(other => other.uuid !== group.uuid).map(other => other.name)
            })
        }
    })
    return result
}

// What deserves a look in a group, most important first: [{code, tone, text}]
export function attentionFlags(group, { standing = null, duplicates = [] } = {}) {
    const flags = []
    if (standing) {
        standing.rows.filter(row => row.state === "other_uuid").forEach(row => flags.push({
            code: "other_uuid", tone: "warning", text: `Another UUID on ${row.name}`,
        }))
        standing.rows.filter(row => row.state === "differs").forEach(row => flags.push({
            code: "differs", tone: "warning", text: `On ${row.name}: ${row.details.join("; ")}`,
        }))
    }
    if (duplicates.length > 0) {
        flags.push({ code: "duplicate", tone: "info", text: `Looks like ${namesText(duplicates.map(name => `“${name}”`), 2)}` })
    }
    const servers = group.servers || []
    const members = group.members || []
    const local = servers.find(server => server.server_id === LOCAL_INSTANCE)
    if (members.length === 0 && !servers.some(server => server.all_orgs)) {
        flags.push({ code: "no_members", tone: "info", text: "No member" })
    }
    // Without any member, "no member" says it all
    if (group.creator && members.length > 0 && !(local && local.all_orgs)) {
        const creator = String(group.creator.uuid || "").toLowerCase()
        if (!members.some(member => String(member.uuid || "").toLowerCase() === creator)) {
            flags.push({ code: "creator_not_member", tone: "info", text: `Its creator, ${group.creator.name}, is not a member` })
        }
    }
    if (!group.active && (group.roaming || servers.length === 0 || servers.some(server => server.server_id !== LOCAL_INSTANCE))) {
        flags.push({ code: "inactive_syncs", tone: "info", text: "Inactive, but still syncs" })
    }
    return flags
}
