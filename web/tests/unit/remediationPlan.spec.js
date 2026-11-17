import { describe, expect, it } from "vitest"
import { applyItems, fixRequest, ruleGroups, serverGroups } from "@/components/baselines/remediationPlan"

function item(rule_id, type, extra = {}) {
    return { rule_id, type, key: `key-${rule_id}`, label: `rule ${rule_id}`, expected: false, current: true, action: "apply", reason: "", ...extra }
}

const UPGRADE = "Upgrade MISP on this server"

// alpha and beta drift on the same galaxy; beta also on a taxonomy it has in another state; both need an upgrade
function plan() {
    return {
        servers: [
            { id: 1, name: "alpha", items: [item(10, "galaxy_enabled"), item(30, "version_min", { action: "manual", reason: UPGRADE, expected: "3.1" })] },
            { id: 2, name: "beta", items: [
                item(20, "organisation", { current: null, expected: { name: "CIRCL" } }),
                item(10, "galaxy_enabled"),
                item(30, "version_min", { action: "manual", reason: UPGRADE, expected: "3.1" }),
            ] },
            { id: 3, name: "gamma", items: [item(10, "galaxy_enabled", { current: false, expected: true })] },
        ],
        excluded: [],
        counts: { apply: 4, manual: 2, servers: 3 },
    }
}

describe("fix dialog: a preview grouped by rule or by server", () => {
    it("groups by rule in the order the fix applies them, rules fixed by hand last", () => {
        const groups = ruleGroups(plan())
        expect(groups.map(group => group.rule.rule_id)).toEqual([20, 10, 30])
        const [organisation, galaxy, version] = groups
        expect(organisation).toMatchObject({ applyCount: 1, manualCount: 0, currentText: "absent" })
        expect(galaxy.details.map(entry => entry.server.name)).toEqual(["alpha", "beta", "gamma"])
        expect(galaxy).toMatchObject({ applyCount: 3, manualCount: 0, currentText: null })
        expect(version).toMatchObject({ applyCount: 0, manualCount: 2, reasonText: UPGRADE })
        expect(version.search).toBe("misp version key-30")
    })

    it("says what a rule is everywhere when servers agree", () => {
        const agreeing = plan()
        agreeing.servers[2].items[0].current = true
        expect(ruleGroups(agreeing)[1].currentText).toBe("enabled")
    })

    it("groups by server with what can be fixed and what cannot", () => {
        expect(serverGroups(plan()).map(group => [group.server.name, group.applyCount, group.manualCount]))
            .toEqual([["alpha", 1, 1], ["beta", 2, 1], ["gamma", 1, 0]])
    })

    it("starts exact cells as such, anything wider by servers and rules", () => {
        expect(applyItems(plan())).toHaveLength(4)
        expect(fixRequest(plan(), { items: [{ server_id: 3, rule_id: 10 }] }).items).toHaveLength(4)
        expect(fixRequest(plan(), {})).toEqual({ server_ids: [1, 2, 3], rule_ids: [10, 20] })
        expect(fixRequest(plan(), { rule_ids: [10] })).toEqual({ server_ids: [1, 2, 3], rule_ids: [10, 20] })
    })
})
