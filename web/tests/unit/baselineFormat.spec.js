import { describe, expect, it } from "vitest"
import {
    actualText, expectedFromSetting, expectedText, isServerSpecific, ruleChange, sameItemExpected, settingOptions,
    sourceParam, typeSummary,
} from "@/components/baselines/baselineFormat"

describe("expected and actual values", () => {
    it("words what a rule expects", () => {
        expect(expectedText({ type: "setting", comparator: "gte", expected: 12 })).toBe("≥ 12")
        expect(expectedText({ type: "setting", expected: true })).toBe("= true")
        expect(expectedText({ type: "setting", expected: "" })).toBe("= (empty)")
        expect(expectedText({ type: "taxonomy_enabled", expected: false })).toBe("disabled")
        expect(expectedText({ type: "object_template_active", expected: true })).toBe("active")
        expect(expectedText({ type: "version_min", expected: "2.5.0" })).toBe("≥ 2.5.0")
        expect(expectedText({ type: "organisation", expected: { name: "CIRCL", type: "CSIRT", local: true } }))
            .toBe("present · CSIRT · local")
        expect(expectedText({ type: "sharing_group", expected: { members: [{ uuid: "a" }] } })).toBe("at least 1 member")
        expect(expectedText({ type: "custom_galaxy", expected: { clusters: { a: 1, b: 2 } } })).toBe("enabled, 2 clusters")
    })

    it("words what a server has", () => {
        expect(actualText({ type: "setting" }, null)).toBe("")
        expect(actualText({ type: "galaxy_enabled" }, { actual: null })).toBe("absent")
        expect(actualText({ type: "object_template_active" }, { actual: false })).toBe("inactive")
        expect(actualText({ type: "version_min" }, { actual: null })).toBe("unknown")
        expect(actualText({ type: "organisation" }, { actual: null, state: "unknown" })).toBe("unknown")
        expect(actualText({ type: "organisation" }, { actual: {}, reason: "sector differs" })).toBe("sector differs")
    })

    it("takes setting values the way MISP reports them", () => {
        expect(expectedFromSetting({ type: "boolean", value: "1" })).toBe(true)
        expect(expectedFromSetting({ type: "boolean", value: 0 })).toBe(false)
        expect(expectedFromSetting({ type: "numeric", value: "12" })).toBe(12)
        expect(expectedFromSetting({ type: "numeric", value: "abc" })).toBe("abc")
        expect(expectedFromSetting({ type: "string", value: null })).toBe("")
        expect(expectedFromSetting(null)).toBe("")
    })

    it("lists setting options from a list or an object", () => {
        expect(settingOptions({ options: ["No", "Yes"] })).toEqual([{ value: "0", text: "No (0)" }, { value: "1", text: "Yes (1)" }])
        expect(settingOptions({ options: { a: "Alpha" } })).toEqual([{ value: "a", text: "Alpha (a)" }])
        expect(settingOptions({})).toBe(null)
    })
})

describe("items, sources and summaries", () => {
    it("compares item rules regardless of order", () => {
        const members = [{ uuid: "a" }, { uuid: "b" }]
        expect(sameItemExpected("sharing_group", { name: "SG", members }, { name: "SG", members: members.slice().reverse() })).toBe(true)
        expect(sameItemExpected("sharing_group", { name: "SG", members }, { name: "SG", members: [{ uuid: "a" }] })).toBe(false)
        expect(sameItemExpected("organisation", { name: "O" }, { name: "O", local: false })).toBe(false)
        expect(sameItemExpected("custom_galaxy", { name: "G", clusters: { a: 1 } }, { name: "G", clusters: { a: 2 } })).toBe(false)
    })

    it("describes what replacing a rule changes", () => {
        const current = { type: "setting", expected: 1, severity: "warning", note: "" }
        expect(ruleChange(current, { ...current, expected: 2, severity: "critical", forced: true }))
            .toEqual({ expected: ["= 1", "= 2"], others: ["severity warning → critical", "forced"] })
        expect(ruleChange(current, { ...current, note: "why" })).toEqual({ expected: null, others: ["new note"] })
        const org = { type: "organisation", expected: { name: "O", type: "CSIRT", sector: "a" }, severity: "info" }
        expect(ruleChange(org, { ...org, expected: { name: "O", type: "CSIRT", sector: "b" } }).expected)
            .toEqual(["present · CSIRT · a", "present · CSIRT · b"])
    })

    it("recognises server-specific settings", () => {
        const types = { server_specific_settings: ["MISP.baseurl"], server_specific_prefixes: ["Plugin.ZeroMQ_"] }
        expect(isServerSpecific("MISP.baseurl", types)).toBe(true)
        expect(isServerSpecific("Plugin.ZeroMQ_port", types)).toBe(true)
        expect(isServerSpecific("MISP.live", types)).toBe(false)
        expect(isServerSpecific("MISP.live", null)).toBe(false)
    })

    it("builds copy parameters and type chips", () => {
        expect(sourceParam({ kind: "preset", id: "focused" })).toEqual({ from_preset: "focused" })
        expect(sourceParam({ kind: "saved", id: 3 })).toEqual({ from_saved_id: 3 })
        expect(sourceParam({ kind: "fleet", id: 2 })).toEqual({ from_fleet_id: 2 })
        expect(typeSummary({ galaxy_enabled: 1, setting: 3, taxonomy_enabled: 0 }).map(t => t.text))
            .toEqual(["3 settings", "1 galaxy"])
    })
})
