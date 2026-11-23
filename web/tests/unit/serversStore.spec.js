import { beforeEach, describe, expect, it, vi } from "vitest"
import api from "@/api/servers"
import servers from "@/store/modules/servers"

vi.mock("@/api/servers", () => ({ default: { queryInfo: vi.fn(), index: vi.fn() } }))

const FINAL_SETTINGS = [
    { setting: "MISP.uuid", value: "c0ffee" },
    { setting: "MISP.background_jobs", value: true },
    { setting: "MISP.baseurl", value: "https://misp.test" },
]

function snapshot(timestamp, light) {
    const serverSettings = { workers: { default: {} }, moduleStatus: {}, proxyStatus: "OK", zmqStatus: 0 }
    serverSettings.finalSettings = light ? FINAL_SETTINGS.slice(0, 2) : FINAL_SETTINGS
    if (!light) {
        serverSettings.dbDiagnostics = { events: 12 }
    }
    const info = { timestamp, query_result: { serverSettings, serverUsage: { stats: {} }, serverUser: { Role: {} } } }
    return light ? Object.assign(info, { light: true }) : info
}

function newState() {
    const state = {}
    servers.mutations.resetState(state)
    return state
}

// Runs an action with a commit that applies the module's mutations to `state`
function run(action, state, payload) {
    const commit = (type, data) => servers.mutations[type](state, data)
    const dispatch = (type, data) => run(type.replace("servers/", ""), state, data)
    return servers.actions[action]({ commit, dispatch, state }, payload)
}

describe("servers store: light snapshots in lists, full ones for the server page", () => {
    let state

    beforeEach(() => {
        state = newState()
        api.queryInfo.mockReset()
    })

    it("fills what lists show from a light snapshot, and leaves the settings list and diagnostics out", () => {
        servers.mutations.setServers(state, [{ id: 1, url: "https://misp.test", server_info: snapshot(100, true) }])
        expect(state.final_settings[1]).toEqual({ "MISP.uuid": "c0ffee", "MISP.background_jobs": true })
        expect(state.workers[1]).toEqual({ default: {} })
        expect(state.last_refresh[1]).toBe(100)
        expect(state.raw_final_settings[1]).toBeUndefined()
        expect(state.diagnostic_full[1]).toBeUndefined()
        expect(state.full_info[1]).toBeUndefined()
    })

    it("loads the full snapshot once per refresh", async () => {
        servers.mutations.setServers(state, [{ id: 1, url: "https://misp.test", server_info: snapshot(100, true) }])
        api.queryInfo.mockImplementation((payload, cb) => cb(snapshot(100, false)))
        await run("fetchFullInfo", state, { server_id: 1 })
        expect(api.queryInfo).toHaveBeenCalledTimes(1)
        expect(Object.values(state.raw_final_settings[1])).toHaveLength(3)
        expect(state.diagnostic_full[1].dbDiagnostics).toEqual({ events: 12 })
        expect(state.final_settings[1]["MISP.baseurl"]).toBe("https://misp.test")
        expect(state.full_info[1]).toBe(100)

        await run("fetchFullInfo", state, { server_id: 1 })
        expect(api.queryInfo).toHaveBeenCalledTimes(1)

        // A refresh sends a light snapshot: the full parts stay until the page asks again
        await run("commitAllQueryInfo", state, Object.assign(snapshot(200, true), { server: { id: 1 } }))
        expect(state.last_refresh[1]).toBe(200)
        expect(Object.values(state.raw_final_settings[1])).toHaveLength(3)
        api.queryInfo.mockImplementation((payload, cb) => cb(snapshot(200, false)))
        await run("fetchFullInfo", state, { server_id: 1 })
        expect(api.queryInfo).toHaveBeenCalledTimes(2)
        expect(state.full_info[1]).toBe(200)
    })

    it("asks again when a refresh landed while the full snapshot was on its way", async () => {
        servers.mutations.setServers(state, [{ id: 1, url: "https://misp.test", server_info: snapshot(100, true) }])
        api.queryInfo
            .mockImplementationOnce((payload, cb) => {
                servers.mutations.setLastRefresh(state, { server_id: 1, last_refresh: 200 })
                cb(snapshot(100, false))
            })
            .mockImplementationOnce((payload, cb) => cb(snapshot(200, false)))
        await run("fetchFullInfo", state, { server_id: 1 })
        expect(api.queryInfo).toHaveBeenCalledTimes(2)
        expect(state.full_info[1]).toBe(200)
        expect(state.last_refresh[1]).toBe(200)
    })

    it("shares one request between views asking at the same time, and copes with a server without snapshot", async () => {
        let answer
        api.queryInfo.mockImplementation((payload, cb) => { answer = cb })
        const first = run("fetchFullInfo", state, { server_id: 2 })
        const second = run("fetchFullInfo", state, { server_id: 2 })
        answer({ error: "Unkown server" })
        await Promise.all([first, second])
        expect(api.queryInfo).toHaveBeenCalledTimes(1)
        expect(state.full_info[2]).toBe(null)
        await run("fetchFullInfo", state, { server_id: 2 })
        expect(api.queryInfo).toHaveBeenCalledTimes(1)
    })
})

describe("servers store: the server list", () => {
    let state, rootState, answers

    // fetchServers with the module's getters and mutations, the selected fleet in `rootState`
    const fetchServers = (payload) => servers.actions.fetchServers({
        commit: (type, data) => servers.mutations[type](state, data),
        getters: { serverCount: servers.getters.serverCount(state) },
        rootState,
    }, payload)
    const names = () => Object.values(state.servers).map((server) => server.name)

    beforeEach(() => {
        state = newState()
        rootState = { fleets: { selected: { id: 1 } } }
        answers = []
        api.index.mockReset()
        // Each request waits until the test answers it
        api.index.mockImplementation((cb, errorCb) => answers.push({ cb, errorCb }))
    })

    it("shares the request on its way for the same fleet, forced or not, and says it is fetching meanwhile", async () => {
        const first = fetchServers({ force: true })
        expect(fetchServers({ force: true })).toBe(first)
        expect(fetchServers()).toBe(first)
        expect(api.index).toHaveBeenCalledTimes(1)
        expect(state.fetching_servers_in_progress).toBe(true)
        answers[0].cb([{ id: 3, name: "misp-a" }])
        await first
        expect(names()).toEqual(["misp-a"])
        expect(state.fetching_servers_in_progress).toBe(false)
    })

    it("fetches a list that is not loaded yet, and only asks again when forced", async () => {
        const first = fetchServers()
        answers[0].cb([{ id: 3, name: "misp-a" }])
        await first
        await expect(fetchServers()).resolves.toBe("Server already loaded")
        expect(api.index).toHaveBeenCalledTimes(1)
        const forced = fetchServers({ force: true })
        expect(api.index).toHaveBeenCalledTimes(2)
        answers[1].cb([{ id: 3, name: "misp-a" }, { id: 4, name: "misp-b" }])
        await forced
        expect(names()).toEqual(["misp-a", "misp-b"])
    })

    it("asks again after a change, and keeps the latest answer whatever the order they come back in", async () => {
        const before = fetchServers({ force: true })
        const after = fetchServers({ force: true, fresh: true })
        expect(after).not.toBe(before)
        expect(api.index).toHaveBeenCalledTimes(2)
        answers[1].cb([{ id: 3, name: "misp-a" }, { id: 4, name: "added" }])
        await after
        answers[0].cb([{ id: 3, name: "misp-a" }])
        await before
        expect(names()).toEqual(["misp-a", "added"])
        expect(state.fetching_servers_in_progress).toBe(false)
    })

    it("does not share a request for another fleet, nor keep a list once another fleet is chosen", async () => {
        const fleetOne = fetchServers({ force: true })
        rootState.fleets.selected = { id: 2 }
        const fleetTwo = fetchServers({ force: true })
        expect(api.index).toHaveBeenCalledTimes(2)
        answers[0].cb([{ id: 3, name: "of fleet 1" }])
        await fleetOne
        expect(names()).toEqual([])
        answers[1].cb([{ id: 7, name: "of fleet 2" }])
        await fleetTwo
        expect(names()).toEqual(["of fleet 2"])

        const late = fetchServers({ force: true })
        rootState.fleets.selected = { id: 1 }
        answers[2].cb([{ id: 8, name: "late" }])
        await late
        expect(names()).toEqual(["of fleet 2"])
    })

    it("passes a failure on, and asks again on the next call", async () => {
        const failing = fetchServers({ force: true })
        answers[0].errorCb("Unreachable")
        await expect(failing).rejects.toBe("Unreachable")
        expect(state.fetching_servers_in_progress).toBe(false)
        const again = fetchServers({ force: true })
        expect(api.index).toHaveBeenCalledTimes(2)
        answers[1].cb([])
        await again
    })
})
