import { describe, expect, it } from "vitest"
import {
    fallbackLatencyClass, healthTone, isProblem, toneBadge, toneTextClass, toneTitle,
} from "@/helpers/healthCells"

function issue(rule, severity, extra = {}) {
    return { id: `${rule}-${severity}`, rule, severity, title: `${rule} ${severity}`, ack: null, category: "workers", ...extra }
}

describe("healthTone", () => {
    it("takes the worst unacknowledged issue of the rules asked for", () => {
        const issues = [issue("workers_down", "warning"), issue("workers_down", "critical", { id: "b" }), issue("slow", "info")]
        const tone = healthTone(issues, { rules: ["workers_down"] })
        expect(tone.level).toBe("critical")
        expect(tone.acked).toBe(false)
        expect(tone.issues.map(i => i.severity)).toEqual(["critical", "warning"])
    })

    it("draws acknowledged issues muted, and only when nothing else matches", () => {
        const acked = issue("slow", "warning", { ack: { until: null } })
        expect(healthTone([acked], { rules: "slow" })).toMatchObject({ level: "warning", acked: true })
        const active = issue("slow", "info", { id: "other" })
        expect(healthTone([acked, active], { rules: "slow" })).toMatchObject({ level: "info", acked: false })
    })

    it("narrows to one subject, compared as text", () => {
        const issues = [issue("worker_queue", "critical", { subject: "prio" }), issue("worker_queue", "warning", { id: "x", subject: "5" })]
        expect(healthTone(issues, { rules: "worker_queue", subject: 5 }).level).toBe("warning")
        expect(healthTone(issues, { rules: "worker_queue", subject: "default" }).level).toBe("ok")
    })

    it("says unchecked when the server cannot be queried, unless the rule does not read the snapshot", () => {
        const down = issue("unreachable", "critical", { category: "availability" })
        expect(healthTone([down], { rules: "workers_down" }).level).toBe("unchecked")
        expect(healthTone([down], { rules: "workers_down", content: false }).level).toBe("ok")
        expect(healthTone([down], { rules: "unreachable", content: false }).level).toBe("critical")
    })
})

describe("tone rendering", () => {
    it("falls back to the cell's own look while health is not loaded", () => {
        expect(toneTextClass(null)).toBe("")
        expect(toneBadge(null, "success")).toEqual({ variant: "success", class: "" })
        expect(toneTitle(null)).toBe("")
        expect(isProblem(null)).toBe(false)
    })

    it("maps levels to classes and badges", () => {
        expect(toneTextClass({ level: "critical", acked: false })).toBe("text-danger")
        expect(toneTextClass({ level: "warning", acked: false })).toBe("health-ink-warning")
        expect(toneTextClass({ level: "ok", acked: false }, "text-muted")).toBe("text-muted")
        expect(toneTextClass({ level: "warning", acked: true })).toBe("health-acked health-acked-warning")
        expect(toneBadge({ level: "critical", acked: false })).toEqual({ variant: "danger", class: "" })
        expect(toneBadge({ level: "unchecked", acked: false })).toEqual({ variant: "light", class: "" })
        expect(toneBadge({ level: "info", acked: true }).class).toContain("health-acked-info")
        expect(isProblem({ level: "info" })).toBe(true)
        expect(isProblem({ level: "ok" })).toBe(false)
        expect(isProblem({ level: "unchecked" })).toBe(false)
    })

    it("explains the colour in the tooltip", () => {
        const tone = healthTone([issue("slow", "warning"), issue("slow", "info", { id: "b", ack: { until: null } })], { rules: "slow" })
        expect(toneTitle(tone)).toBe("slow warning\nslow info (acknowledged)")
        expect(toneTitle({ level: "unchecked", issues: [] })).toMatch(/^Not checked/)
    })

    it("colours latency by threshold until health is loaded", () => {
        expect(fallbackLatencyClass(0.1)).toBe("text-success")
        expect(fallbackLatencyClass(1)).toBe("text-warning")
        expect(fallbackLatencyClass(3)).toBe("text-danger")
    })
})
