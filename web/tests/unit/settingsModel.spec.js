import { describe, expect, it } from "vitest"
import {
    filterGroups, formatValue, groupSettings, isSameValue, rangeText, saveInOrder, toSaved, validateValue,
} from "@/views/settings/settingsModel"

const interval = { type: "number", min: 1, max: 1440, default: 10, unit: "minutes" }
const dayRetention = { type: "number", min: 0, max: 3650, min_nonzero: 365, default: 0, zero_text: "Kept as long as their server" }
const enabled = { type: "checkbox", default: true }

describe("groupSettings", () => {
    it("keeps the order of the definitions, not the order of the keys", () => {
        const settings = {
            a_last: { panel: "Queries", scope: "History", position: 3 },
            b_first: { panel: "Scheduler", scope: "Fleet Watcher", position: 0 },
            c_second: { panel: "Scheduler", scope: "Monitoring System", position: 1 },
            d_third: { panel: "Scheduler", scope: "Fleet Watcher", position: 2 },
        }
        const groups = groupSettings(settings)
        expect(groups.map(p => p.panel)).toEqual(["Scheduler", "Queries"])
        expect(groups[0].scopes.map(s => s.scope)).toEqual(["Fleet Watcher", "Monitoring System"])
        expect(groups[0].scopes[0].settings.map(s => s.key)).toEqual(["b_first", "d_third"])
    })

    it("puts settings without a position after the others, by name", () => {
        const groups = groupSettings({ z: { panel: "P", position: 0 }, b: { panel: "P" }, a: { panel: "P" } })
        expect(groups[0].scopes[0].settings.map(s => s.key)).toEqual(["z", "a", "b"])
    })
})

describe("filterGroups", () => {
    const groups = groupSettings({
        monitoring_interval: { panel: "Scheduler", scope: "Monitoring System", name: "Monitoring Interval", description: "How often", position: 0 },
        job_retention_days: { panel: "Jobs", scope: "History", name: "Job Retention", description: "How long jobs are kept", position: 1 },
    })

    it("needs every word, in the name, description, key, panel or scope", () => {
        expect(filterGroups(groups, "jobs kept").map(p => p.panel)).toEqual(["Jobs"])
        expect(filterGroups(groups, "monitoring_interval")[0].scopes[0].settings[0].key).toBe("monitoring_interval")
        expect(filterGroups(groups, "retention days")).toHaveLength(1)
        expect(filterGroups(groups, "nothing like this")).toEqual([])
    })

    it("keeps everything for an empty query", () => {
        expect(filterGroups(groups, "  ")).toHaveLength(2)
    })
})

describe("values", () => {
    it("compares what a field holds with the saved value", () => {
        expect(isSameValue(interval, "10", 10)).toBe(true)
        expect(isSameValue(interval, "", 0)).toBe(false)
        expect(isSameValue(enabled, "1", true)).toBe(true)
        expect(isSameValue(enabled, false, true)).toBe(false)
    })

    it("sends numbers and booleans", () => {
        expect(toSaved(interval, "15")).toBe(15)
        expect(toSaved(enabled, "1")).toBe(true)
    })

    it("checks numbers before sending them", () => {
        expect(validateValue(interval, "")).toBe("Enter a number")
        expect(validateValue(interval, "2.5")).toBe("The value must be a whole number")
        expect(validateValue(interval, "0")).toBe("The value must be at least 1")
        expect(validateValue(interval, "1441")).toBe("The value must be at most 1440")
        expect(validateValue(interval, "15")).toBeNull()
        expect(validateValue(dayRetention, "0")).toBeNull()
        expect(validateValue(dayRetention, "30")).toBe("The value must be 0 or at least 365")
        expect(validateValue(dayRetention, "400")).toBeNull()
        expect(validateValue(enabled, false)).toBeNull()
    })

    it("describes the range", () => {
        expect(rangeText(interval)).toBe("1–1440")
        expect(rangeText(dayRetention)).toBe("0 or 365–3650")
        expect(rangeText({ type: "number", min: 5 })).toBe("at least 5")
        expect(rangeText(enabled)).toBe("")
    })

    it("formats a value with its unit", () => {
        expect(formatValue(interval, 10)).toBe("10 minutes")
        expect(formatValue(interval, 1)).toBe("1 minute")
        expect(formatValue({ type: "number", unit: "ms" }, 1)).toBe("1 ms")
        expect(formatValue(enabled, "1")).toBe("On")
    })
})

describe("saveInOrder", () => {
    it("tries a refused change again once another one went through", async () => {
        // Raw retention may not exceed hourly retention: raising both works hourly first
        const saved = { raw: 14, hour: 30 }
        const calls = []
        const save = (key, value) => {
            calls.push(key)
            if (key === "raw" && value > saved.hour) {
                return Promise.reject("The value must be at most the hourly retention")
            }
            saved[key] = value
            return Promise.resolve()
        }
        const result = await saveInOrder([{ key: "raw", value: 60 }, { key: "hour", value: 90 }], save)
        expect(result).toEqual({ saved: ["hour", "raw"], failed: {} })
        expect(calls).toEqual(["raw", "hour", "raw"])
    })

    it("stops when a pass saves nothing", async () => {
        const save = key => (key === "bad" ? Promise.reject("Nope") : Promise.resolve())
        const result = await saveInOrder([{ key: "bad", value: 1 }, { key: "good", value: 2 }], save)
        expect(result).toEqual({ saved: ["good"], failed: { bad: "Nope" } })
    })
})
