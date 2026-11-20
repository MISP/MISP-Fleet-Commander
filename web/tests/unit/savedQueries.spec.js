import { describe, expect, it } from "vitest"
import {
    answerText, consequenceText, expectationForm, expectationText, formExpectation, overviewParts, savedBody,
    savedSelection, scheduleLabel, stateMeta, targetText, wholeFleet,
} from "@/helpers/savedQueries"

// As `GET /queries/language` gives them, under `saved`
const OPTIONS = {
    schedules: [{ minutes: 15, label: "Every 15 minutes" }, { minutes: 60, label: "Every hour" }],
    comparators: [
        { name: "eq", symbol: "=", words: "exactly" }, { name: "lte", symbol: "≤", words: "at most" },
        { name: "gt", symbol: ">", words: "above" },
    ],
    row_expectations: [{ comparator: "eq", value: 0, label: "no rows" }, { comparator: "gt", value: 0, label: "some rows" }],
}

const FLEETS = [
    { id: 1, name: "Production", servers: [{ id: 11 }, { id: 12 }] },
    { id: 2, name: "Lab", servers: [{ id: 21 }] },
]

describe("states", () => {
    it("takes the saved query's severity when not as expected", () => {
        expect(stateMeta("unmet", "critical").tone).toBe("critical")
        expect(stateMeta("unmet", "info").tone).toBe("info")
        expect(stateMeta("unchecked", "critical").tone).toBe("info")
        expect(stateMeta("met", "critical").tone).toBe("ok")
        expect(stateMeta("somethingnew").label).toBe("somethingnew")
    })

    it("lists the states worth showing, worst first", () => {
        const parts = overviewParts({ met: 2, unmet: 1, unchecked: 0, not_run: 3, answered: 0 }, "warning")
        expect(parts.map(part => part.text)).toEqual(["1 not as expected", "2 as expected", "3 not run yet"])
        expect(parts[0].tone).toBe("warning")
        expect(overviewParts(null, "warning")).toEqual([])
    })
})

describe("words", () => {
    it("names the schedule and the target", () => {
        expect(scheduleLabel(null, OPTIONS.schedules)).toBe("By hand")
        expect(scheduleLabel(60, OPTIONS.schedules)).toBe("Every hour")
        expect(scheduleLabel(90, OPTIONS.schedules)).toBe("Every 90 minutes")
        expect(targetText({ fleet_id: 1, fleet_name: "Production" })).toBe("Fleet Production")
        expect(targetText({ fleet_id: null, server_ids: [1], server_count: 1 })).toBe("1 server")
        expect(targetText({ fleet_id: null, server_ids: null, server_count: 0 })).toBe("No servers")
    })

    it("says what a server answered", () => {
        expect(answerText({ outcome: "count", value: 12345 })).toBe("12,345")
        expect(answerText({ outcome: "rows", value: 0 })).toBe("No rows")
        expect(answerText({ outcome: "rows", value: 1 })).toBe("1 row")
        expect(answerText({ outcome: "rows", value: 100, more: true })).toBe("100 rows or more")
        expect(answerText({ outcome: "not_supported", message: "This MISP does not run complex queries" }))
            .toBe("This MISP does not run complex queries")
        expect(answerText({ outcome: "timeout", message: "" })).toBe("Timeout")
        expect(answerText({ outcome: "not_supported", message: "this MISP does not run them" })).toBe("This MISP does not run them")
        expect(answerText(null)).toBe("")
    })

    it("says the expectation as the server does", () => {
        expect(expectationText("count", { comparator: "lte", value: 5 }, OPTIONS)).toBe("at most 5")
        expect(expectationText("select", { comparator: "eq", value: 0 }, OPTIONS)).toBe("no rows")
        expect(expectationText("select", { comparator: "gt", value: 0 }, OPTIONS)).toBe("some rows")
        expect(expectationText("count", null, OPTIONS)).toBe("")
    })

    it("says what saving will do", () => {
        const base = { schedules: OPTIONS.schedules, options: OPTIONS, severity: "warning" }
        expect(consequenceText(Object.assign({}, base, { kind: "describe" }))).toMatch(/don't run on a schedule/)
        expect(consequenceText(Object.assign({}, base, { kind: "count", schedule: null, expectation: null })))
            .toBe("Kept to run again by hand.")
        expect(consequenceText(Object.assign({}, base, { kind: "count", schedule: 60, expectation: null })))
            .toBe("Runs every hour; each server's answer is kept, without raising issues.")
        expect(consequenceText(Object.assign({}, base, { kind: "count", schedule: 60, expectation: { comparator: "eq", value: 0 } })))
            .toBe("Runs every hour. A server whose count is not exactly 0 shows on Needs attention as a warning issue; one that can't run it, as info.")
        expect(consequenceText(Object.assign({}, base, { kind: "select", schedule: 15, severity: "info", expectation: { comparator: "eq", value: 0 } })))
            .toBe("Runs every 15 minutes. A server that finds rows shows on Needs attention as info; one that can't run it, as info.")
        expect(consequenceText(Object.assign({}, base, { kind: "select", schedule: null, expectation: { comparator: "gt", value: 0 } })))
            .toBe("Run by hand, each server shows whether it answered some rows. Only scheduled runs raise issues.")
    })
})

describe("targets", () => {
    it("recognises a whole fleet, whatever the order", () => {
        expect(wholeFleet([12, 11], FLEETS).name).toBe("Production")
        expect(wholeFleet([11], FLEETS)).toBe(null)
        expect(wholeFleet([11, 12, 21], FLEETS)).toBe(null)
        expect(wholeFleet([], FLEETS)).toBe(null)
    })

    it("selects a saved query's servers among those known", () => {
        expect(savedSelection({ fleet_id: 1 }, FLEETS)).toEqual([11, 12])
        expect(savedSelection({ fleet_id: 9 }, FLEETS)).toEqual([])
        expect(savedSelection({ fleet_id: null, server_ids: [21, 99, 11] }, FLEETS)).toEqual([21, 11])
        expect(savedSelection({ fleet_id: null, server_ids: null }, FLEETS)).toEqual([])
    })
})

describe("the form", () => {
    it("turns the expectation into what the API takes, and back", () => {
        expect(formExpectation("count", { comparator: "", value: 3 })).toBe(null)
        expect(formExpectation("count", { comparator: "lte", value: "3" })).toEqual({ comparator: "lte", value: 3 })
        expect(formExpectation("count", { comparator: "lte", value: "3.5" })).toEqual({ comparator: "lte", value: "3.5" })
        expect(formExpectation("select", { rows: "no_rows" })).toEqual({ comparator: "eq", value: 0 })
        expect(formExpectation("select", { rows: "some_rows" })).toEqual({ comparator: "gt", value: 0 })
        expect(formExpectation("select", { rows: "none" })).toBe(null)
        expect(formExpectation("describe", { comparator: "eq", value: 0 })).toBe(null)
        expect(expectationForm("select", { comparator: "gt", value: 0 }).rows).toBe("some_rows")
        expect(expectationForm("count", { comparator: "lte", value: 7 })).toMatchObject({ comparator: "lte", value: 7 })
        expect(expectationForm("count", null)).toEqual({ comparator: "", value: 0, rows: "none" })
    })

    it("builds the body: the fleet when it was chosen whole, else the servers", () => {
        const form = { name: "q", description: "", schedule: 60, comparator: "eq", value: 0, rows: "none", severity: "critical", target: "fleet" }
        expect(savedBody(form, { kind: "count", statement: "S", selected: [11, 12], fleet: FLEETS[0] })).toEqual({
            name: "q", description: "", statement: "S", fleet_id: 1, schedule_minutes: 60,
            expectation: { comparator: "eq", value: 0 }, severity: "critical",
        })
        const servers = savedBody(Object.assign({}, form, { target: "servers" }), { kind: "count", statement: "S", selected: [11, 12], fleet: FLEETS[0] })
        expect(servers.server_ids).toEqual([11, 12])
        expect(servers.fleet_id).toBe(undefined)
        // Details only: neither the statement nor the target
        const details = savedBody(form, { kind: "count" })
        expect(details.statement).toBe(undefined)
        expect(details.fleet_id).toBe(undefined)
        expect(details.server_ids).toBe(undefined)
        // DESCRIBE: no schedule, no expectation
        expect(savedBody(form, { kind: "describe", statement: "DESCRIBE events" })).toMatchObject({ schedule_minutes: null, expectation: null })
    })
})
