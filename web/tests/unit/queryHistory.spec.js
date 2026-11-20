import { describe, expect, it } from "vitest"
import { hasPoints, historyCharts, latestText, pointNote, sharedDomain, thresholdOf } from "@/helpers/queryHistory"

// As `GET /queries/saved/<id>/history` gives it
const HISTORY = {
    kind: "count",
    tier: "hour",
    limit: null,
    servers: [
        { server_id: 1, server_name: "misp-a", points: [[100, 4], [200, 7]], lows: [[100, 2], [200, 7]], highs: [[100, 9], [200, 7]], capped: [] },
        { server_id: 2, server_name: "misp-b", points: [], lows: [], highs: [], capped: [] },
        { server_id: 3, server_name: "misp-c", points: [[200, 1200]], lows: [[200, 1100]], highs: [[200, 1300]], capped: [200] },
    ],
}

describe("thresholdOf", () => {
    it("draws the expectation, tinting where answers miss it", () => {
        expect(thresholdOf({ comparator: "lte", value: 500 }, "at most 500")).toEqual({ value: 500, text: "Expected at most 500", side: "above" })
        expect(thresholdOf({ comparator: "gte", value: 3 }, "at least 3")).toEqual({ value: 3, text: "Expected at least 3", side: "below" })
        expect(thresholdOf({ comparator: "eq", value: 12 }, "exactly 12").side).toBe(null)
        expect(thresholdOf({ comparator: "ne", value: 12 }, "anything but 12").side).toBe(null)
    })

    it("knows counts are never negative", () => {
        expect(thresholdOf({ comparator: "eq", value: 0 }, "no rows")).toEqual({ value: 0, text: "Expected no rows", side: "above" })
        expect(thresholdOf({ comparator: "lte", value: 0 }, "at most 0").side).toBe("above")
        // Nothing a line on the baseline could show
        expect(thresholdOf({ comparator: "gt", value: 0 }, "some rows")).toBe(null)
        expect(thresholdOf({ comparator: "gte", value: 0 }, "at least 0")).toBe(null)
        expect(thresholdOf({ comparator: "ne", value: 0 }, "anything but 0")).toBe(null)
    })

    it("draws nothing without an expectation", () => {
        expect(thresholdOf(null, null)).toBe(null)
        expect(thresholdOf({ comparator: "about", value: 3 }, "")).toBe(null)
        expect(thresholdOf({ comparator: "eq", value: "3" }, "")).toBe(null)
        expect(thresholdOf({ comparator: "lt", value: 5 }, null).text).toBe("")
    })
})

describe("sharedDomain", () => {
    it("spans every server's answers and the expectation, with some room, never below 0", () => {
        // 2 … 1300, 15% of the span on each side
        expect(sharedDomain(HISTORY.servers, null)).toEqual([0, 1300 + 1298 * 0.15])
        const [lo, hi] = sharedDomain([{ points: [[1, 800], [2, 900]] }], { value: 1000 })
        expect([lo, hi]).toEqual([770, 1030])
        expect(sharedDomain([{ points: [[1, 837]] }], null)).toEqual([837 - 41.85, 837 + 41.85])
        expect(sharedDomain([{ points: [] }], { value: 5 })).toBe(null)
        expect(sharedDomain([], null)).toBe(null)
    })
})

describe("historyCharts", () => {
    it("follows the table's order, then the others as listed", () => {
        const charts = historyCharts(HISTORY, [3, 99, 1])
        expect(charts.map((chart) => chart.serverId)).toEqual([3, 1, 2])
        expect(historyCharts(HISTORY, null).map((chart) => chart.serverName)).toEqual(["misp-a", "misp-b", "misp-c"])
    })

    it("gives each server one series with its band, and its latest answer", () => {
        const [a, b, c] = historyCharts(HISTORY, [])
        expect(a.series).toEqual([{ key: "value", label: "Count", points: [[100, 4], [200, 7]], peaks: [[100, 9], [200, 7]], lows: [[100, 2], [200, 7]] }])
        expect(a.latest).toEqual({ ts: 200, value: 7, more: false })
        expect(b.latest).toBe(null)
        expect(c.latest.more).toBe(true)
        expect(historyCharts({ ...HISTORY, kind: "select" }, [])[0].series[0].label).toBe("Rows")
        expect(historyCharts(null, [])).toEqual([])
    })
})

describe("words", () => {
    it("says the latest answer", () => {
        expect(latestText({ value: 1284, more: false })).toBe("Latest 1,284")
        expect(latestText({ value: 100, more: true })).toBe("Latest 100 or more")
        expect(latestText(null)).toBe("No answer over this range")
    })

    it("says what a point stands for", () => {
        expect(pointNote({ tier: "raw", kind: "count" })).toBe("Each point is one answer.")
        expect(pointNote({ tier: "day", kind: "count" })).toMatch(/^Each point is a day: its last answer/)
        expect(pointNote({ tier: "raw", kind: "select", limit: 1000 }))
            .toBe("Each point is one answer. A SELECT counts the rows it returned, at most its LIMIT: a point at 1,000 may stand for more.")
        expect(pointNote(null)).toBe("")
    })

    it("knows whether there is anything to draw", () => {
        expect(hasPoints(HISTORY)).toBe(true)
        expect(hasPoints({ servers: [{ points: [] }] })).toBe(false)
        expect(hasPoints(null)).toBe(false)
    })
})
