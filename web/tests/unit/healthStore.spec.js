import { beforeEach, describe, expect, it, vi } from "vitest"
import health, { EMPTY_DIGEST, compareIssues, serverDigest, severityRank, worstSeverity } from "@/store/modules/health"

vi.mock("@/api/health", () => ({ default: { summary: vi.fn() } }))

function issue(id, server_id, severity, extra = {}) {
    return { id, server_id, fleet_id: 1, severity, ack: null, first_seen: 100, ...extra }
}

function newState() {
    return { issuesByServer: {}, digests: {}, summary: null, loaded: false, loading: false, error: null, pending: {} }
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

    it("breaks ties on the ID as plain text, like the backend", () => {
        const issues = [issue("drift:1:9", 1, "info"), issue("drift:1:10", 1, "info"), issue("Drift:1:2", 1, "info")]
        expect(issues.sort(compareIssues).map(i => i.id)).toEqual(["Drift:1:2", "drift:1:10", "drift:1:9"])
    })
})

describe("server digest", () => {
    it("sorts unacknowledged issues and counts them per severity and per fleet", () => {
        const digest = serverDigest([
            issue("i", 1, "info"),
            issue("w", 1, "warning", { fleet_id: 2 }),
            issue("acked", 1, "critical", { ack: { until: null } }),
            issue("c", 1, "critical"),
        ])
        expect(digest.active.map(i => i.id)).toEqual(["c", "w", "i"])
        expect(digest.counts).toEqual({ critical: 1, warning: 1, info: 1 })
        expect(digest.fleetCounts).toEqual({ 1: { critical: 1, warning: 0, info: 1 }, 2: { critical: 0, warning: 1, info: 0 } })
        expect(digest.worst).toBe("critical")
        expect(digest.ackedCount).toBe(1)
    })

    it("weighs servers criticals first, then warnings, then info", () => {
        const oneCritical = serverDigest([issue("c", 1, "critical")])
        const manyWarnings = serverDigest(Array.from({ length: 999 }, (_, n) => issue(`w${n}`, 1, "warning")))
        const manyInfo = serverDigest(Array.from({ length: 999 }, (_, n) => issue(`i${n}`, 1, "info")))
        expect(oneCritical.weight).toBeGreaterThan(manyWarnings.weight)
        expect(serverDigest([issue("w", 1, "warning")]).weight).toBeGreaterThan(manyInfo.weight)
        expect(EMPTY_DIGEST).toMatchObject({ active: [], worst: null, ackedCount: 0, weight: 0 })
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

    it("only applies an acknowledgement to an issue it knows, and keeps the server's digest in line", () => {
        const before = state.issuesByServer[1]
        health.mutations.updateIssue(state, { id: "down", server_id: 1, ack: { until: 5 } })
        expect(state.issuesByServer[1][0].ack).toEqual({ until: 5 })
        expect(before[0].ack).toBe(null)
        expect(state.digests[1]).toMatchObject({ active: [], worst: null, ackedCount: 2 })
        expect(gettersOf(state).attentionCount).toBe(0)
        health.mutations.updateIssue(state, { id: "down", server_id: 9, ack: { until: 5 } })
        expect(state.issuesByServer[9]).toBeUndefined()
    })

    it("keeps issues frozen, so that the UI never makes them reactive", () => {
        health.mutations.setServerIssues(state, { server_id: 3, issues: [issue("new", 3, "warning")] })
        ;[1, 2, 3].forEach((server_id) => {
            expect(Object.isFrozen(state.issuesByServer[server_id])).toBe(true)
            state.issuesByServer[server_id].forEach(item => expect(Object.isFrozen(item)).toBe(true))
            expect(Object.isFrozen(state.digests[server_id])).toBe(true)
        })
    })

    it("lists the most severe issues of all servers, and every server's worst", () => {
        health.mutations.setServerIssues(state, { server_id: 3, issues: [
            issue("w1", 3, "warning", { first_seen: 50 }), issue("w2", 3, "warning", { first_seen: 60 }),
        ] })
        const getters = gettersOf(state)
        expect(getters.topIssues(3).map(i => i.id)).toEqual(["down", "w1", "w2"])
        expect(getters.topIssues(10).map(i => i.id)).toEqual(["down", "w1", "w2", "info"])
        expect(getters.serverActiveIssues[3].map(i => i.id)).toEqual(["w1", "w2"])
        expect(getters.activeIssues).toHaveLength(4)
        expect(getters.serverWorst).toEqual({ 1: "critical", 2: "info", 3: "warning" })
    })

    it("ignores live updates until the issues are loaded", () => {
        const fresh = newState()
        const commit = vi.fn()
        health.actions.SOCKET_HEALTH_UPDATED({ commit, dispatch: vi.fn(), state: fresh }, { server_id: 1, issues: [] })
        expect(commit).not.toHaveBeenCalled()
    })
})
