// Wording shared by the baseline views

export const TYPE_META = {
    setting: { label: "Setting", icon: "fas fa-sliders", keyLabel: "Setting" },
    taxonomy_enabled: { label: "Taxonomy", icon: "fas fa-tags", keyLabel: "Taxonomy" },
    galaxy_enabled: { label: "Galaxy", icon: "fas fa-meteor", keyLabel: "Galaxy" },
    object_template_active: { label: "Object template", icon: "fas fa-cubes", keyLabel: "Object template" },
    version_min: { label: "MISP version", icon: "fas fa-code-branch", keyLabel: null },
    organisation: { label: "Organisation", icon: "fas fa-building", keyLabel: "Organisation" },
    sharing_group: { label: "Sharing group", icon: "fas fa-users-rectangle", keyLabel: "Sharing group" },
    custom_galaxy: { label: "Custom galaxy", icon: "fas fa-wand-magic-sparkles", keyLabel: "Custom galaxy" },
}

// Enabled or disabled
export const CONTENT_TYPES = ["taxonomy_enabled", "galaxy_enabled", "object_template_active"]
// Present and as described: the expected value is an object taken from a reference server
export const ITEM_TYPES = ["organisation", "sharing_group", "custom_galaxy"]
// Listed from MISP by a content check
export const LISTED_TYPES = CONTENT_TYPES.concat(ITEM_TYPES)

export const COMPARATOR_META = {
    eq: { symbol: "=", text: "equals" },
    gte: { symbol: "≥", text: "at least" },
    lte: { symbol: "≤", text: "at most" },
}

export const SEVERITY_OPTIONS = [
    { value: "critical", text: "Critical" },
    { value: "warning", text: "Warning" },
    { value: "info", text: "Info" },
]

export function isContentType(type) {
    return CONTENT_TYPES.includes(type)
}

export function isItemType(type) {
    return ITEM_TYPES.includes(type)
}

function plural(count, noun) {
    return `${count} ${noun}${count === 1 ? "" : "s"}`
}

// A list or a count: previews and jobs keep only the count
function countOf(value) {
    if (Array.isArray(value)) {
        return value.length
    }
    if (value && typeof value === "object") {
        return Object.keys(value).length
    }
    return Number(value) || 0
}

// What an organisation, sharing group or custom galaxy rule expects, short
export function itemExpectedText(type, expected) {
    const value = expected || {}
    if (type === "organisation") {
        const parts = ["type", "nationality", "sector"].filter(field => value[field]).map(field => value[field])
        if (value.local === true || value.local === false) {
            parts.push(value.local ? "local" : "external")
        }
        return parts.length > 0 ? `present · ${parts.join(" · ")}` : "present"
    }
    if (type === "sharing_group") {
        return `at least ${plural(countOf(value.members), "member")}`
    }
    return `enabled, ${plural(countOf(value.clusters), "cluster")}`
}

// Whether two expected values of an item rule check the same thing (the server normalises their order)
export function sameItemExpected(type, a, b) {
    const left = a || {}
    const right = b || {}
    const texts = type === "organisation" ? ["name", "type", "nationality", "sector"] : ["name", "releasability", "description"]
    if (texts.some(field => (left[field] || "") !== (right[field] || ""))) {
        return false
    }
    if (type === "organisation") {
        return (left.local === undefined ? null : left.local) === (right.local === undefined ? null : right.local)
    }
    if (type === "sharing_group") {
        const members = list => (list || []).map(member => member.uuid).sort().join(",")
        return members(left.members) === members(right.members)
    }
    const clusters = map => Object.entries(map || {}).map(([uuid, version]) => `${uuid}:${version}`).sort().join(",")
    return clusters(left.clusters) === clusters(right.clusters)
}

// A value the way MISP's diagnostics show it
export function formatValue(value) {
    if (value === null || value === undefined || value === "") {
        return "(empty)"
    }
    if (typeof value === "boolean") {
        return value ? "true" : "false"
    }
    if (typeof value === "object") {
        return JSON.stringify(value)
    }
    return String(value)
}

// What a rule expects, short: "≥ 12", "= true", "enabled", "at least 4 members"
export function expectedText(rule) {
    if (isItemType(rule.type)) {
        return itemExpectedText(rule.type, rule.expected)
    }
    if (isContentType(rule.type)) {
        const on = rule.type === "object_template_active" ? "active" : "enabled"
        const off = rule.type === "object_template_active" ? "inactive" : "disabled"
        return rule.expected === false ? off : on
    }
    if (rule.type === "version_min") {
        return `≥ ${rule.expected}`
    }
    const comparator = COMPARATOR_META[rule.comparator] || COMPARATOR_META.eq
    return `${comparator.symbol} ${formatValue(rule.expected)}`
}

// What a server has, in the rule's words. For an organisation, sharing group or custom galaxy, what differs
export function actualText(rule, cell) {
    if (!cell) {
        return ""
    }
    if (isItemType(rule.type)) {
        if (cell.actual === null || cell.actual === undefined) {
            return cell.state === "unknown" ? "unknown" : "absent"
        }
        return cell.reason || "as expected"
    }
    if (isContentType(rule.type)) {
        if (cell.actual === null || cell.actual === undefined) {
            return "absent"
        }
        const on = rule.type === "object_template_active" ? "active" : "enabled"
        const off = rule.type === "object_template_active" ? "inactive" : "disabled"
        return cell.actual ? on : off
    }
    if (rule.type === "version_min" && (cell.actual === null || cell.actual === undefined)) {
        return "unknown"
    }
    return formatValue(cell.actual)
}

export function ruleTitle(rule) {
    if (rule.type === "version_min") {
        return "MISP version"
    }
    return rule.label || rule.key
}

// The setting name under a label, or the item's key when it has no label yet
export function ruleSubtitle(rule) {
    if (rule.type === "setting" && rule.label && rule.label !== rule.key) {
        return rule.key
    }
    if ((rule.type === "galaxy_enabled" || rule.type === "object_template_active") && !rule.label) {
        return "Name not listed yet"
    }
    return ""
}

export function isServerSpecific(name, types) {
    if (!types || !name) {
        return false
    }
    return types.server_specific_settings.includes(name) || types.server_specific_prefixes.some(prefix => name.startsWith(prefix))
}

// A setting's value as a rule expects it: MISP reports numbers as text
export function expectedFromSetting(setting) {
    if (!setting) {
        return ""
    }
    const value = setting.value
    if (setting.type === "boolean") {
        return value === true || value === 1 || value === "1" || value === "true"
    }
    if ((setting.type === "numeric" || setting.type === "float") && value !== "" && value !== null && !Number.isNaN(Number(value))) {
        return Number(value)
    }
    return value === null || value === undefined ? "" : value
}

// `options` of a MISP setting: a list (index = value) or an object (value → label)
export function settingOptions(setting) {
    if (!setting || !setting.options) {
        return null
    }
    const entries = Array.isArray(setting.options)
        ? setting.options.map((text, index) => [String(index), text])
        : Object.entries(setting.options)
    return entries.map(([value, text]) => ({ value, text: `${text} (${value})` }))
}

// Where a baseline can be copied from
export const SOURCE_KINDS = {
    preset: { label: "Preset", plural: "Presets", icon: "fas fa-box-archive" },
    saved: { label: "Saved baseline", plural: "Saved baselines", icon: "fas fa-bookmark" },
    fleet: { label: "Fleet", plural: "Other fleets", icon: "fas fa-layer-group" },
}

export function sourceKey(source) {
    return source ? `${source.kind}:${source.id}` : ""
}

// The copy request's field for a source
export function sourceParam(source) {
    if (source.kind === "preset") {
        return { from_preset: source.id }
    }
    if (source.kind === "saved") {
        return { from_saved_id: source.id }
    }
    return { from_fleet_id: source.id }
}

export function ruleCountText(count) {
    return plural(count, "rule")
}

const TYPE_COUNT_NOUNS = {
    setting: ["setting", "settings"],
    taxonomy_enabled: ["taxonomy", "taxonomies"],
    galaxy_enabled: ["galaxy", "galaxies"],
    object_template_active: ["object template", "object templates"],
    version_min: ["minimum version", "minimum versions"],
    organisation: ["organisation", "organisations"],
    sharing_group: ["sharing group", "sharing groups"],
    custom_galaxy: ["custom galaxy", "custom galaxies"],
}

// `{type: count}` as a list in the usual type order, for chips: `text` is "6 taxonomies"
export function typeSummary(types) {
    return Object.keys(TYPE_META)
        .filter(type => types && types[type] > 0)
        .map(type => ({
            type,
            count: types[type],
            label: TYPE_META[type].label,
            icon: TYPE_META[type].icon,
            text: `${types[type]} ${TYPE_COUNT_NOUNS[type][types[type] === 1 ? 0 : 1]}`,
        }))
}

// What changes when a rule is replaced by another with the same type and key: the expected value (a pair of texts,
// null when it stays), and the rest in words
export function ruleChange(current, next) {
    const others = []
    if (current.severity !== next.severity) {
        others.push(`severity ${current.severity} → ${next.severity}`)
    }
    if ((current.note || "") !== (next.note || "")) {
        others.push(next.note ? "new note" : "note removed")
    }
    if (Boolean(current.forced) !== Boolean(next.forced)) {
        others.push(next.forced ? "forced" : "no longer forced")
    }
    const before = expectedText(current)
    const after = expectedText(next)
    const sameExpected = isItemType(current.type)
        ? sameItemExpected(current.type, current.expected, next.expected)
        : before === after
    if (sameExpected) {
        return { expected: null, others }
    }
    // An item described differently, with the same short text
    return { expected: before === after ? [before, "described differently"] : [before, after], others }
}

const IP_HOST = /^(\d{1,3}(\.\d{1,3}){3}|\[.*\])$/

// The host (and port) of a server named after its URL, else null
function urlHost(name) {
    if (!/^https?:\/\//i.test(name || "")) {
        return null
    }
    try {
        const url = new URL(name)
        return { hostname: url.hostname, port: url.port }
    } catch (error) {
        return null
    }
}

// Short column labels for the servers of a fleet. A server named after its URL is shown by its host, without the
// domain all such servers share (misp-a.example.org, misp-b.example.org → misp-a, misp-b); other names are kept.
// Answers the labels by server ID and the shared domain (empty when nothing was left out)
export function serverLabels(servers) {
    const hosts = new Map()
    servers.forEach((server) => {
        const host = urlHost(server.name)
        if (host !== null) {
            hosts.set(server.id, host)
        }
    })
    // Only host names lose their domain: the common end of IP addresses means nothing
    const named = [...hosts.values()].filter(host => !IP_HOST.test(host.hostname)).map(host => host.hostname.split("."))
    let shared = 0
    if (named.length >= 2) {
        shared = Math.min(...named.map(labels => labels.length - 1))
        while (shared > 0 && !named.every(labels => labels.slice(-shared).join(".") === named[0].slice(-shared).join("."))) {
            shared -= 1
        }
    }
    const domain = shared > 0 ? named[0].slice(-shared).join(".") : ""
    const labels = new Map()
    servers.forEach((server) => {
        const host = hosts.get(server.id)
        if (!host) {
            labels.set(server.id, server.name || server.url || `Server ${server.id}`)
            return
        }
        const hostname = domain !== "" && !IP_HOST.test(host.hostname) ? host.hostname.slice(0, -(domain.length + 1)) : host.hostname
        labels.set(server.id, host.port ? `${hostname}:${host.port}` : hostname)
    })
    return { labels, domain }
}

// How a rule stands across the fleet: servers per state, and the values found where it drifts, most frequent first
export function ruleTally(rule, servers) {
    const tally = { match: 0, drift: 0, unknown: 0, found: [] }
    const found = new Map()
    servers.forEach((server) => {
        const cell = server.results[String(rule.id)]
        const state = cell && ["match", "drift", "unknown"].includes(cell.state) ? cell.state : "unknown"
        tally[state] += 1
        if (state === "drift") {
            const text = actualText(rule, cell)
            found.set(text, (found.get(text) || 0) + 1)
        }
    })
    tally.found = [...found.entries()]
        .map(([text, count]) => ({ text, count }))
        .sort((a, b) => b.count - a.count || a.text.localeCompare(b.text))
    return tally
}

// The tally in words, for a tooltip: "Drifts on 3 of 51 servers, found false on 2 and (empty) on 1"
export function tallyText(tally, total) {
    const parts = []
    if (tally.drift > 0) {
        const shown = tally.found.slice(0, 4).map(value => `${value.text} on ${value.count}`)
        const others = tally.found.length - shown.length
        if (others > 0) {
            shown.push(plural(others, "other value"))
        }
        parts.push(`Drifts on ${tally.drift} of ${plural(total, "server")}, found ${shown.join(", ")}`)
    } else if (tally.match > 0) {
        parts.push(`In line on ${tally.match} of ${plural(total, "server")}`)
    }
    if (tally.unknown > 0) {
        parts.push(`unknown on ${tally.unknown}`)
    }
    return parts.join("; ") || "No server to check"
}
