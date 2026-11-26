// What the settings modal does with the settings the backend lists: grouping, checks, hints and the saving order

// $root event that opens the settings modal, optionally on one setting: { focus: "<setting name>" }
export const OPEN_SETTINGS_EVENT = "settings:open"

const PANEL_ICONS = {
    Scheduler: "fas fa-clock",
    Health: "fas fa-heart-pulse",
    Jobs: "fas fa-list-check",
    Queries: "fas fa-magnifying-glass",
}

export function panelIcon(panel) {
    return PANEL_ICONS[panel] || "fas fa-sliders"
}

function byPosition([nameA, a], [nameB, b]) {
    const positionA = Number.isFinite(a.position) ? a.position : Infinity
    const positionB = Number.isFinite(b.position) ? b.position : Infinity
    if (positionA !== positionB) {
        return positionA < positionB ? -1 : 1
    }
    return nameA.localeCompare(nameB)
}

// [{ panel, scopes: [{ scope, settings: [{ key, ...config }] }] }]: settings in the order they are defined in, panels
// and scopes in the order of their first setting
export function groupSettings(settings) {
    const panels = []
    Object.entries(settings || {}).sort(byPosition).forEach(([key, config]) => {
        const panelName = config.panel || "Other"
        const scopeName = config.scope || ""
        let panel = panels.find(p => p.panel === panelName)
        if (panel === undefined) {
            panel = { panel: panelName, scopes: [] }
            panels.push(panel)
        }
        let scope = panel.scopes.find(s => s.scope === scopeName)
        if (scope === undefined) {
            scope = { scope: scopeName, settings: [] }
            panel.scopes.push(scope)
        }
        scope.settings.push({ ...config, key })
    })
    return panels
}

export function settingLabel(setting) {
    return setting.text || setting.name || setting.key
}

// Every word of the query is in the setting's name, description, key, panel or scope
export function matchesQuery(setting, query) {
    const words = (query || "").toLowerCase().split(/\s+/).filter(Boolean)
    if (words.length === 0) {
        return true
    }
    const haystack = [settingLabel(setting), setting.description, setting.key, setting.key && setting.key.replace(/_/g, " "),
        setting.panel, setting.scope].filter(Boolean).join(" ").toLowerCase()
    return words.every(word => haystack.includes(word))
}

export function filterGroups(groups, query) {
    return groups
        .map(panel => ({
            ...panel,
            scopes: panel.scopes
                .map(scope => ({ ...scope, settings: scope.settings.filter(setting => matchesQuery(setting, query)) }))
                .filter(scope => scope.settings.length > 0),
        }))
        .filter(panel => panel.scopes.length > 0)
}

export function countSettings(panel) {
    return panel.scopes.reduce((total, scope) => total + scope.settings.length, 0)
}

export function isLocked(setting) {
    return setting.disabled === true
}

// config.json may hold "1" or 1 for a switch saved by older versions
export function asBoolean(value) {
    return value === true || value === 1 || value === "1" || value === "true"
}

function parseNumber(value) {
    if (typeof value === "number") {
        return value
    }
    if (typeof value !== "string" || value.trim() === "") {
        return NaN
    }
    return Number(value)
}

// The value sent to the backend for what the field holds
export function toSaved(setting, value) {
    if (setting.type === "checkbox") {
        return asBoolean(value)
    }
    if (setting.type === "number") {
        const number = parseNumber(value)
        return Number.isNaN(number) ? value : number
    }
    return value
}

// Whether the field holds the saved value: "10" and 10 are the same number
export function isSameValue(setting, a, b) {
    if (setting.type === "checkbox") {
        return asBoolean(a) === asBoolean(b)
    }
    if (setting.type === "number") {
        const numberA = parseNumber(a)
        const numberB = parseNumber(b)
        if (Number.isNaN(numberA) || Number.isNaN(numberB)) {
            return a === b
        }
        return numberA === numberB
    }
    return JSON.stringify(a) === JSON.stringify(b)
}

// Why the value cannot be saved, or null. The backend checks again, along with what depends on other settings
export function validateValue(setting, value) {
    if (setting.type !== "number") {
        return null
    }
    const number = parseNumber(value)
    if (Number.isNaN(number)) {
        return "Enter a number"
    }
    if (!Number.isInteger(number)) {
        return "The value must be a whole number"
    }
    const hasMin = Number.isFinite(setting.min)
    const hasMax = Number.isFinite(setting.max)
    if (Number.isFinite(setting.min_nonzero) && number !== 0 && number < setting.min_nonzero) {
        return `The value must be 0 or at least ${setting.min_nonzero}`
    }
    if (hasMin && number < setting.min) {
        return `The value must be at least ${setting.min}`
    }
    if (hasMax && number > setting.max) {
        return `The value must be at most ${setting.max}`
    }
    return null
}

// "1–1440", "0 or 365–3650", "at least 5"; empty for a setting that is not a number
export function rangeText(setting) {
    if (setting.type !== "number") {
        return ""
    }
    const hasMin = Number.isFinite(setting.min)
    const hasMax = Number.isFinite(setting.max)
    const low = Number.isFinite(setting.min_nonzero) ? setting.min_nonzero : setting.min
    let range = ""
    if (hasMin && hasMax) {
        range = `${low}–${setting.max}`
    } else if (hasMin) {
        range = `at least ${low}`
    } else if (hasMax) {
        range = `at most ${setting.max}`
    }
    if (range && Number.isFinite(setting.min_nonzero)) {
        return `0 or ${range}`
    }
    return range
}

const SINGULAR_UNITS = {
    minutes: "minute",
    seconds: "second",
    days: "day",
    servers: "server",
    rows: "row",
}

export function formatValue(setting, value) {
    if (setting.type === "checkbox") {
        return asBoolean(value) ? "On" : "Off"
    }
    if (value === null || value === undefined || value === "") {
        return "empty"
    }
    if (setting.type === "number" && setting.unit) {
        const unit = Number(value) === 1 && SINGULAR_UNITS[setting.unit] ? SINGULAR_UNITS[setting.unit] : setting.unit
        return `${value} ${unit}`
    }
    return String(value)
}

// Saves the changes one by one with save(key, value), a promise. The backend compares some settings with others
// (a retention never shorter than a finer one): a change refused before another one went through is tried again,
// as long as a pass saves something. Resolves to { saved: [key], failed: { key: message } }
export async function saveInOrder(changes, save) {
    const saved = []
    let pending = changes
    let failed = {}
    while (pending.length > 0) {
        const refused = []
        failed = {}
        for (const change of pending) {
            try {
                await save(change.key, change.value)
                saved.push(change.key)
            } catch (error) {
                failed[change.key] = typeof error === "string" ? error : (error && error.message) || "Could not save the setting"
                refused.push(change)
            }
        }
        if (refused.length === pending.length) {
            break
        }
        pending = refused
    }
    return { saved, failed }
}
