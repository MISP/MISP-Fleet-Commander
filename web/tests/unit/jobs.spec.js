import { describe, expect, it } from "vitest"
import { formatDuration, isFinalJob, jobStatusMeta, jobTally, mergeJob, resultCounts } from "@/helpers/jobs"

describe("job helpers", () => {
    it("tallies results from the counters", () => {
        expect(jobTally({ total: 10, succeeded: 4, failed: 2, done: 7 })).toEqual({ total: 10, ok: 4, failed: 2, other: 1, pending: 3, done: 7 })
        expect(jobTally({})).toEqual({ total: 0, ok: 0, failed: 0, other: 0, pending: 0, done: 0 })
    })

    it("knows final statuses and describes unknown ones", () => {
        expect(isFinalJob({ status: "partial" })).toBe(true)
        expect(isFinalJob({ status: "running" })).toBe(false)
        expect(isFinalJob(null)).toBe(false)
        expect(jobStatusMeta("weird")).toMatchObject({ label: "weird", tone: "muted" })
    })

    it("counts results by status", () => {
        expect(resultCounts({ results: [{ status: "ok" }, { status: "ok" }, { status: "error" }] }))
            .toEqual({ pending: 0, ok: 2, error: 1, skipped: 0, cancelled: 0 })
        expect(resultCounts(null).ok).toBe(0)
    })

    it("formats durations", () => {
        expect(formatDuration(0.25)).toBe("0.3 s")
        expect(formatDuration(42)).toBe("42 s")
        expect(formatDuration(125)).toBe("2 min 05 s")
        expect(formatDuration(3720)).toBe("1 h 02 min")
        expect(formatDuration(null)).toBe("")
        expect(formatDuration(-1)).toBe("")
    })
})

describe("mergeJob", () => {
    const pending = { id: 1, status: "pending" }
    const ok = { id: 1, status: "ok" }

    it("keeps a final state over a late snapshot", () => {
        const done = { id: "j", status: "done", finished: 20, succeeded: 2, failed: 0, results: [ok] }
        const stale = { id: "j", status: "running", finished: null, succeeded: 1, failed: 0, results: [pending] }
        const merged = mergeJob(done, stale)
        expect(merged).toMatchObject({ status: "done", finished: 20, succeeded: 2, done: 1 })
        expect(merged.results).toEqual([ok])
    })

    it("takes newer results and keeps known ones when the update has none", () => {
        const running = { id: "j", status: "running", results: [pending, { id: 2, status: "pending" }] }
        const merged = mergeJob(running, { id: "j", status: "running", results: [ok, { id: 2, status: "error" }], failed: 1 })
        expect(merged.results.map(r => r.status)).toEqual(["ok", "error"])
        expect(merged.done).toBe(2)
        expect(mergeJob(merged, { id: "j", status: "partial" }).results).toBe(merged.results)
        expect(mergeJob(null, ok)).toBe(ok)
    })
})
