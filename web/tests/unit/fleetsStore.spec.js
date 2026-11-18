import { describe, expect, it, vi } from "vitest"
import fleets from "@/store/modules/fleets"

vi.mock("@/api/fleets", () => ({ default: {} }))

describe("fleet timestamps", () => {
    it("updates the fleet in the list and the selected one, so that views watching either see a collection", () => {
        const listed = { id: 1, watched_timestamp: 10, monitored_timestamp: 20 }
        const other = { id: 2, watched_timestamp: null, monitored_timestamp: null }
        const state = { all: { 1: listed, 2: other }, selected: { ...listed } }
        fleets.mutations.setFleetTimestamps(state, { fleet_id: 1, monitored_timestamp: 30 })
        expect(listed.monitored_timestamp).toBe(30)
        expect(state.selected.monitored_timestamp).toBe(30)
        fleets.mutations.setFleetTimestamps(state, { fleet_id: 1, watched_timestamp: 40 })
        expect([listed.watched_timestamp, state.selected.watched_timestamp]).toEqual([40, 40])
        expect(other).toEqual({ id: 2, watched_timestamp: null, monitored_timestamp: null })
    })
})
