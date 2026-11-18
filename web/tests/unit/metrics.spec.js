import { describe, expect, it, vi } from "vitest"
import * as metrics from "@/helpers/metrics"

// Hours and days below are read in the browser's time zone: pinned before the module builds its formatters
// (`vi.hoisted` runs ahead of the imports)
vi.hoisted(() => {
    process.env.TZ = "UTC"
})

const HOUR = 3600
const DAY = 24 * HOUR
const MIDNIGHT = 1790035200 // Tue 2026-09-22 00:00 UTC

describe("formats", () => {
    it("formats values by unit", () => {
        const { formatValue } = metrics
        expect(formatValue(4291, "count")).toBe("4,291")
        expect(formatValue(2923792, "count")).toBe("2.9M")
        expect(formatValue(2923792, "count", { exact: true })).toBe("2,923,792")
        expect(formatValue(12900, "count")).toBe("12.9K")
        expect(formatValue("77.27", "percent")).toBe("77.3%")
        expect(formatValue(50, "percent")).toBe("50%")
        expect(formatValue(4.7841796875, "load")).toBe("4.78")
        expect(formatValue(9325825229, "bytes")).toBe("8.7 GB")
        expect(formatValue(42937360, "bytes")).toBe("41 MB")
        expect(formatValue(512, "bytes")).toBe("512 B")
        expect(formatValue(3, "jobs")).toBe("3")
        expect(formatValue(null, "count")).toBe("–")
        expect(formatValue("n/a", "count")).toBe("–")
    })

    it("signs changes", () => {
        const { formatDelta } = metrics
        expect(formatDelta(1204, "count")).toBe("+1,204")
        expect(formatDelta(-3, "count")).toBe("−3")
        expect(formatDelta(0, "count")).toBe("0")
        expect(formatDelta(125829120, "bytes")).toBe("+120 MB")
        expect(formatDelta(null, "count")).toBe("–")
    })

    it("formats relative changes", () => {
        const { formatChangePct } = metrics
        expect(formatChangePct(0.4321)).toBe("+0.4%")
        expect(formatChangePct(-12.3)).toBe("\u221212%")
        expect(formatChangePct(0.01)).toBe("")
        expect(formatChangePct(null)).toBe("")
    })

    it("formats axis ticks, with byte ticks in the unit of the axis maximum", () => {
        const { bytesUnit, formatTick } = metrics
        const gigabytes = bytesUnit(9325825229)
        expect(gigabytes).toEqual({ factor: 1024 ** 3, suffix: "GB" })
        expect(formatTick(2 * 1024 ** 3, "bytes", gigabytes)).toBe("2 GB")
        expect(formatTick(0.5 * 1024 ** 3, "bytes", gigabytes)).toBe("0.5 GB")
        expect(formatTick(50, "percent")).toBe("50%")
        expect(formatTick(20000, "count")).toBe("20K")
        expect(formatTick(2500, "count")).toBe("2,500")
        expect(formatTick(1.5, "load")).toBe("1.5")
    })

    it("formats benchmark durations", () => {
        const { formatDuration } = metrics
        expect(formatDuration(0.34)).toBe("340 ms")
        expect(formatDuration(0.0042)).toBe("4.2 ms")
        expect(formatDuration(1.234)).toBe("1.23 s")
        expect(formatDuration(12.34)).toBe("12.3 s")
        expect(formatDuration(252)).toBe("4 min 12 s")
        expect(formatDuration(240)).toBe("4 min")
        expect(formatDuration(5760)).toBe("1.6 h")
        expect(formatDuration(undefined)).toBe("–")
    })

    it("describes the period of a change", () => {
        const { changePhrase, rangeOf } = metrics
        const year = rangeOf("1y")
        const from = MIDNIGHT - 365 * DAY
        expect(changePhrase(year, from, from + HOUR)).toBe("over the last year")
        expect(changePhrase(year, from, MIDNIGHT)).toBe("since 22 Sept")
        expect(changePhrase(rangeOf("7d"), from, null)).toBe("over the last 7 days")
        expect(rangeOf("nope").key).toBe("7d")
    })

    it("names buckets by their size", () => {
        const { formatBucket } = metrics
        const ts = MIDNIGHT + 14 * HOUR + 20 * 60
        expect(formatBucket(ts, 600)).toBe("Tue 22 Sept, 14:20")
        expect(formatBucket(MIDNIGHT + 14 * HOUR, HOUR)).toBe("Tue 22 Sept, 14:00–15:00")
        expect(formatBucket(MIDNIGHT, DAY)).toBe("Tue 22 Sept")
    })
})

describe("snapshot", () => {
    it("reads MISP's statistics fields, numbers sent as strings", () => {
        expect(metrics.snapshotValues({ event_count: "4291", user_count: 6, org_count: "", attributes_per_event: "681" }))
            .toEqual({ events: 4291, users: 6 })
        expect(metrics.snapshotValues(undefined)).toEqual({})
    })
})

describe("series", () => {
    it("measures the change over the range", () => {
        expect(metrics.changeOver([[1, 100], [2, 150], [3, 120]])).toEqual({ first: 100, last: 120, abs: 20, pct: 20 })
        expect(metrics.changeOver([[1, 0], [2, 5]])).toMatchObject({ abs: 5, pct: null })
        expect(metrics.changeOver([[1, 7]])).toBeNull()
        expect(metrics.changeOver([])).toBeNull()
    })

    it("finds the maximum", () => {
        expect(metrics.maxOf([[1, 3], [2, 9], [3, 4]])).toBe(9)
        expect(metrics.maxOf([])).toBeNull()
    })

    it("cuts series where samples are missing", () => {
        const points = [[0, 1], [600, 2], [1200, 3], [4800, 4], [5400, 5]]
        expect(metrics.segments(points, 1500)).toEqual([[[0, 1], [600, 2], [1200, 3]], [[4800, 4], [5400, 5]]])
        expect(metrics.segments([], 1500)).toEqual([])
    })

    it("downsamples for sparklines", () => {
        const points = Array.from({ length: 100 }, (_, index) => [index, index])
        const result = metrics.downsample(points, 10)
        expect(result).toHaveLength(10)
        expect(result[0]).toEqual([9, 4.5])
        expect(result[9]).toEqual([99, 94.5])
        expect(metrics.downsample(points.slice(0, 5), 10)).toHaveLength(5)
    })

    it("sums points per bucket", () => {
        const points = [[MIDNIGHT + 60, 1], [MIDNIGHT + 1800, 2], [MIDNIGHT + HOUR, 4], [MIDNIGHT + DAY + 5, 8]]
        expect(metrics.bucketSum(points, HOUR)).toEqual([[MIDNIGHT, 3], [MIDNIGHT + HOUR, 4], [MIDNIGHT + DAY, 8]])
        expect(metrics.bucketSum(points, DAY)).toEqual([[MIDNIGHT, 7], [MIDNIGHT + DAY, 8]])
    })

    it("buckets logins per hour up to 7 days, per day beyond", () => {
        const raw = { logins: [[MIDNIGHT + 60, 1], [MIDNIGHT + 660, 2]], failed_logins: [[MIDNIGHT + 60, 1]] }
        expect(metrics.loginBars(raw, "24h", 600)).toEqual({
            size: HOUR, logins: [[MIDNIGHT, 3]], failed_logins: [[MIDNIGHT, 1]],
        })
        const hours = { logins: [[MIDNIGHT, 3], [MIDNIGHT + HOUR, 4]], failed_logins: [] }
        expect(metrics.loginBars(hours, "7d", HOUR).logins).toEqual(hours.logins)
        expect(metrics.loginBars(hours, "30d", HOUR)).toEqual({ size: DAY, logins: [[MIDNIGHT, 7]], failed_logins: [] })
        expect(metrics.loginBars({ logins: [[MIDNIGHT, 9]] }, "1y", DAY).logins).toEqual([[MIDNIGHT, 9]])
    })
})

describe("hour heatmap", () => {
    it("lays hourly counts out as days × hours", () => {
        const now = MIDNIGHT + 13 * HOUR + 600
        const points = [
            [MIDNIGHT - DAY + 9 * HOUR, 4], // Yesterday 09:00
            [MIDNIGHT - DAY + 9 * HOUR + 1800, 1], // Same hour
            [MIDNIGHT + 8 * HOUR, 0], // Today 08:00, read but no login
            [MIDNIGHT + 13 * HOUR, 2], // The current hour
            [MIDNIGHT - 5 * DAY, 7], // Before the window
        ]
        const { rows, max, total } = metrics.hourMatrix(points, 3, now)
        expect(rows.map((row) => row.start)).toEqual([MIDNIGHT - 2 * DAY, MIDNIGHT - DAY, MIDNIGHT])
        expect(rows[1].cells[9]).toBe(5)
        expect(rows[1].cells[10]).toBeNull()
        expect(rows[2].cells[8]).toBe(0)
        expect(rows[2].cells[13]).toBe(2)
        expect(rows[2].future[13]).toBe(false)
        expect(rows[2].future[14]).toBe(true)
        expect(rows[0].future).toBeUndefined()
        expect([max, total, rows[1].total]).toEqual([5, 7, 5])
    })
})

describe("collection status", () => {
    const base = { enabled: true, fleet_monitored: true, has_authkey: true, last_attempt: 200, last_success: 200 }

    it("reports the first thing in the way, worst first", () => {
        const { collectionStatus } = metrics
        expect(collectionStatus(null).code).toBe("unknown")
        expect(collectionStatus({ ...base, enabled: false, fleet_monitored: false }).code).toBe("off")
        expect(collectionStatus({ ...base, fleet_monitored: false }).code).toBe("fleet")
        expect(collectionStatus({ ...base, has_authkey: false }).code).toBe("authkey")
        expect(collectionStatus({ ...base, last_attempt: null, last_success: null }).code).toBe("waiting")
        expect(collectionStatus({ ...base, last_success: 100, last_error: "Statistics: Server unreachable" }))
            .toEqual({ code: "failed", error: "Statistics: Server unreachable", since: 100 })
        expect(collectionStatus({ ...base, last_success: null }).code).toBe("failed")
        expect(collectionStatus({ ...base, last_error: "Logins: Forbidden" })).toEqual({ code: "partial", error: "Logins: Forbidden" })
        expect(collectionStatus(base).code).toBe("ok")
    })

    it("computes ratios", () => {
        expect(metrics.ratio(2923792, 4291)).toBe(681.4)
        expect(metrics.ratio(3, 0)).toBeNull()
        expect(metrics.ratio(null, 3)).toBeNull()
    })
})
