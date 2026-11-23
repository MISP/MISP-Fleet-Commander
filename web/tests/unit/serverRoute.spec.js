import { describe, expect, it, vi } from "vitest"
import { sameServer, selectServerFleet, serverInSelectedFleet } from "@/helpers/serverRoute"

// The parts of the Vuex store the server page's guards read
function fakeStore({ selected = null, servers = {}, fails = false } = {}) {
    return {
        state: { servers: { servers } },
        getters: { "fleets/selectedFleet": selected },
        dispatch: vi.fn((action) => {
            if (action === "fleets/selectFleetFromServerId" && fails) {
                return Promise.reject(new Error("Unknown server"))
            }
            return Promise.resolve()
        }),
    }
}

describe("sameServer", () => {
    it("compares server IDs whether a link gave a number or the URL gave text", () => {
        const route = (serverId) => ({ params: { server_id: serverId } })
        expect(sameServer(route("2"), route(2))).toBe(true)
        expect(sameServer(route("2"), route("2"))).toBe(true)
        expect(sameServer(route("2"), route(12))).toBe(false)
    })
})

describe("serverInSelectedFleet", () => {
    it("holds a server only once its fleet is selected and its servers are loaded", () => {
        expect(serverInSelectedFleet(fakeStore({ selected: { id: 1 }, servers: { 3: { id: 3 } } }), "3")).toBe(true)
        expect(serverInSelectedFleet(fakeStore({ selected: { id: 1 }, servers: { 3: { id: 3 } } }), "12")).toBe(false)
        expect(serverInSelectedFleet(fakeStore({ selected: { id: 1 } }), "3")).toBe(false)
        expect(serverInSelectedFleet(fakeStore({ servers: { 3: { id: 3 } } }), "3")).toBe(false)
    })
})

describe("selectServerFleet", () => {
    it("leaves the store alone when it already holds the server", async () => {
        const store = fakeStore({ selected: { id: 1 }, servers: { 3: { id: 3 } } })
        await expect(selectServerFleet(store, "3")).resolves.toBe(false)
        expect(store.dispatch).not.toHaveBeenCalled()
    })

    it("selects the fleet of a server from another fleet, then loads its servers", async () => {
        const store = fakeStore({ selected: { id: 1 }, servers: { 3: { id: 3 } } })
        await expect(selectServerFleet(store, "12")).resolves.toBe(true)
        expect(store.dispatch.mock.calls).toEqual([
            ["fleets/selectFleetFromServerId", "12"],
            ["servers/fetchServers", { force: true }],
        ])
    })

    it("selects it when no fleet is selected, or its servers are not loaded yet", async () => {
        for (const store of [fakeStore(), fakeStore({ selected: { id: 1 } })]) {
            await expect(selectServerFleet(store, "3")).resolves.toBe(true)
            expect(store.dispatch).toHaveBeenCalledWith("fleets/selectFleetFromServerId", "3")
        }
    })

    it("rejects an unknown server without loading anything", async () => {
        const store = fakeStore({ fails: true })
        await expect(selectServerFleet(store, "99")).rejects.toThrow("Unknown server")
        expect(store.dispatch).toHaveBeenCalledTimes(1)
    })
})
