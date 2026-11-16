import { beforeEach, describe, expect, it, vi } from "vitest"
import health, { compareIssues, severityRank, worstSeverity } from "@/store/modules/health"

vi.mock("@/api/health", () => ({ default: { summary: vi.fn() } }))

function issue(id, server_id, severity, extra = {}) {
    return { id, server_id, fleet_id: 1, severity, ack: null, first_seen: 100, ...extra }
}

function newState() {
    return { issuesByServer: {}, summary: null, loaded: false, loading: false, error: null, pending: {} }
}

// Evaluates the module's getters the way vuex does, each one seeing the others
function gettersOf(state) {
    const getters = {}
    Object.entries(health.getters).forEach(([name, getter]) => {
        Object.defineProperty(getters, name, { get: () => getter(state, getters) })
    })
    return getters
}

describe("severity helpers", () => {
    it("ranks severities, unknown ones last", () => {
        expect(severityRank("critical")).toBeLessThan(severityRank("warning"))
        expect(severityRank("whatever")).toBe(3)
        expect(worstSeverity([{ severity: "info" }, { severity: "warning" }])).toBe("warning")
        expect(worstSeverity([])).toBe(null)
    })

    it("sorts the most severe first, then the oldest", () => {
        const issues = [issue("c", 1, "info", { first_seen: 1 }), issue("b", 1, "critical", { first_seen: 9 }), issue("a", 1, "critical", { first_seen: 5 })]
        expect(issues.sort(compareIssues).map(i => i.id)).toEqual(["a", "b", "c"])
    })
})

describe("health store", () => {
    let state

    beforeEach(() => {
        state = newState()
        health.mutations.setAllIssues(state, [
            issue("down", 1, "critical"),
            issue("old", 1, "warning", { ack: { until: null } }),
            issue("info", 2, "info", { fleet_id: 2 }),
        ])
    })

    it("counts unacknowledged issues; the navigation only counts critical and warning ones", () => {
        const getters = gettersOf(state)
        expect(getters.counts).toEqual({ critical: 1, warning: 0, info: 1 })
        expect(getters.attentionCount).toBe(1)
        expect(getters.acknowledgedIssues.map(i => i.id)).toEqual(["old"])
        expect(getters.fleetCounts).toEqual({ 1: { critical: 1, warning: 0, info: 0 }, 2: { critical: 0, warning: 0, info: 1 } })
        expect(getters.serverWorst).toEqual({ 1: "critical", 2: "info" })
    })

    it("replaces a server's issues on a live update, and a reload empties servers that no longer have any", () => {
        health.mutations.setServerIssues(state, { server_id: 1, issues: [] })
        expect(gettersOf(state).attentionCount).toBe(0)
        health.mutations.setAllIssues(state, [issue("info", 2, "info")])
        expect(state.issuesByServer).toEqual({ 1: [], 2: [expect.objectContaining({ id: "info" })] })
    })

    it("only applies an acknowledgement to an issue it knows", () => {
        health.mutations.updateIssue(state, { id: "down", server_id: 1, ack: { until: 5 } })
        expect(state.issuesByServer[1][0].ack).toEqual({ until: 5 })
        health.mutations.updateIssue(state, { id: "down", server_id: 9, ack: { until: 5 } })
        expect(state.issuesByServer[9]).toBeUndefined()
    })

    it("ignores live updates until the issues are loaded", () => {
        const fresh = newState()
        const commit = vi.fn()
        health.actions.SOCKET_HEALTH_UPDATED({ commit, dispatch: vi.fn(), state: fresh }, { server_id: 1, issues: [] })
        expect(commit).not.toHaveBeenCalled()
    })
})
