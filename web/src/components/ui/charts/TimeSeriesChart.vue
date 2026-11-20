<template>
    <figure class="ts-chart">
        <figcaption class="chart-head">
            <span class="chart-title">{{ title }}</span>
            <span v-if="subtitle" class="chart-subtitle">{{ subtitle }}</span>
            <slot name="badge"></slot>
            <button
                type="button"
                class="chart-table-toggle"
                :aria-pressed="showTable ? 'true' : 'false'"
                :title="showTable ? 'Hide the table' : 'Show the values as a table'"
                @click="showTable = !showTable"
            >
                <i class="fas fa-table" aria-hidden="true"></i>
                <span class="sr-only">{{ showTable ? "Hide the table" : "Show the values as a table" }}</span>
            </button>
        </figcaption>

        <ul v-if="series.length > 1" class="chart-legend">
            <li v-for="item in legend" :key="item.key" class="legend-item">
                <svg class="legend-key" width="14" height="10" aria-hidden="true">
                    <rect v-if="mode === 'bars'" x="2" y="1" width="10" height="8" rx="2" :fill="item.color" />
                    <line v-else x1="1" y1="5" x2="13" y2="5" :stroke="item.color" stroke-width="2" stroke-linecap="round" />
                </svg>
                <span class="legend-label">{{ item.label }}</span>
                <span v-if="item.value !== null" class="legend-value">{{ item.value }}</span>
            </li>
        </ul>

        <div ref="plot" class="chart-plot" :style="{ height: `${height}px` }">
            <svg
                v-if="width > 0"
                :width="width"
                :height="height"
                class="chart-svg"
                role="img"
                :aria-label="ariaLabel"
                tabindex="0"
                @pointermove="onPointer"
                @pointerleave="onLeave"
                @focus="onFocus"
                @blur="onLeave"
                @keydown="onKey"
            >
                <g class="chart-grid" aria-hidden="true">
                    <g v-for="tick in yTicks" :key="`y${tick.value}`">
                        <line :x1="margin.left" :x2="width - margin.right" :y1="tick.y" :y2="tick.y" :class="tick.base ? 'axis-line' : 'grid-line'" />
                        <text :x="margin.left - 6" :y="tick.y" class="tick-label" text-anchor="end" dominant-baseline="middle">{{ tick.label }}</text>
                    </g>
                    <text
                        v-for="tick in xTicks"
                        :key="`x${tick.time}`"
                        :x="tick.x"
                        :y="height - 6"
                        class="tick-label"
                        :text-anchor="tick.anchor"
                    >{{ tick.label }}</text>
                </g>

                <g v-if="thresholdMark" class="threshold" aria-hidden="true">
                    <rect
                        v-if="thresholdMark.zone"
                        :x="margin.left"
                        :y="thresholdMark.zone.y"
                        :width="Math.max(0, width - margin.left - margin.right)"
                        :height="thresholdMark.zone.height"
                        :class="['threshold-zone', `tone-${threshold.tone || 'warning'}`]"
                    />
                    <line :x1="margin.left" :x2="width - margin.right" :y1="thresholdMark.y" :y2="thresholdMark.y" class="threshold-line" />
                    <text
                        v-if="threshold.label"
                        :x="width - margin.right - 2"
                        :y="thresholdMark.labelY"
                        text-anchor="end"
                        class="threshold-label"
                    >{{ threshold.label }}</text>
                </g>

                <rect
                    v-if="active && mode === 'bars'"
                    :x="active.bandX"
                    :y="margin.top"
                    :width="active.bandWidth"
                    :height="plotBottom - margin.top"
                    class="hover-band"
                    aria-hidden="true"
                />

                <g v-if="mode === 'bars'" aria-hidden="true">
                    <path
                        v-for="bar in bars"
                        :key="bar.key"
                        :d="bar.d"
                        :fill="bar.color"
                        :class="{ 'is-partial': bar.partial }"
                    />
                </g>
                <g v-else aria-hidden="true">
                    <path v-for="band in bands" :key="band.key" :d="band.d" :fill="band.color" class="peak-band" />
                    <path v-for="path in lines" :key="path.key" :d="path.d" :stroke="path.color" class="series-line" />
                    <circle
                        v-for="dot in endDots"
                        :key="dot.key"
                        :cx="dot.x"
                        :cy="dot.y"
                        r="4"
                        :fill="dot.color"
                        class="series-dot"
                    />
                </g>

                <g v-if="active && mode !== 'bars'" aria-hidden="true">
                    <line :x1="active.x" :x2="active.x" :y1="margin.top" :y2="plotBottom" class="crosshair" />
                    <circle
                        v-for="dot in active.dots"
                        :key="dot.key"
                        :cx="active.x"
                        :cy="dot.y"
                        r="4"
                        :fill="dot.color"
                        class="series-dot"
                    />
                </g>
            </svg>

            <div
                v-if="active"
                class="chart-tooltip"
                :class="{ 'is-left': active.x > width / 2 }"
                :style="{ left: `${active.x}px` }"
                role="status"
            >
                <div class="tooltip-time">{{ active.label }}<span v-if="active.partial" class="tooltip-note"> · in progress</span></div>
                <div v-for="row in active.rows" :key="row.key" class="tooltip-row">
                    <svg width="12" height="8" aria-hidden="true">
                        <line x1="1" y1="4" x2="11" y2="4" :stroke="row.color" stroke-width="2" stroke-linecap="round" />
                    </svg>
                    <strong class="tooltip-value">{{ row.value }}</strong>
                    <span class="tooltip-label">{{ row.label }}</span>
                    <span v-if="row.peak" class="tooltip-peak">{{ row.spread }}</span>
                </div>
            </div>

            <p v-if="isEmpty" class="chart-empty">No sample over this range</p>
        </div>

        <div v-if="showTable" class="chart-table-wrap">
            <table class="chart-table">
                <caption class="sr-only">{{ title }}, newest first</caption>
                <thead>
                    <tr>
                        <th scope="col">Time</th>
                        <th v-for="item in series" :key="item.key" scope="col" class="num">{{ item.label }}</th>
                        <th v-for="item in seriesWithLows" :key="`${item.key}-low`" scope="col" class="num">{{ item.label }} (min)</th>
                        <th v-for="item in seriesWithPeaks" :key="`${item.key}-peak`" scope="col" class="num">{{ item.label }} (max)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in tableRows" :key="row.ts">
                        <th scope="row">{{ row.label }}</th>
                        <td v-for="cell in row.cells" :key="cell.key" class="num">{{ cell.value }}</td>
                    </tr>
                    <tr v-if="tableRows.length === 0">
                        <td :colspan="1 + series.length + seriesWithLows.length + seriesWithPeaks.length" class="chart-table-empty">No sample over this range</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </figure>
</template>

<script>
import { area, line, scaleLinear, scaleTime, timeDay, timeFormat, timeHour, timeMonth, timeYear } from "d3"
import { axisTicks, bytesUnit, formatBucket, formatTick, formatValue, segments } from "@/helpers/metrics"
import { SERIES_COLORS, widthMixin } from "./chartTheme"

const formatClock = timeFormat("%H:%M")
const formatWeekday = timeFormat("%a %-d")
const formatDate = timeFormat("%-d %b")
const formatMonth = timeFormat("%b")
const formatYear = timeFormat("%Y")
const BAR_MAX = 24
// Closest two time labels may be: d3's day ticks restart on the 1st, so the 31st and the 1st can meet
const TICK_GAP = 56
const RADIUS = 4

/** A bar with a rounded data end (its top) and a square base */
function barPath(x, y, width, height, rounded) {
    const r = rounded ? Math.min(RADIUS, width / 2, height) : 0
    if (r <= 0) {
        return `M${x},${y}h${width}v${height}h${-width}Z`
    }
    return `M${x},${y + height}V${y + r}A${r},${r} 0 0 1 ${x + r},${y}H${x + width - r}`
        + `A${r},${r} 0 0 1 ${x + width},${y + r}V${y + height}Z`
}

export default {
    name: "TimeSeriesChart",
    mixins: [widthMixin],
    props: {
        title: { type: String, required: true },
        subtitle: { type: String, default: "" },
        // [{key, label, points: [[ts, value]], peaks?: [[ts, value]], lows?: [[ts, value]], band?: false, color?}].
        // The band runs from each point (or its low, when given) to its peak. `band: false` keeps it out of the
        // drawing (tooltip and table only), when several bands would pile up
        series: { type: Array, required: true },
        // `line`, or `bars` (stacked in the order of `series`)
        mode: { type: String, default: "line" },
        unit: { type: String, default: "count" },
        from: { type: Number, required: true },
        to: { type: Number, required: true },
        // Seconds between points: the sampling interval or the bucket size
        interval: { type: Number, required: true },
        // Start of the bucket still being filled, if any
        partialSince: { type: Number, default: null },
        // false: the value axis hugs the data instead of starting at zero
        zero: { type: Boolean, default: true },
        yMax: { type: Number, default: null },
        // [min, max] the value axis spans, whatever the data: charts that share one axis get the same
        yDomain: { type: Array, default: null },
        height: { type: Number, default: 168 },
        // A level the values are held to: `{value, label?, description?, side?, tone?}`. Drawn as a dashed line, with
        // `label` beside it (charts sharing a legend leave it out and give `description` to screen readers); `side`
        // (`above` or `below`) tints the part of the plot where values miss it, in the health tone `tone` (warning by
        // default)
        threshold: { type: Object, default: null },
    },
    data() {
        return {
            activeTs: null,
            showTable: false,
        }
    },
    computed: {
        coloured() {
            return this.series.map((item, index) => ({
                ...item,
                color: item.color || SERIES_COLORS[index % SERIES_COLORS.length],
                points: item.points || [],
                peaks: item.peaks || [],
                lows: item.lows || [],
                byTs: new Map((item.points || []).map(([ts, value]) => [ts, value])),
                peakByTs: new Map((item.peaks || []).map(([ts, value]) => [ts, value])),
                lowByTs: new Map((item.lows || []).map(([ts, value]) => [ts, value])),
            }))
        },
        seriesWithPeaks() {
            return this.coloured.filter((item) => item.peaks.length > 0)
        },
        seriesWithLows() {
            return this.coloured.filter((item) => item.lows.length > 0)
        },
        thresholdValue() {
            const value = this.threshold ? this.threshold.value : null
            return typeof value === "number" && Number.isFinite(value) ? value : null
        },
        isEmpty() {
            return this.coloured.every((item) => item.points.length === 0)
        },
        stamps() {
            const all = new Set()
            this.coloured.forEach((item) => item.points.forEach(([ts]) => all.add(ts)))
            return [...all].sort((a, b) => a - b)
        },
        stacks() {
            // Bars: the stacked total of each bucket
            return this.stamps.map((ts) => this.coloured.reduce((total, item) => total + Math.max(0, item.byTs.get(ts) || 0), 0))
        },
        extent() {
            let min = Infinity
            let max = -Infinity
            const visit = (value) => {
                if (typeof value === "number" && Number.isFinite(value)) {
                    min = Math.min(min, value)
                    max = Math.max(max, value)
                }
            }
            if (this.mode === "bars") {
                this.stacks.forEach(visit)
            } else {
                this.coloured.forEach((item) => {
                    item.points.forEach(([, value]) => visit(value))
                    item.peaks.forEach(([, value]) => visit(value))
                    item.lows.forEach(([, value]) => visit(value))
                })
            }
            if (this.thresholdValue !== null) {
                visit(this.thresholdValue)
            }
            if (min === Infinity) {
                return [0, 1]
            }
            return [min, max]
        },
        bytes() {
            return this.unit === "bytes" ? bytesUnit(this.extent[1]) : null
        },
        yScale() {
            let [min, max] = this.extent
            if (this.yDomain) {
                [min, max] = this.yDomain
            } else if (this.zero || this.mode === "bars") {
                min = Math.min(0, min)
            } else {
                const pad = (max - min) * 0.15 || Math.abs(max) * 0.05 || 1
                min = Math.max(0, min - pad)
                max += pad
            }
            if (this.yMax !== null) {
                max = Math.max(max, this.yMax)
            }
            if (max <= min) {
                max = min + 1
            }
            // Byte axes tick on round values of their unit (2 GB, not 2.15 GB)
            const factor = this.bytes ? this.bytes.factor : 1
            const scaled = scaleLinear().domain([min / factor, max / factor]).nice(4)
            const [lo, hi] = scaled.domain()
            return scaleLinear().domain([lo * factor, hi * factor]).range([this.plotBottom, this.margin.top])
        },
        yTickValues() {
            const factor = this.bytes ? this.bytes.factor : 1
            const [lo, hi] = this.yScale.domain()
            return axisTicks(scaleLinear().domain([lo / factor, hi / factor]).ticks(4), this.unit).map((value) => value * factor)
        },
        margin() {
            const labels = this.yTickValuesForMargin.map((value) => formatTick(value, this.unit, this.bytes))
            const longest = labels.reduce((size, label) => Math.max(size, label.length), 1)
            return { top: 10, right: 10, bottom: 24, left: Math.ceil(longest * 6.4) + 12 }
        },
        yTickValuesForMargin() {
            // The margin depends on the labels, the scale on the margin: estimate the labels from the domain alone
            const factor = this.bytes ? this.bytes.factor : 1
            if (this.yDomain) {
                const ticks = scaleLinear().domain([this.yDomain[0] / factor, this.yDomain[1] / factor]).nice(4).ticks(4)
                return axisTicks(ticks, this.unit).map((value) => value * factor)
            }
            const [min, max] = this.extent
            const top = this.yMax !== null ? Math.max(max, this.yMax) : max
            const ticks = scaleLinear().domain([Math.min(0, min) / factor, top / factor]).nice(4).ticks(4)
            return axisTicks(ticks, this.unit).map((value) => value * factor)
        },
        plotBottom() {
            return this.height - 24
        },
        domainEnd() {
            const lastStamp = this.stamps.length > 0 ? this.stamps[this.stamps.length - 1] : this.to
            return this.mode === "bars" ? Math.max(this.to, lastStamp + this.interval) : this.to
        },
        domainStart() {
            if (this.mode !== "bars") {
                return this.from
            }
            const first = this.stamps.length > 0 ? this.stamps[0] : this.from
            return Math.min(this.from - (this.from % this.interval), first)
        },
        xScale() {
            return scaleTime()
                .domain([new Date(this.domainStart * 1000), new Date(this.domainEnd * 1000)])
                .range([this.margin.left, Math.max(this.margin.left + 1, this.width - this.margin.right)])
        },
        yTicks() {
            return this.yTickValues.map((value) => ({
                value,
                y: Math.round(this.yScale(value)) + 0.5,
                label: formatTick(value, this.unit, this.bytes),
                base: value === this.yScale.domain()[0],
            }))
        },
        xTicks() {
            const plotWidth = this.width - this.margin.left - this.margin.right
            const count = Math.max(2, Math.floor(plotWidth / 92))
            const span = this.domainEnd - this.domainStart
            const kept = []
            this.xScale.ticks(count).forEach((date) => {
                let label
                let boundary = false
                if (timeHour(date) < date || timeDay(date) < date) {
                    label = formatClock(date)
                } else if (timeMonth(date) < date) {
                    label = span <= 10 * 86400 ? formatWeekday(date) : formatDate(date)
                } else if (timeYear(date) < date) {
                    label = formatMonth(date)
                    boundary = true
                } else {
                    label = formatYear(date)
                    boundary = true
                }
                const tick = { time: date.getTime(), x: this.xScale(date), label, boundary }
                const previous = kept[kept.length - 1]
                if (previous && tick.x - previous.x < TICK_GAP) {
                    if (tick.boundary && !previous.boundary) {
                        kept[kept.length - 1] = tick
                    }
                    return
                }
                kept.push(tick)
            })
            return kept.map((tick, index) => {
                let anchor = "middle"
                if (index === 0 && tick.x - this.margin.left < 24) anchor = "start"
                if (index === kept.length - 1 && this.width - this.margin.right - tick.x < 24) anchor = "end"
                return { ...tick, anchor }
            })
        },
        gapLimit() {
            return this.interval * 2.5
        },
        lines() {
            const draw = line().x((point) => this.xScale(new Date(point[0] * 1000))).y((point) => this.yScale(point[1]))
            const paths = []
            this.coloured.forEach((item) => {
                segments(item.points, this.gapLimit).forEach((segment, index) => {
                    // A lone sample between gaps draws as a dot, not an invisible zero-length line
                    const shape = segment.length === 1 ? [segment[0], [segment[0][0] + this.interval / 4, segment[0][1]]] : segment
                    paths.push({ key: `${item.key}-${index}`, color: item.color, d: draw(shape) })
                })
            })
            return paths
        },
        bands() {
            const draw = area()
                .x((point) => this.xScale(new Date(point[0] * 1000)))
                .y0((point) => this.yScale(point[1]))
                .y1((point) => this.yScale(point[2]))
            const result = []
            this.coloured.forEach((item) => {
                if (item.peaks.length === 0 || item.band === false) {
                    return
                }
                const withPeaks = item.points
                    .filter(([ts]) => item.peakByTs.has(ts))
                    .map(([ts, value]) => [ts, item.lowByTs.has(ts) ? item.lowByTs.get(ts) : value, item.peakByTs.get(ts)])
                segments(withPeaks, this.gapLimit).forEach((segment, index) => {
                    if (segment.length > 1) {
                        result.push({ key: `${item.key}-${index}`, color: item.color, d: draw(segment) })
                    }
                })
            })
            return result
        },
        endDots() {
            return this.coloured
                .filter((item) => item.points.length > 0)
                .map((item) => {
                    const [ts, value] = item.points[item.points.length - 1]
                    return { key: item.key, color: item.color, x: this.xScale(new Date(ts * 1000)), y: this.yScale(value) }
                })
        },
        thresholdMark() {
            if (this.thresholdValue === null || this.width <= 0) {
                return null
            }
            const y = Math.round(this.yScale(this.thresholdValue)) + 0.5
            let zone = null
            if (this.threshold.side === "above" && y > this.margin.top) {
                zone = { y: this.margin.top, height: y - this.margin.top }
            } else if (this.threshold.side === "below" && y < this.plotBottom) {
                zone = { y, height: this.plotBottom - y }
            }
            // The label sits above the line, or under it when the line runs along the top
            const labelY = y - this.margin.top > 14 ? y - 4 : y + 12
            return { y, zone, labelY }
        },
        bars() {
            const result = []
            const base = this.yScale(0)
            this.stamps.forEach((ts) => {
                const x0 = this.xScale(new Date(ts * 1000))
                const x1 = this.xScale(new Date((ts + this.interval) * 1000))
                const slot = Math.max(0, x1 - x0)
                const gap = slot >= 8 ? 2 : slot >= 4 ? 1 : 0
                const width = Math.max(1, Math.min(BAR_MAX, slot - gap))
                const x = x0 + (slot - width) / 2
                const partial = this.partialSince !== null && ts >= this.partialSince
                const parts = this.coloured
                    .map((item) => ({ item, value: item.byTs.get(ts) || 0 }))
                    .filter((part) => part.value > 0)
                let top = base
                parts.forEach((part, index) => {
                    let height = base - this.yScale(part.value)
                    let y = top - height
                    // The 2px surface gap between stacked segments, taken from the upper one
                    if (index > 0 && height > 3) {
                        height -= 2
                    }
                    if (height < 1) {
                        height = 1
                        y = top - 1
                    }
                    result.push({
                        key: `${ts}-${part.item.key}`,
                        color: part.item.color,
                        partial,
                        d: barPath(x, y, width, height, index === parts.length - 1 && width >= 6),
                    })
                    top = y
                })
            })
            return result
        },
        active() {
            if (this.activeTs === null) {
                return null
            }
            const ts = this.activeTs
            const x = this.mode === "bars"
                ? this.xScale(new Date((ts + this.interval / 2) * 1000))
                : this.xScale(new Date(ts * 1000))
            const x0 = this.xScale(new Date(ts * 1000))
            const x1 = this.xScale(new Date((ts + this.interval) * 1000))
            return {
                x,
                bandX: x0,
                bandWidth: Math.max(1, x1 - x0),
                label: formatBucket(ts, this.mode === "bars" || this.interval >= 3600 ? this.interval : 0),
                partial: this.partialSince !== null && ts >= this.partialSince,
                rows: this.coloured.map((item) => ({
                    key: item.key,
                    label: item.label,
                    color: item.color,
                    value: item.byTs.has(ts) ? formatValue(item.byTs.get(ts), this.unit) : "no sample",
                    peak: item.peakByTs.has(ts) ? formatValue(item.peakByTs.get(ts), this.unit) : null,
                    spread: !item.peakByTs.has(ts) ? null
                        : item.lowByTs.has(ts)
                            ? `min ${formatValue(item.lowByTs.get(ts), this.unit)} · max ${formatValue(item.peakByTs.get(ts), this.unit)}`
                            : `max ${formatValue(item.peakByTs.get(ts), this.unit)}`,
                })),
                dots: this.coloured
                    .filter((item) => item.byTs.has(ts))
                    .map((item) => ({ key: item.key, color: item.color, y: this.yScale(item.byTs.get(ts)) })),
            }
        },
        legend() {
            return this.coloured.map((item) => {
                const last = item.points[item.points.length - 1]
                return {
                    key: item.key,
                    label: item.label,
                    color: item.color,
                    value: this.mode === "bars" || !last ? null : formatValue(last[1], this.unit),
                }
            })
        },
        ariaLabel() {
            if (this.isEmpty) {
                return `${this.title}: no sample over this range`
            }
            const latest = this.coloured
                .filter((item) => item.points.length > 0)
                .map((item) => `${item.label} ${formatValue(item.points[item.points.length - 1][1], this.unit)}`)
            const said = this.threshold && (this.threshold.description || this.threshold.label)
            const level = this.thresholdValue !== null && said ? ` ${said}.` : ""
            return `${this.title}. Latest: ${latest.join(", ")}.${level} Use the arrow keys to read the values`
        },
        tableRows() {
            if (!this.showTable) {
                return []
            }
            const size = this.mode === "bars" || this.interval >= 3600 ? this.interval : 0
            return [...this.stamps].reverse().map((ts) => ({
                ts,
                label: formatBucket(ts, size),
                cells: [
                    ...this.coloured.map((item) => ({
                        key: item.key,
                        value: item.byTs.has(ts) ? formatValue(item.byTs.get(ts), this.unit) : "–",
                    })),
                    ...this.seriesWithLows.map((item) => ({
                        key: `${item.key}-low`,
                        value: item.lowByTs.has(ts) ? formatValue(item.lowByTs.get(ts), this.unit) : "–",
                    })),
                    ...this.seriesWithPeaks.map((item) => ({
                        key: `${item.key}-peak`,
                        value: item.peakByTs.has(ts) ? formatValue(item.peakByTs.get(ts), this.unit) : "–",
                    })),
                ],
            }))
        },
    },
    methods: {
        nearestStamp(time) {
            const stamps = this.stamps
            if (stamps.length === 0) {
                return null
            }
            if (this.mode === "bars") {
                // The bucket under the pointer, else the closest one
                const inside = stamps.find((ts) => time >= ts && time < ts + this.interval)
                if (inside !== undefined) {
                    return inside
                }
            }
            let best = stamps[0]
            stamps.forEach((ts) => {
                const reference = this.mode === "bars" ? ts + this.interval / 2 : ts
                const bestReference = this.mode === "bars" ? best + this.interval / 2 : best
                if (Math.abs(reference - time) < Math.abs(bestReference - time)) {
                    best = ts
                }
            })
            return best
        },
        onPointer(event) {
            const box = event.currentTarget.getBoundingClientRect()
            const x = event.clientX - box.left
            if (x < this.margin.left - 4 || x > this.width - this.margin.right + 4) {
                this.activeTs = null
                return
            }
            this.activeTs = this.nearestStamp(this.xScale.invert(x).getTime() / 1000)
        },
        onLeave() {
            this.activeTs = null
        },
        onFocus() {
            if (this.stamps.length > 0) {
                this.activeTs = this.stamps[this.stamps.length - 1]
            }
        },
        onKey(event) {
            const stamps = this.stamps
            if (stamps.length === 0) {
                return
            }
            const index = this.activeTs === null ? stamps.length - 1 : stamps.indexOf(this.activeTs)
            const moves = {
                ArrowLeft: Math.max(0, index - 1),
                ArrowRight: Math.min(stamps.length - 1, index + 1),
                Home: 0,
                End: stamps.length - 1,
            }
            if (event.key in moves) {
                event.preventDefault()
                this.activeTs = stamps[moves[event.key]]
            } else if (event.key === "Escape") {
                this.activeTs = null
            }
        },
    },
}
</script>

<style scoped>
.ts-chart {
    margin: 0;
    min-width: 0;
}

.chart-head {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.15rem 0.5rem;
    margin-bottom: 0.2rem;
}

.chart-title {
    font-weight: 600;
    font-size: 0.875rem;
    color: #212d40;
}

.chart-subtitle {
    color: #6c757d;
    font-size: 0.78rem;
}

.chart-table-toggle {
    margin-left: auto;
    padding: 0.05rem 0.35rem;
    border: 1px solid transparent;
    border-radius: 4px;
    background: none;
    color: #8a929c;
    font-size: 0.78rem;
    line-height: 1.4;
}

.chart-table-toggle:hover,
.chart-table-toggle:focus-visible {
    color: #2978a0;
    border-color: #d5dbe3;
}

.chart-table-toggle[aria-pressed="true"] {
    color: #2978a0;
    background: #eef3f9;
}

.chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.1rem 0.9rem;
    margin: 0 0 0.15rem;
    padding: 0;
    list-style: none;
    font-size: 0.78rem;
    color: #52514e;
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    white-space: nowrap;
}

.legend-value {
    color: #212d40;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.chart-plot {
    position: relative;
    width: 100%;
}

.chart-svg {
    display: block;
    overflow: visible;
    outline: none;
    touch-action: pan-y;
}

.chart-svg:focus-visible {
    box-shadow: 0 0 0 2px rgba(41, 120, 160, 0.35);
    border-radius: 4px;
}

.grid-line {
    stroke: #eceef1;
    stroke-width: 1;
    shape-rendering: crispEdges;
}

.axis-line {
    stroke: #c3c8d0;
    stroke-width: 1;
    shape-rendering: crispEdges;
}

.tick-label {
    fill: #7b838d;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.series-line {
    fill: none;
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
}

.peak-band {
    opacity: 0.13;
}

.threshold-zone {
    fill: var(--health-warning);
    opacity: 0.08;
}

.threshold-zone.tone-critical {
    fill: var(--health-critical);
    opacity: 0.06;
}

.threshold-zone.tone-info {
    fill: var(--health-info);
    opacity: 0.07;
}

.threshold-line {
    stroke: #52514e;
    stroke-width: 1;
    stroke-dasharray: 4 3;
    shape-rendering: crispEdges;
}

.threshold-label {
    fill: #52514e;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    paint-order: stroke;
    stroke: #fff;
    stroke-width: 3px;
    stroke-linejoin: round;
}

.series-dot {
    stroke: #fff;
    stroke-width: 2;
}

.crosshair {
    stroke: #9aa6b5;
    stroke-width: 1;
    shape-rendering: crispEdges;
}

.hover-band {
    fill: #eef3f9;
}

.is-partial {
    opacity: 0.45;
}

.chart-tooltip {
    position: absolute;
    top: 4px;
    z-index: 2;
    transform: translateX(14px);
    min-width: 9rem;
    padding: 0.4rem 0.55rem;
    border: 1px solid rgba(33, 45, 64, 0.12);
    border-radius: 6px;
    background: #fff;
    box-shadow: 0 4px 14px rgba(33, 45, 64, 0.12);
    font-size: 0.78rem;
    line-height: 1.45;
    pointer-events: none;
    white-space: nowrap;
}

.chart-tooltip.is-left {
    transform: translateX(calc(-100% - 14px));
}

.tooltip-time {
    margin-bottom: 0.15rem;
    color: #6c757d;
}

.tooltip-note {
    font-style: italic;
}

.tooltip-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.tooltip-value {
    color: #212d40;
    font-variant-numeric: tabular-nums;
}

.tooltip-label {
    color: #52514e;
}

.tooltip-peak {
    margin-left: auto;
    padding-left: 0.5rem;
    color: #6c757d;
    font-variant-numeric: tabular-nums;
}

.chart-empty {
    position: absolute;
    top: 40%;
    left: 0;
    right: 0;
    margin: 0;
    text-align: center;
    color: #8a929c;
    font-size: 0.8rem;
    pointer-events: none;
}

.chart-table-wrap {
    max-height: 15rem;
    margin-top: 0.4rem;
    overflow: auto;
    border: 1px solid #e4e7ec;
    border-radius: 4px;
}

.chart-table {
    width: 100%;
    font-size: 0.78rem;
    border-collapse: collapse;
}

.chart-table th,
.chart-table td {
    padding: 0.2rem 0.5rem;
    border-bottom: 1px solid #eef0f3;
    white-space: nowrap;
}

.chart-table thead th {
    position: sticky;
    top: 0;
    background: #f8f9fb;
    color: #52514e;
    font-weight: 600;
}

.chart-table tbody th {
    font-weight: 400;
    color: #52514e;
}

.chart-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.chart-table-empty {
    color: #8a929c;
    text-align: center;
}
</style>
