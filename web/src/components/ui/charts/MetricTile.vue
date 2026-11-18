<template>
    <div class="metric-tile" :class="{ 'is-snapshot': !hasHistory }">
        <div class="tile-label" :title="label">
            <i v-if="icon" :class="['fas', 'fa-fw', icon]" aria-hidden="true"></i>
            <span class="tile-label-text">{{ label }}</span>
        </div>
        <div class="tile-value" :title="exactTitle">{{ shownValue }}</div>
        <div v-if="deltaText" class="tile-delta" :title="deltaTitle">
            <i v-if="deltaIcon" :class="['fas', deltaIcon]" aria-hidden="true"></i>
            {{ deltaText }}
        </div>
        <div v-if="note" class="tile-note">{{ note }}</div>
        <div v-show="hasHistory" ref="plot" class="tile-spark" :title="sparkTitle">
            <svg v-if="width > 0 && spark" :width="width" :height="SPARK_HEIGHT" aria-hidden="true">
                <path :d="spark.line" class="spark-line" />
                <circle :cx="spark.end.x" :cy="spark.end.y" r="3.5" class="spark-end" />
            </svg>
        </div>
    </div>
</template>

<script>
import { line, scaleLinear } from "d3"
import { changeOver, downsample, formatChangePct, formatDelta, formatValue, maxOf } from "@/helpers/metrics"
import { widthMixin } from "./chartTheme"

const SPARK_HEIGHT = 30

export default {
    name: "MetricTile",
    mixins: [widthMixin],
    props: {
        label: { type: String, required: true },
        icon: { type: String, default: "" },
        value: { type: Number, default: null },
        unit: { type: String, default: "count" },
        // `total` shows the change over the range, `gauge` the maximum
        kind: { type: String, default: "total" },
        // The metric over the range, [[ts, value]]; none: the tile only has the latest value
        points: { type: Array, default: null },
        // Gauges on hourly or daily buckets: each bucket's maximum (the points are averages)
        peaks: { type: Array, default: null },
        // The period of the points, as a phrase: `over the last 7 days`, `since 18 Jul`
        rangePhrase: { type: String, default: "" },
        note: { type: String, default: "" },
    },
    data() {
        return { SPARK_HEIGHT }
    },
    computed: {
        hasHistory() {
            return Array.isArray(this.points)
        },
        shownValue() {
            return formatValue(this.value, this.unit)
        },
        exactTitle() {
            if (this.value === null || this.unit !== "count") {
                return null
            }
            return formatValue(this.value, this.unit, { exact: true })
        },
        change() {
            return this.hasHistory && this.kind === "total" ? changeOver(this.points) : null
        },
        peak() {
            if (!this.hasHistory || this.kind !== "gauge") {
                return null
            }
            return maxOf(this.peaks && this.peaks.length > 0 ? this.peaks : this.points)
        },
        deltaText() {
            if (!this.hasHistory) {
                return ""
            }
            if (this.kind === "gauge") {
                return this.peak === null ? "" : `max ${formatValue(this.peak, this.unit)}`
            }
            if (this.change === null) {
                return "Not enough samples yet"
            }
            if (this.change.abs === 0) {
                return "No change"
            }
            const pct = formatChangePct(this.change.pct)
            return `${formatDelta(this.change.abs, this.unit)}${pct ? ` (${pct})` : ""}`
        },
        deltaIcon() {
            if (this.kind !== "total" || !this.change || this.change.abs === 0) {
                return ""
            }
            return this.change.abs > 0 ? "fa-arrow-up" : "fa-arrow-down"
        },
        deltaTitle() {
            if (this.kind === "gauge") {
                return this.peak === null ? null : `Highest value ${this.rangePhrase}`
            }
            if (!this.change) {
                return null
            }
            return `From ${formatValue(this.change.first, this.unit, { exact: true })} to `
                + `${formatValue(this.change.last, this.unit, { exact: true })} ${this.rangePhrase}`
        },
        sparkTitle() {
            return this.rangePhrase ? `${this.label} ${this.rangePhrase}` : null
        },
        spark() {
            const points = downsample(this.points || [], 48)
            if (points.length < 2) {
                return null
            }
            const values = points.map((point) => point[1])
            let min = Math.min(...values)
            let max = Math.max(...values)
            if (min === max) {
                min -= 1
                max += 1
            }
            const x = scaleLinear().domain([points[0][0], points[points.length - 1][0]]).range([4, this.width - 4])
            const y = scaleLinear().domain([min, max]).range([SPARK_HEIGHT - 4, 4])
            const last = points[points.length - 1]
            return {
                line: line().x((point) => x(point[0])).y((point) => y(point[1]))(points),
                end: { x: x(last[0]), y: y(last[1]) },
            }
        },
    },
}
</script>

<style scoped>
.metric-tile {
    display: flex;
    flex-direction: column;
    min-width: 0;
    padding: 0.6rem 0.75rem 0.45rem;
    border: 1px solid #e4e7ec;
    border-radius: 6px;
    background: #fff;
}

.metric-tile.is-snapshot {
    padding-bottom: 0.6rem;
}

.tile-label {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
    color: #52514e;
    font-size: 0.8rem;
}

.tile-label-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tile-label i {
    color: #8a929c;
    font-size: 0.85em;
}

.tile-value {
    margin-top: 0.1rem;
    color: #212d40;
    font-size: 1.45rem;
    font-weight: 600;
    line-height: 1.25;
    letter-spacing: -0.01em;
}

.tile-delta,
.tile-note {
    color: #6c757d;
    font-size: 0.76rem;
    line-height: 1.35;
    font-variant-numeric: tabular-nums;
}

.tile-delta i {
    font-size: 0.85em;
}

.tile-spark {
    height: 30px;
    margin-top: auto;
    padding-top: 0.3rem;
    box-sizing: content-box;
}

.tile-spark svg {
    display: block;
    overflow: visible;
}

.spark-line {
    fill: none;
    stroke: #9aa6b5;
    stroke-width: 1.5;
    stroke-linejoin: round;
    stroke-linecap: round;
}

.spark-end {
    fill: #2a78d6;
    stroke: #fff;
    stroke-width: 1.5;
}
</style>
