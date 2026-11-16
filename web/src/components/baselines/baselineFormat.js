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
