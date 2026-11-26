import { describe, expect, it } from "vitest"
import {
    candidateWhere, carriedText, changeText, movedIds, problemText, reportingText, scheduleWords, standingParts, totalNote,
    totalValueText, totalView, widgetFacts, widgetSpans,
} from "@/helpers/usageWidgets"

// As `GET /fleets/<id>/widgets/<widget id>/history` gives it
const HISTORY = {
    kind: "count",
    limit: null,
    total: {
        tier: "hour",
        interval_s: 3600,
        points: [[0, 10], [3600, 12], [7200, 19]],
        reporting: [[0, 1], [3600, 1], [7200, 2]],
        capped: [],
        servers: 3,
    },
}

describe("widgetFacts", () => {
    it("says what the saved query is, how often it runs, what it expects", () => {
        expect(widgetFacts({ kind: "count", schedule_minutes: 60, expectation_text: "at most 900" }))
            .toBe("COUNT · hourly · expects at most 900")
        expect(widgetFacts({ kind: "select", schedule_minutes: null, expectation_text: null })).toBe("SELECT · run by hand")
        expect(widgetFacts(null)).toBe("")
    })

    it("names every schedule", () => {
        expect([15, 60, 360, 720, 1440, 30].map(scheduleWords))
            .toEqual(["every 15 min", "hourly", "every 6 h", "every 12 h", "daily", "every 30 min"])
    })
})

describe("standingParts", () => {
    it("counts the fleet's servers by state, worst first", () => {
        const servers = [{ state: "met" }, { state: "unmet" }, { state: "met" }, { state: "not_run" }]
        expect(standingParts(servers, "critical").map((part) => [part.text, part.tone])).toEqual([
            ["1 not as expected", "critical"], ["2 as expected", "ok"], ["1 not run yet", "muted"],
        ])
        expect(standingParts([], "warning")).toEqual([])
    })
})

describe("candidateWhere", () => {
    it("says where a saved query runs from the fleet's point of view", () => {
        expect(candidateWhere({ aims_at_fleet: true, fleet_servers: 4 }, 4)).toBe("On this fleet")
        expect(candidateWhere({ aims_at_fleet: false, fleet_servers: 4 }, 4)).toBe("On all 4 of this fleet's servers")
        expect(candidateWhere({ aims_at_fleet: false, fleet_servers: 1 }, 4)).toBe("On 1 of this fleet's 4 servers")
        expect(candidateWhere({ aims_at_fleet: false, fleet_servers: 1 }, 1)).toBe("On this fleet's server")
        expect(candidateWhere({ aims_at_fleet: false, fleet_servers: 2 }, 2)).toBe("On both of this fleet's servers")
    })
})

describe("widgetSpans", () => {
    it("pairs Fleet totals that follow each other, in order; anything alone in its row takes it whole", () => {
        const widgets = [[1, "total"], [2, "total"], [3, "total"], [4, "servers"], [5, "total"], [6, "total"], [7, "total"]]
            .map(([id, display]) => ({ id, display }))
        expect(widgetSpans(widgets)).toEqual({ 1: "half", 2: "half", 3: "full", 4: "full", 5: "half", 6: "half", 7: "full" })
        expect(widgetSpans([])).toEqual({})
    })
})

describe("totalView", () => {
    it("draws the total and reads its last point", () => {
        const view = totalView(HISTORY)
        expect(view.series).toEqual([{ key: "total", label: "Count", points: HISTORY.total.points, band: false }])
        expect(view.latest).toEqual({ ts: 7200, value: 19, more: false, reporting: 2 })
        expect(view.change).toMatchObject({ first: 10, last: 19, abs: 9 })
        expect(view.servers).toBe(3)
        expect(totalValueText(view.latest)).toBe("19")
        expect(changeText(view.change)).toBe("+9 (+90%)")
        expect(reportingText(view)).toBe("2 of 3 servers answered so far")
    })

    it("says when a SELECT's total may stand for more", () => {
        const view = totalView({ kind: "select", total: { points: [[0, 100]], reporting: [[0, 1]], capped: [0], servers: 1 } })
        expect(view.series[0].label).toBe("Rows")
        expect(totalValueText(view.latest)).toBe("100 or more")
        expect(changeText(view.change)).toBe("")
        expect(reportingText(view)).toBe("")
    })

    it("has nothing to say without points or a total", () => {
        const view = totalView({ kind: "count", total: { points: [], reporting: [], capped: [], servers: 2 } })
        expect(view.latest).toBe(null)
        expect(totalValueText(view.latest)).toBe("—")
        expect(reportingText(view)).toBe("")
        expect(totalView({ kind: "count" })).toBe(null)
        expect(changeText({ abs: 0 })).toBe("No change")
    })
})

describe("carriedText", () => {
    const NOW = 2000000000
    const withCarried = (carried) => ({ kind: "count", total: Object.assign({}, HISTORY.total, { to: NOW, carried }) })

    it("names the one server whose old answer the total still holds", () => {
        const text = carriedText(withCarried([
            { server_id: 4, server_name: "Refused org test", ts: NOW - 12 * 86400, value: 471, more: false },
        ]))
        expect(text.text).toBe("Includes Refused org test's last answer (471), 12 days old")
        expect(text.title).toMatch(/^Its last run gave no number/)
    })

    it("sums several, gives the oldest age, and lists each one in the title", () => {
        const text = carriedText(withCarried([
            { server_id: 4, server_name: "Refused org test", ts: NOW - 12 * 86400, value: 1471, more: false },
            { server_id: 7, server_name: "Lab", ts: NOW - 3 * 3600, value: 100, more: true },
        ]))
        expect(text.text).toBe("Includes 2 servers' last answers (1,571 or more), the oldest 12 days old")
        expect(text.title.split("\n")).toEqual([
            "Their last run gave no number: the total keeps each one's last answer until it answers again.",
            "Refused org test: 1,471, 12 days old",
            "Lab: 100 or more, 3 h old",
        ])
    })

    it("says nothing when every number in the total is current", () => {
        expect(carriedText(withCarried([]))).toBe(null)
        expect(carriedText(HISTORY)).toBe(null)
        expect(carriedText(null)).toBe(null)
    })
})

describe("totalNote", () => {
    it("says what a point of the total is", () => {
        expect(totalNote(HISTORY)).toBe(
            "Each point is an hour: each server's last answer, summed. A server without an answer that hour counts with its previous one.")
        const daily = { kind: "select", limit: 1000, total: { tier: "day" } }
        expect(totalNote(daily)).toBe(
            "Each point is a day: each server's last answer, summed. A server without an answer that day counts with its previous one."
            + " A SELECT counts the rows it returned, at most 1,000 each: a total holding one at its LIMIT may stand for more.")
        expect(totalNote(null)).toBe("")
    })

    it("speaks of the one server the tab is limited to", () => {
        expect(totalNote(HISTORY, { single: true })).toBe(
            "Each point is an hour: the server's last answer that hour, or its previous one when it gave none.")
        const daily = { kind: "select", limit: 1000, total: { tier: "day" } }
        expect(totalNote(daily, { single: true })).toBe(
            "Each point is a day: the server's last answer that day, or its previous one when it gave none."
            + " A SELECT counts the rows it returned, at most 1,000: a point at its LIMIT may stand for more.")
    })
})

describe("movedIds", () => {
    it("moves one widget up or down, never out", () => {
        expect(movedIds([1, 2, 3], 2, -1)).toEqual([2, 1, 3])
        expect(movedIds([1, 2, 3], 2, 1)).toEqual([1, 3, 2])
        expect(movedIds([1, 2, 3], 1, -1)).toEqual([1, 2, 3])
        expect(movedIds([1, 2, 3], 3, 1)).toEqual([1, 2, 3])
        expect(movedIds([1, 2, 3], 9, 1)).toEqual([1, 2, 3])
    })
})

describe("problemText", () => {
    it("says why a widget has nothing to draw", () => {
        expect(problemText("no_server")).toBe("It runs on none of this fleet's servers now.")
        expect(problemText("no_number")).toMatch(/no longer answers a number/)
        expect(problemText(null)).toBe("")
    })

    it("names the server the tab is limited to", () => {
        expect(problemText("no_server", "misp-a")).toBe("It does not run on misp-a now.")
        expect(problemText("no_number", "misp-a")).toMatch(/no longer answers a number/)
    })
})
