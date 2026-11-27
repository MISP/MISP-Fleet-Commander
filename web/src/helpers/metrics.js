// Shaping the stored usage metrics of a server or a fleet for the Usage tabs: ranges, value formats, series cut at
// gaps, login buckets, the hour × day heatmap, where the collection stands and the fleet's per-server rows. Pure
// functions: no Vue, no store, no d3

export const HOUR = 3600
export const DAY = 24 * HOUR

export const RANGES = [
    { key: "24h", label: "24 h", phrase: "the last 24 hours", seconds: DAY },
    { key: "7d", label: "7 d", phrase: "the last 7 days", seconds: 7 * DAY },
    { key: "30d", label: "30 d", phrase: "the last 30 days", seconds: 30 * DAY },
    { key: "90d", label: "90 d", phrase: "the last 90 days", seconds: 90 * DAY },
    { key: "1y", label: "1 y", phrase: "the last year", seconds: 365 * DAY },
]
export const DEFAULT_RANGE = "7d"

export function rangeOf(key) {
    return RANGES.find((range) => range.key === key) || RANGES.find((range) => range.key === DEFAULT_RANGE)
}

// MISP's statistics fields (the refresh snapshot, `/users/statistics`) behind the metrics read from them
export const SNAPSHOT_FIELDS = {
    events: "event_count",
    attributes: "attribute_count",
    objects: "object_count",
    event_reports: "eventreport_count",
    analyst_data: "analyst_data_count",
    correlations: "correlation_count",
    proposals: "proposal_count",
    users: "user_count",
    users_pgp: "user_count_pgp",
    orgs: "org_count",
    local_orgs: "local_org_count",
    contributing_orgs: "contributing_org_count",
}

function toNumber(value) {
    if (value === null || value === undefined || value === "" || typeof value === "boolean") {
        return null
    }
    const number = Number(value)
    return Number.isFinite(number) ? number : null
}

/** The latest values the regular refresh read, keyed like the metrics: what the tab shows without history */
export function snapshotValues(stats) {
    const values = {}
    if (!stats || typeof stats !== "object") {
        return values
    }
    Object.entries(SNAPSHOT_FIELDS).forEach(([key, field]) => {
        const number = toNumber(stats[field])
        if (number !== null) {
            values[key] = number
        }
    })
    return values
}

/* Formats ---------------------------------------------------------------------------------------------------------- */

const BYTE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
const MINUS = "−"
const grouped = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 })

/** The binary unit that suits a byte amount: MISP and Redis report sizes in powers of 1024 */
export function bytesUnit(bytes) {
    let index = 0
    let value = Math.abs(bytes || 0)
    while (value >= 1024 && index < BYTE_UNITS.length - 1) {
        value /= 1024
        index += 1
    }
    return { factor: 1024 ** index, suffix: BYTE_UNITS[index] }
}

function trimmed(value, decimals) {
    return Number(value.toFixed(decimals)).toString()
}

/** A value for reading: `4,291`, `2.9M`, `77.3%`, `4.78`, `8.7 GB`. `exact` keeps counts whole (`2,923,792`) */
export function formatValue(value, unit, { exact = false } = {}) {
    const number = toNumber(value)
    if (number === null) {
        return "–"
    }
    const sign = number < 0 ? MINUS : ""
    const size = Math.abs(number)
    switch (unit) {
    case "percent":
        return `${sign}${trimmed(size, 1)}%`
    case "load":
        return `${sign}${size.toFixed(2)}`
    case "bytes": {
        const { factor, suffix } = bytesUnit(size)
        const scaled = size / factor
        return `${sign}${trimmed(scaled, scaled < 10 && factor > 1 ? 1 : 0)} ${suffix}`
    }
    default:
        if (exact || size < 10000) {
            return `${sign}${grouped.format(size)}`
        }
        return `${sign}${compact.format(size)}`
    }
}

/** A change, always signed: `+1,204`, `−3`, `+120 MB`, `0` */
export function formatDelta(value, unit) {
    const number = toNumber(value)
    if (number === null) {
        return "–"
    }
    if (number === 0) {
        return "0"
    }
    const text = formatValue(Math.abs(number), unit)
    return `${number > 0 ? "+" : MINUS}${text}`
}

/** A relative change: `+0.4%`, `−12%`; empty when unknown or under 0.05% */
export function formatChangePct(pct) {
    const number = toNumber(pct)
    if (number === null || Math.abs(number) < 0.05) {
        return ""
    }
    const size = Math.abs(number)
    return `${number > 0 ? "+" : MINUS}${size < 10 ? trimmed(size, 1) : Math.round(size)}%`
}

/** An axis tick: as short as the axis allows (`10K`, `50%`, `2 GB` when `factor` comes from `bytesUnit`) */
export function formatTick(value, unit, bytes = null) {
    if (unit === "percent") {
        return `${trimmed(value, 1)}%`
    }
    if (unit === "bytes" && bytes) {
        return `${trimmed(value / bytes.factor, 2)} ${bytes.suffix}`
    }
    if (unit === "load") {
        return trimmed(value, 2)
    }
    return Math.abs(value) < 10000 ? grouped.format(value) : compact.format(value)
}

/** The axis ticks worth labelling: counts only take whole numbers (an axis up to 2 logins ticks 0, 1, 2, not 0, 0.5, 1,
 * 1.5, 2 shown as 0, 1, 1, 2, 2) */
export function axisTicks(ticks, unit) {
    return unit === "count" ? ticks.filter((value) => Number.isInteger(value)) : ticks
}

/** A duration given in seconds, as MISP's benchmarks report them: `340 ms`, `12.3 s`, `4 min 12 s`, `1.6 h` */
export function formatDuration(seconds) {
    const number = toNumber(seconds)
    if (number === null) {
        return "–"
    }
    if (number < 1) {
        return `${trimmed(number * 1000, number < 0.01 ? 1 : 0)} ms`
    }
    if (number < 60) {
        return `${trimmed(number, number < 10 ? 2 : 1)} s`
    }
    if (number < 3600) {
        const minutes = Math.floor(number / 60)
        const rest = Math.round(number - minutes * 60)
        return rest ? `${minutes} min ${rest} s` : `${minutes} min`
    }
    return `${trimmed(number / 3600, 1)} h`
}

const dayFormat = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" })
const utcDayFormat = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" })
const timeFormat = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" })

const shortDateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" })

/** A day, short: `18 Jul` */
export function formatShortDate(ts) {
    return shortDateFormat.format(new Date(ts * 1000))
}

/** How the change of the tiles is described: over the range, or since the first sample when the history starts
 * more than two days after the range does */
export function changePhrase(range, from, firstTs) {
    if (firstTs && firstTs - from > 2 * DAY) {
        return `since ${formatShortDate(firstTs)}`
    }
    return `over ${range.phrase}`
}

/** What the API requests chart counts: Fleet Commander's own requests are not usage, the collector leaves them out.
 * A narrow card wraps it between its phrases, not inside one */
export function apiRequestsSubtitle(tierPhrase) {
    return ["over the previous 24 hours", "Fleet Commander's own left out", tierPhrase].filter(Boolean)
        .map((phrase) => phrase.replace(/ /g, " ")).join(", ")
}

/** When a point was taken, for its bucket size: a sample `Tue 18 Nov, 14:20`, an hour `Tue 18 Nov, 14:00–15:00`,
 * a day `Tue 18 Nov` (days are UTC days, like the day roll-up) */
export function formatBucket(ts, size) {
    const start = new Date(ts * 1000)
    if (size >= DAY) {
        return utcDayFormat.format(start)
    }
    if (size >= HOUR) {
        const end = new Date((ts + size) * 1000)
        return `${dayFormat.format(start)}, ${timeFormat.format(start)}–${timeFormat.format(end)}`
    }
    return `${dayFormat.format(start)}, ${timeFormat.format(start)}`
}

/* Series ----------------------------------------------------------------------------------------------------------- */

/** First and last value of a series over the range, and the change between them; null with fewer than two points */
export function changeOver(points) {
    const values = (points || []).filter((point) => point && toNumber(point[1]) !== null)
    if (values.length < 2) {
        return null
    }
    const first = values[0][1]
    const last = values[values.length - 1][1]
    return {
        first,
        last,
        abs: last - first,
        pct: first === 0 ? null : ((last - first) / first) * 100,
    }
}

/** Highest value of a series (null when empty) */
export function maxOf(points) {
    let max = null
    ;(points || []).forEach((point) => {
        const value = toNumber(point && point[1])
        if (value !== null && (max === null || value > max)) {
            max = value
        }
    })
    return max
}

/** The series cut where samples are missing: a gap longer than `maxGap` seconds starts a new segment, so that a
 * line is not drawn across an outage */
export function segments(points, maxGap) {
    const result = []
    let current = []
    ;(points || []).forEach((point) => {
        if (current.length > 0 && point[0] - current[current.length - 1][0] > maxGap) {
            result.push(current)
            current = []
        }
        current.push(point)
    })
    if (current.length > 0) {
        result.push(current)
    }
    return result
}

/** A sparkline's worth of points: consecutive points averaged into at most `count` */
export function downsample(points, count = 48) {
    const list = (points || []).filter((point) => toNumber(point[1]) !== null)
    if (list.length <= count) {
        return list
    }
    const result = []
    const size = list.length / count
    for (let index = 0; index < count; index += 1) {
        const chunk = list.slice(Math.floor(index * size), Math.floor((index + 1) * size))
        if (chunk.length > 0) {
            const sum = chunk.reduce((total, point) => total + point[1], 0)
            result.push([chunk[chunk.length - 1][0], sum / chunk.length])
        }
    }
    return result
}

/** Points summed per bucket of `size` seconds (UTC), as [[bucket start, sum]] */
export function bucketSum(points, size) {
    const buckets = new Map()
    ;(points || []).forEach(([ts, value]) => {
        const number = toNumber(value)
        if (number === null) {
            return
        }
        const bucket = ts - (((ts % size) + size) % size)
        buckets.set(bucket, (buckets.get(bucket) || 0) + number)
    })
    return [...buckets.entries()].sort((a, b) => a[0] - b[0])
}

/** Bucket size of the login bars for a range: hours up to 7 days, days beyond */
export function loginBucketSize(rangeKey) {
    return ["24h", "7d"].includes(rangeKey) ? HOUR : DAY
}

/** The login series of an answer summed into the bars' buckets. `interval` is the answer's own bucket size */
export function loginBars(series, rangeKey, interval) {
    const size = loginBucketSize(rangeKey)
    const shape = (points) => (interval === size ? (points || []).map(([ts, value]) => [ts, value]) : bucketSum(points, size))
    return {
        size,
        logins: shape(series && series.logins),
        failed_logins: shape(series && series.failed_logins),
    }
}

/** Hourly counts laid out as days (rows, oldest first) × the 24 hours of the day, in the browser's time zone.
 * A cell is null when no sample covers that hour, and `future` past the current hour */
export function hourMatrix(points, days, now) {
    const today = new Date(now * 1000)
    today.setHours(0, 0, 0, 0)
    const rows = []
    const byDay = new Map()
    for (let index = days - 1; index >= 0; index -= 1) {
        const start = new Date(today)
        start.setDate(today.getDate() - index)
        const row = { start: Math.floor(start.getTime() / 1000), cells: new Array(24).fill(null), total: 0 }
        rows.push(row)
        byDay.set(start.toDateString(), row)
    }
    let max = 0
    let total = 0
    ;(points || []).forEach(([ts, value]) => {
        const number = toNumber(value)
        if (number === null) {
            return
        }
        const date = new Date(ts * 1000)
        const row = byDay.get(date.toDateString())
        if (!row) {
            return
        }
        const hour = date.getHours()
        row.cells[hour] = (row.cells[hour] || 0) + number
        row.total += number
        total += number
        max = Math.max(max, row.cells[hour])
    })
    const current = new Date(now * 1000)
    const last = rows[rows.length - 1]
    if (last) {
        last.future = last.cells.map((_, hour) => hour > current.getHours())
    }
    return { rows, max, total }
}

/* Collection ------------------------------------------------------------------------------------------------------- */

/** Where the collection of the server stands, from the answer's `state`, worst first:
 * `off` (monitoring disabled), `fleet` (fleet not monitored), `authkey` (no API key), `stalled` (the collection has
 * stopped running: workers down), `waiting` (no attempt yet), `failed` (the last attempt stored nothing), `partial`
 * (stored, some sources failed), `ok` */
export function collectionStatus(state) {
    if (!state) {
        return { code: "unknown" }
    }
    if (!state.enabled) {
        return { code: "off" }
    }
    if (!state.fleet_monitored) {
        return { code: "fleet" }
    }
    if (!state.has_authkey) {
        return { code: "authkey" }
    }
    if (state.collector && state.collector.stalled) {
        return { code: "stalled", lastRun: state.collector.last_run || null }
    }
    if (!state.last_attempt) {
        return { code: "waiting" }
    }
    if (!state.last_success || state.last_success < state.last_attempt) {
        return { code: "failed", error: state.last_error || "Nothing could be read", since: state.last_success }
    }
    if (state.last_error) {
        return { code: "partial", error: state.last_error }
    }
    return { code: "ok" }
}

/** How long ago, roughly: `1 min`, `23 min`, `5 h`, `3 days` */
export function agoText(seconds) {
    const minutes = Math.round(seconds / 60)
    if (minutes < 90) {
        return `${Math.max(1, minutes)} min`
    }
    const hours = Math.round(seconds / 3600)
    if (hours < 48) {
        return `${hours} h`
    }
    return `${Math.round(seconds / 86400)} days`
}

/** What the Usage tabs say once the usage collection has stopped running (`lastRun`: when it last ran, or null;
 * `now`: the answer's time). `past`: what the charts still show */
export function stalledNotice(lastRun, { now, isAdmin = false, past = "" } = {}) {
    const when = lastRun ? `It last ran ${agoText(now - lastRun)} ago` : "It has not run since MFC was started"
    const check = isAdmin
        ? "check that they are running"
        : "an administrator should check that they are running"
    return {
        level: "warning",
        icon: "fa-pause-circle",
        title: "Usage collection is not running.",
        text: `${when}: samples are collected by MFC's workers, ${check}.${past}`,
    }
}

/** `a / b` for reading (`681.4`), or null when it can't be computed */
export function ratio(a, b, decimals = 1) {
    const top = toNumber(a)
    const bottom = toNumber(b)
    if (top === null || bottom === null || bottom === 0) {
        return null
    }
    return Number((top / bottom).toFixed(decimals))
}

/* Fleet ------------------------------------------------------------------------------------------------------------ */

export const QUEUE_KEYS = ["queue_default", "queue_prio", "queue_email", "queue_cache", "queue_update"]

/** Several series added up point by point, as [[ts, sum]] over the timestamps of any of them */
export function sumSeries(seriesList) {
    const sums = new Map()
    ;(seriesList || []).forEach((points) => {
        ;(points || []).forEach(([ts, value]) => {
            const number = toNumber(value)
            if (number !== null) {
                sums.set(ts, (sums.get(ts) || 0) + number)
            }
        })
    })
    return [...sums.entries()].sort((a, b) => a[0] - b[0])
}

/** The last value of a series, or null */
export function lastValue(points) {
    const list = points || []
    return list.length > 0 ? toNumber(list[list.length - 1][1]) : null
}

/** How the collection of a fleet's servers stands: how many were read at their last collection, and the others by
 * reason (`failed`, `authkey`, `waiting`), each `{id, name, error}` */
export function fleetCollection(servers) {
    const result = { total: 0, reporting: 0, failed: [], authkey: [], waiting: [] }
    ;(servers || []).forEach((server) => {
        result.total += 1
        const status = collectionStatus(server.state)
        if (status.code === "ok" || status.code === "partial") {
            result.reporting += 1
        } else if (result[status.code]) {
            result[status.code].push({ id: server.id, name: server.name, error: status.error || "" })
        }
    })
    return result
}

/** "All 3 servers reporting", "2 of 3 servers reporting"; for one server, whether it is */
export function reportingText({ reporting, total }) {
    if (total === 1) {
        return reporting === 1 ? "The server is reporting" : "The server is not reporting"
    }
    return reporting === total ? `All ${total} servers reporting` : `${reporting} of ${total} servers reporting`
}

/** The server a fleet's Usage tab is limited to, from its page's `?server=<id>`; null for all of them */
export function usageServerOf(query) {
    const text = query && query.server
    return typeof text === "string" && /^[1-9]\d*$/.test(text) ? Number.parseInt(text, 10) : null
}

/** One row per server of a fleet answer, with the figures its comparison table shows. Values are null when unknown */
export function fleetServerRows(servers) {
    return (servers || []).map((server) => {
        const values = (server.latest && server.latest.values) || {}
        const value = (key) => toNumber(values[key])
        const queues = QUEUE_KEYS.map(value).filter((number) => number !== null)
        const sums = server.sums || {}
        const change = server.change || {}
        const peaks = server.peaks || {}
        return {
            id: server.id,
            name: server.name,
            status: collectionStatus(server.state),
            lastTs: server.latest ? server.latest.ts : null,
            since: server.since,
            logins: server.since === null || server.since === undefined ? null : toNumber(sums.logins) || 0,
            failedLogins: toNumber(sums.failed_logins) || 0,
            apiRequests: value("api_requests_24h"),
            load: value("load_1"),
            loadPeak: toNumber(peaks.load_1),
            memory: value("memory_used_pct"),
            disk: value("disk_used_pct"),
            dbSize: value("db_size_bytes"),
            dbChange: toNumber(change.db_size_bytes),
            events: value("events"),
            eventsChange: toNumber(change.events),
            jobs: queues.length > 0 ? queues.reduce((total, number) => total + number, 0) : null,
        }
    })
}

/** Rows sorted on `key`, unknown values last whatever the direction; names break ties */
export function sortRows(rows, key, descending = false) {
    const direction = descending ? -1 : 1
    return [...(rows || [])].sort((a, b) => {
        const left = a[key]
        const right = b[key]
        const leftMissing = left === null || left === undefined
        const rightMissing = right === null || right === undefined
        if (leftMissing || rightMissing) {
            if (leftMissing && rightMissing) {
                return String(a.name).localeCompare(String(b.name))
            }
            return leftMissing ? 1 : -1
        }
        const order = typeof left === "string" ? left.localeCompare(right, undefined, { sensitivity: "base" }) : left - right
        return order !== 0 ? order * direction : String(a.name).localeCompare(String(b.name))
    })
}
