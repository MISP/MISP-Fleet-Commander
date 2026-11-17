import { TYPE_META, actualText, expectedText, formatValue, isContentType, isItemType } from "./baselineFormat"

// A remediation preview (`servers[].items[]`, see the backend's `previewForUser`) as the fix dialog shows it

// The order the fix applies rules in on a server: organisations, then sharing groups, then the rest
const TYPE_RANK = { organisation: 0, sharing_group: 1 }

export function typeIcon(item) {
    return (TYPE_META[item.type] || {}).icon || "fas fa-circle"
}

export function typeLabel(item) {
    return (TYPE_META[item.type] || {}).label || ""
}

export function itemName(item) {
    if (item.type === "version_min") {
        return "MISP version"
    }
    return item.label || item.key
}

export function currentText(item) {
    if (isItemType(item.type)) {
        return item.current === null || item.current === undefined ? "absent" : item.difference
    }
    return actualText(item, { actual: item.current })
}

export function targetText(item) {
    if (isItemType(item.type)) {
        return item.current === null || item.current === undefined ? "created" : "as in the baseline"
    }
    if (isContentType(item.type)) {
        return expectedText(item)
    }
    return formatValue(item.expected)
}

function isApplied(item) {
    return item.action === "apply"
}

// Each drifting rule with the servers it drifts on (`details`: [{server, item}]). Rules fixed from here come first,
// in the order the fix applies them; rules only fixable by hand last. `currentText` is the value the rule has on
// every server, or null when it varies; `reasonText` the one reason it must be done by hand, or null
export function ruleGroups(plan) {
    const groups = new Map()
    plan.servers.forEach((server) => {
        server.items.forEach((item) => {
            if (!groups.has(item.rule_id)) {
                groups.set(item.rule_id, { key: `rule:${item.rule_id}`, rule: item, details: [], seen: groups.size })
            }
            groups.get(item.rule_id).details.push({ server, item })
        })
    })
    return Array.from(groups.values())
        .map((group) => {
            const applied = group.details.filter(entry => isApplied(entry.item))
            const currents = new Set(applied.map(entry => currentText(entry.item)))
            const reasons = new Set(group.details.filter(entry => !isApplied(entry.item)).map(entry => entry.item.reason))
            return Object.freeze(Object.assign(group, {
                applyCount: applied.length,
                manualCount: group.details.length - applied.length,
                currentText: currents.size === 1 ? currents.values().next().value : null,
                reasonText: reasons.size === 1 ? reasons.values().next().value : null,
                search: `${itemName(group.rule)} ${group.rule.key || ""}`.toLowerCase(),
            }))
        })
        .sort((a, b) => (a.applyCount === 0) - (b.applyCount === 0)
            || (TYPE_RANK[a.rule.type] ?? 2) - (TYPE_RANK[b.rule.type] ?? 2)
            || a.seen - b.seen)
}

// Each server with its values (`details`), in the order the fix applies them
export function serverGroups(plan) {
    return plan.servers.map((server) => {
        const applyCount = server.items.filter(isApplied).length
        return Object.freeze({
            key: `server:${server.id}`,
            server,
            details: server.items,
            applyCount,
            manualCount: server.items.length - applyCount,
            search: server.name.toLowerCase(),
        })
    })
}

// The `[{server_id, rule_id}]` the fix can apply from here
export function applyItems(plan) {
    return plan.servers.flatMap(server => server.items
        .filter(isApplied)
        .map(item => ({ server_id: server.id, rule_id: item.rule_id })))
}

// What starts the fix: exact cells as such; otherwise the servers and rules the preview listed, which may be more
// pairs than a request can name. The backend fixes what still drifts among them
export function fixRequest(plan, scope) {
    const items = applyItems(plan)
    if (scope && scope.items) {
        return { items }
    }
    return {
        server_ids: Array.from(new Set(items.map(item => item.server_id))),
        rule_ids: Array.from(new Set(items.map(item => item.rule_id))),
    }
}
