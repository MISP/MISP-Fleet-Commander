// Wording shared by the baseline views

export const TYPE_META = {
    setting: { label: "Setting", icon: "fas fa-sliders", keyLabel: "Setting" },
    taxonomy_enabled: { label: "Taxonomy", icon: "fas fa-tags", keyLabel: "Taxonomy" },
    galaxy_enabled: { label: "Galaxy", icon: "fas fa-meteor", keyLabel: "Galaxy" },
    object_template_active: { label: "Object template", icon: "fas fa-cubes", keyLabel: "Object template" },
    version_min: { label: "MISP version", icon: "fas fa-code-branch", keyLabel: null },
}

export const CONTENT_TYPES = ["taxonomy_enabled", "galaxy_enabled", "object_template_active"]

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

// What a rule expects, short: "≥ 12", "= true", "enabled"
export function expectedText(rule) {
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

// What a server has, in the rule's words
export function actualText(rule, cell) {
    if (!cell) {
        return ""
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
