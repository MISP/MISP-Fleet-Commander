<template>
    <figure class="heatmap">
        <figcaption class="chart-head">
            <span class="chart-title">{{ title }}</span>
            <span v-if="subtitle" class="chart-subtitle">{{ subtitle }}</span>
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

        <div ref="plot" class="heatmap-plot" :style="{ height: `${svgHeight}px` }">
            <svg
                v-if="width > 0"
                :width="width"
                :height="svgHeight"
                class="heatmap-svg"
                role="img"
                :aria-label="ariaLabel"
                tabindex="0"
                @pointerleave="active = null"
                @blur="active = null"
                @focus="onFocus"
                @keydown="onKey"
            >
                <g aria-hidden="true">
                    <text
                        v-for="hour in hourLabels"
                        :key="`h${hour}`"
                        :x="cellX(hour) + cellWidth / 2"
                        :y="HEADER - 5"
                        class="tick-label"
                        text-anchor="middle"
                    >{{ String(hour).padStart(2, "0") }}</text>
                    <g v-for="(row, rowIndex) in matrix.rows" :key="row.start">
                        <text :x="LABEL_WIDTH - 8" :y="cellY(rowIndex) + CELL / 2" class="tick-label" text-anchor="end" dominant-baseline="middle">{{ dayLabel(row.start) }}</text>
                        <template v-for="(value, hour) in row.cells">
                            <rect
                                v-if="!(row.future && row.future[hour])"
                                :key="`${row.start}-${hour}`"
                                :x="cellX(hour)"
                                :y="cellY(rowIndex)"
                                :width="cellWidth"
                                :height="CELL"
                                rx="2"
                                :class="['cell', { 'is-empty': value === null, 'is-active': isActive(rowIndex, hour) }]"
                                :fill="cellFill(value)"
                                @pointerenter="active = { row: rowIndex, hour }"
                            />
                        </template>
                    </g>
                </g>
            </svg>
            <div
                v-if="activeCell"
                class="chart-tooltip"
                :class="{ 'is-left': activeCell.x > width / 2 }"
                :style="{ left: `${activeCell.x}px`, top: `${activeCell.y}px` }"
                role="status"
            >
                <div class="tooltip-time">{{ activeCell.label }}</div>
                <strong class="tooltip-value">{{ activeCell.value }}</strong>
            </div>
        </div>

        <div class="heatmap-legend" aria-hidden="true">
            <span class="legend-item"><span class="swatch is-empty"></span>No sample</span>
            <span class="legend-item"><span class="swatch" :style="{ background: ZERO }"></span>None</span>
            <span class="legend-item">
                <span class="legend-ramp">
                    <span v-for="color in ramp" :key="color" class="ramp-step" :style="{ background: color }"></span>
                </span>
                up to {{ matrix.max }} {{ unitLabel(matrix.max) }} an hour
            </span>
        </div>

        <div v-if="showTable" class="chart-table-wrap">
            <table class="chart-table">
                <caption class="sr-only">{{ title }}, per day and hour</caption>
                <thead>
                    <tr>
                        <th scope="col">Day</th>
                        <th scope="col" class="num">Total</th>
                        <th v-for="hour in 24" :key="hour" scope="col" class="num">{{ String(hour - 1).padStart(2, "0") }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in tableRows" :key="row.start">
                        <th scope="row">{{ row.label }}</th>
                        <td class="num">{{ row.total }}</td>
                        <td v-for="(cell, hour) in row.cells" :key="hour" class="num">{{ cell }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </figure>
</template>

<script>
import { hourMatrix } from "@/helpers/metrics"
import { INK, SEQUENTIAL, widthMixin } from "./chartTheme"

const LABEL_WIDTH = 64
const HEADER = 18
const CELL = 13
const GAP = 2
const dayFormat = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric" })
const longDayFormat = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" })

export default {
    name: "HourHeatmap",
    mixins: [widthMixin],
    props: {
        title: { type: String, required: true },
        subtitle: { type: String, default: "" },
        // Hourly counts, [[ts, value]]
        points: { type: Array, required: true },
        now: { type: Number, required: true },
        days: { type: Number, default: 14 },
        // Singular and plural names of what is counted
        noun: { type: Array, default: () => ["login", "logins"] },
    },
    data() {
        return {
            LABEL_WIDTH, HEADER, CELL, ZERO: INK.zero, ramp: SEQUENTIAL, active: null, showTable: false,
        }
    },
    computed: {
        matrix() {
            return hourMatrix(this.points, this.days, this.now)
        },
        svgHeight() {
            return HEADER + this.matrix.rows.length * (CELL + GAP)
        },
        cellWidth() {
            return Math.max(4, (this.width - LABEL_WIDTH) / 24 - GAP)
        },
        hourLabels() {
            const step = this.cellWidth >= 22 ? 2 : (this.cellWidth >= 12 ? 3 : 6)
            return Array.from({ length: 24 / step }, (_, index) => index * step)
        },
        activeCell() {
            if (!this.active) {
                return null
            }
            const row = this.matrix.rows[this.active.row]
            if (!row) {
                return null
            }
            const value = row.cells[this.active.hour]
            const start = new Date(row.start * 1000)
            start.setHours(this.active.hour)
            const hour = String(this.active.hour).padStart(2, "0")
            const next = String((this.active.hour + 1) % 24).padStart(2, "0")
            return {
                x: this.cellX(this.active.hour) + this.cellWidth / 2,
                y: this.cellY(this.active.row) + CELL + 4,
                label: `${longDayFormat.format(start)}, ${hour}:00–${next}:00`,
                value: value === null ? "No sample" : `${value} ${this.unitLabel(value)}`,
            }
        },
        ariaLabel() {
            const busiest = this.busiest
            const total = `${this.matrix.total} ${this.unitLabel(this.matrix.total)} over the last ${this.days} days`
            return busiest ? `${this.title}: ${total}, most at ${busiest}. Use the arrow keys to read each hour` : `${this.title}: ${total}`
        },
        busiest() {
            let best = null
            this.matrix.rows.forEach((row) => row.cells.forEach((value, hour) => {
                if (value && (!best || value > best.value)) {
                    best = { value, start: row.start, hour }
                }
            }))
            if (!best) {
                return ""
            }
            return `${dayFormat.format(new Date(best.start * 1000))} ${String(best.hour).padStart(2, "0")}:00 (${best.value})`
        },
        tableRows() {
            return [...this.matrix.rows].reverse().map((row) => ({
                start: row.start,
                label: longDayFormat.format(new Date(row.start * 1000)),
                total: row.total,
                cells: row.cells.map((value, hour) => (row.future && row.future[hour]) || value === null ? "–" : value),
            }))
        },
    },
    methods: {
        cellX(hour) {
            return LABEL_WIDTH + hour * (this.cellWidth + GAP)
        },
        cellY(row) {
            return HEADER + row * (CELL + GAP)
        },
        dayLabel(start) {
            return dayFormat.format(new Date(start * 1000))
        },
        unitLabel(value) {
            return value === 1 ? this.noun[0] : this.noun[1]
        },
        cellFill(value) {
            if (value === null) {
                return "#fff"
            }
            if (value === 0 || this.matrix.max === 0) {
                return INK.zero
            }
            // Square root: a few busy hours must not wash every other hour out
            const share = Math.sqrt(value / this.matrix.max)
            const index = Math.min(SEQUENTIAL.length - 1, Math.max(0, Math.ceil(share * SEQUENTIAL.length) - 1))
            return SEQUENTIAL[index]
        },
        isActive(row, hour) {
            return this.active !== null && this.active.row === row && this.active.hour === hour
        },
        onFocus() {
            if (!this.active) {
                const row = this.matrix.rows.length - 1
                const current = new Date(this.now * 1000).getHours()
                this.active = { row, hour: current }
            }
        },
        onKey(event) {
            if (!this.active) {
                this.onFocus()
            }
            const { row, hour } = this.active
            const last = this.matrix.rows.length - 1
            const moves = {
                ArrowLeft: { row, hour: Math.max(0, hour - 1) },
                ArrowRight: { row, hour: Math.min(23, hour + 1) },
                ArrowUp: { row: Math.max(0, row - 1), hour },
                ArrowDown: { row: Math.min(last, row + 1), hour },
            }
            if (event.key in moves) {
                event.preventDefault()
                this.active = moves[event.key]
            } else if (event.key === "Escape") {
                this.active = null
            }
        },
    },
}
</script>

<style scoped>
.heatmap {
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

.heatmap-plot {
    position: relative;
    width: 100%;
}

.heatmap-svg {
    display: block;
    overflow: visible;
    outline: none;
}

.heatmap-svg:focus-visible {
    box-shadow: 0 0 0 2px rgba(41, 120, 160, 0.35);
    border-radius: 4px;
}

.tick-label {
    fill: #7b838d;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.cell.is-empty {
    stroke: #e4e7ec;
    stroke-width: 1;
}

.cell.is-active {
    stroke: #212d40;
    stroke-width: 1.5;
}

.chart-tooltip {
    position: absolute;
    z-index: 2;
    transform: translateX(-50%);
    padding: 0.35rem 0.55rem;
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
    transform: translateX(calc(-100% + 1rem));
}

.tooltip-time {
    color: #6c757d;
}

.tooltip-value {
    color: #212d40;
    font-variant-numeric: tabular-nums;
}

.heatmap-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 1rem;
    margin-top: 0.4rem;
    padding-left: 64px;
    color: #6c757d;
    font-size: 0.76rem;
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    white-space: nowrap;
}

.swatch {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
}

.swatch.is-empty {
    border: 1px solid #e4e7ec;
    background: #fff;
}

.legend-ramp {
    display: inline-flex;
    gap: 2px;
}

.ramp-step {
    display: inline-block;
    width: 10px;
    height: 12px;
    border-radius: 2px;
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
    font-size: 0.75rem;
    border-collapse: collapse;
}

.chart-table th,
.chart-table td {
    padding: 0.2rem 0.4rem;
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

@media (max-width: 480px) {
    .heatmap-legend {
        padding-left: 0;
    }
}
</style>
