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

    it("keeps whole ticks on count axes", () => {
        const { axisTicks } = metrics
        expect(axisTicks([0, 0.5, 1, 1.5, 2], "count")).toEqual([0, 1, 2])
        expect(axisTicks([0, 10, 20], "count")).toEqual([0, 10, 20])
        expect(axisTicks([0, 0.5, 1, 1.5, 2], "load")).toEqual([0, 0.5, 1, 1.5, 2])
        expect(axisTicks([0, 0.5, 1], "percent")).toEqual([0, 0.5, 1])
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

    it("says that the API requests leave Fleet Commander's own out", () => {
        const { apiRequestsSubtitle } = metrics
        const spaced = (text) => text.replace(/ /g, " ")
        expect(spaced(apiRequestsSubtitle("hourly average")))
            .toBe("over the previous 24 hours, Fleet Commander's own left out, hourly average")
        expect(spaced(apiRequestsSubtitle(""))).toBe("over the previous 24 hours, Fleet Commander's own left out")
        // A line breaks only between the phrases
        expect(apiRequestsSubtitle("hourly average").split(" ")).toEqual(
            ["over the previous 24 hours,", "Fleet Commander's own left out,",
                "hourly average"])
    })

    it("draws the API requests by who made them when the range holds the split", () => {
        const { apiRequestsSeries } = metrics
        const total = [[100, 50], [200, 60]]
        const split = {
            api_requests_24h: total,
            api_requests_users_24h: [[200, 40]],
            api_requests_sync_24h: [[200, 20]],
            api_requests_unknown_24h: [[200, 0]],
        }
        const peaks = { api_requests_24h: [[200, 70]] }
        const drawn = apiRequestsSeries((key) => split[key], (key) => peaks[key] || [])
        // Unknown keys made no request: left out
        expect(drawn.map((item) => [item.key, item.label])).toEqual([
            ["api_requests_24h", "All"], ["api_requests_users_24h", "Users and tools"],
            ["api_requests_sync_24h", "Sync"],
        ])
        expect(drawn.every((item) => item.band === false && item.color)).toBe(true)
        expect(drawn[0].points).toEqual(total)
        expect(drawn[0].peaks).toEqual([[200, 70]])
        expect(new Set(drawn.map((item) => item.color)).size).toBe(3)
        split.api_requests_unknown_24h = [[200, 3]]
        expect(apiRequestsSeries((key) => split[key]).map((item) => item.label))
            .toEqual(["All", "Users and tools", "Sync", "Unknown keys"])
    })

    it("names the servers whose API requests are not split", () => {
        const { fleetServerRows, unsplitApiServers } = metrics
        const rows = fleetServerRows([
            { id: 1, name: "split", latest: { ts: 1, values: { api_requests_24h: 30, api_requests_users_24h: 0 } } },
            { id: 2, name: "misp-2.4", latest: { ts: 1, values: { api_requests_24h: 12 } } },
            { id: 3, name: "no sample", latest: null },
        ])
        expect(rows.map((row) => row.apiRequestsSplit)).toEqual([true, false, false])
        // A server without any API requests figure is not in the chart at all
        expect(unsplitApiServers(rows)).toEqual(["misp-2.4"])
        expect(unsplitApiServers(undefined)).toEqual([])
    })

    it("draws the API requests total alone without the split", () => {
        const { apiRequestsSeries } = metrics
        const total = [[100, 50]]
        const drawn = apiRequestsSeries((key) => (key === "api_requests_24h" ? total : null), () => [[100, 55]])
        expect(drawn).toEqual([{ key: "api_requests_24h", label: "Requests", points: total, peaks: [[100, 55]] }])
        expect(apiRequestsSeries(() => undefined)).toEqual(
            [{ key: "api_requests_24h", label: "Requests", points: [], peaks: [] }])
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

    it("says when the collection no longer runs, whatever the server's last sample", () => {
        const { collectionStatus } = metrics
        const stalled = { last_run: 1000, stalled: true }
        expect(collectionStatus({ ...base, collector: stalled })).toEqual({ code: "stalled", lastRun: 1000 })
        expect(collectionStatus({ ...base, last_attempt: null, collector: { last_run: null, stalled: true } }))
            .toEqual({ code: "stalled", lastRun: null })
        // What the user can act on comes first
        expect(collectionStatus({ ...base, enabled: false, collector: stalled }).code).toBe("off")
        expect(collectionStatus({ ...base, fleet_monitored: false, collector: stalled }).code).toBe("fleet")
        expect(collectionStatus({ ...base, has_authkey: false, collector: stalled }).code).toBe("authkey")
        expect(collectionStatus({ ...base, collector: { last_run: 1000, stalled: false } }).code).toBe("ok")
    })

    it("tells how long the collection has not run, and who can start it again", () => {
        const notice = metrics.stalledNotice(1000, { now: 1000 + 23 * 60, isAdmin: true })
        expect(notice).toEqual({
            level: "warning",
            icon: "fa-pause-circle",
            title: "Usage collection is not running.",
            text: "It last ran 23 min ago: samples are collected by MFC's workers, check that they are running.",
        })
        expect(metrics.stalledNotice(null, { now: 5000, past: " The charts show what was collected before." }).text)
            .toBe("It has not run since MFC was started: samples are collected by MFC's workers, an administrator "
                + "should check that they are running. The charts show what was collected before.")
        expect([20, 600, 5340, 5400, 3 * 3600, 47 * 3600, 3 * 86400].map(metrics.agoText))
            .toEqual(["1 min", "10 min", "89 min", "2 h", "3 h", "47 h", "3 days"])
    })

    it("computes ratios", () => {
        expect(metrics.ratio(2923792, 4291)).toBe(681.4)
        expect(metrics.ratio(3, 0)).toBeNull()
        expect(metrics.ratio(null, 3)).toBeNull()
    })
})

describe("fleet", () => {
    const state = { enabled: true, fleet_monitored: true, has_authkey: true, last_attempt: 200, last_success: 200 }
    const server = (id, name, extra = {}) => ({
        id, name, state, latest: null, sums: {}, change: {}, peaks: {}, since: null, ...extra,
    })

    it("adds series up point by point", () => {
        expect(metrics.sumSeries([[[10, 1], [20, 2]], [[20, 3], [30, "4"]], null, [[30, null]]]))
            .toEqual([[10, 1], [20, 5], [30, 4]])
        expect(metrics.sumSeries([])).toEqual([])
        expect(metrics.lastValue([[10, 1], [20, 5]])).toBe(5)
        expect(metrics.lastValue([])).toBeNull()
    })

    it("counts the servers reporting and lists the others by reason", () => {
        const collection = metrics.fleetCollection([
            server(1, "ok"),
            server(2, "partial", { state: { ...state, last_error: "Logins: Forbidden" } }),
            server(3, "down", { state: { ...state, last_success: 100, last_error: "Server unreachable" } }),
            server(4, "keyless", { state: { ...state, has_authkey: false } }),
            server(5, "new", { state: { ...state, last_attempt: null, last_success: null } }),
        ])
        expect(collection.total).toBe(5)
        expect(collection.reporting).toBe(2)
        expect(collection.failed).toEqual([{ id: 3, name: "down", error: "Server unreachable" }])
        expect(collection.authkey.map((item) => item.name)).toEqual(["keyless"])
        expect(collection.waiting.map((item) => item.name)).toEqual(["new"])
    })

    it("shapes one row per server", () => {
        const [row, empty] = metrics.fleetServerRows([
            server(1, "misp-a", {
                latest: {
                    ts: 500,
                    values: { load_1: 1.5, memory_used_pct: 64, disk_used_pct: "71.2", db_size_bytes: 1024, events: 40, queue_default: 2, queue_prio: 1 },
                },
                sums: { logins: 12, failed_logins: 2 },
                change: { events: 3, db_size_bytes: -24 },
                peaks: { load_1: 4 },
                since: 100,
            }),
            server(2, "misp-b"),
        ])
        expect(row).toMatchObject({
            id: 1, name: "misp-a", lastTs: 500, logins: 12, failedLogins: 2, apiRequests: null, load: 1.5, loadPeak: 4,
            memory: 64, disk: 71.2, dbSize: 1024, dbChange: -24, events: 40, eventsChange: 3, jobs: 3,
        })
        expect(row.status.code).toBe("ok")
        // No bucket in the range: logins unknown, not zero
        expect(empty).toMatchObject({ logins: null, failedLogins: 0, jobs: null, lastTs: null, dbChange: null })
    })

    it("sorts rows with unknown values last", () => {
        const rows = [
            { name: "c", load: 2 }, { name: "a", load: null }, { name: "B", load: 5 }, { name: "d", load: 2 },
        ]
        const names = (sorted) => sorted.map((row) => row.name)
        expect(names(metrics.sortRows(rows, "load", true))).toEqual(["B", "c", "d", "a"])
        expect(names(metrics.sortRows(rows, "load", false))).toEqual(["c", "d", "B", "a"])
        expect(names(metrics.sortRows(rows, "name"))).toEqual(["a", "B", "c", "d"])
        expect(names(metrics.sortRows(rows, "name", true))).toEqual(["d", "c", "B", "a"])
    })
})

describe("fleet Usage tab", () => {
    it("says how many servers report", () => {
        expect(metrics.reportingText({ reporting: 3, total: 3 })).toBe("All 3 servers reporting")
        expect(metrics.reportingText({ reporting: 2, total: 3 })).toBe("2 of 3 servers reporting")
        expect(metrics.reportingText({ reporting: 1, total: 1 })).toBe("The server is reporting")
        expect(metrics.reportingText({ reporting: 0, total: 1 })).toBe("The server is not reporting")
    })

    it("reads the server it is limited to from the page's address", () => {
        expect(metrics.usageServerOf({ tab: "usage", server: "12" })).toBe(12)
        expect(metrics.usageServerOf({ tab: "usage" })).toBe(null)
        expect(metrics.usageServerOf({ server: "" })).toBe(null)
        expect(metrics.usageServerOf({ server: "0" })).toBe(null)
        expect(metrics.usageServerOf({ server: "12abc" })).toBe(null)
        expect(metrics.usageServerOf({ server: ["12", "13"] })).toBe(null)
        expect(metrics.usageServerOf(undefined)).toBe(null)
    })
})
