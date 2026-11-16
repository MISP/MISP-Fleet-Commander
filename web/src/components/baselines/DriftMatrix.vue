<template>
    <div :class="['matrix-wrap', { 'is-refreshing': refreshing, 'is-compact': compact }]">
        <div class="matrix-scroll" tabindex="0" role="region" aria-label="Drift: rules against servers">
            <div ref="inner" class="matrix-inner">
                <table class="matrix" @mouseover="onPointer" @focusin="onPointer" @mouseleave="setHover(null)" @focusout="onFocusOut">
                    <thead>
                        <tr>
                            <th scope="col" class="col-rule">
                                <div class="matrix-corner">
                                    <span>Rule <span class="text-muted font-weight-normal">· expected</span></span>
                                    <span v-if="labels.domain" class="matrix-domain" :title="`Server names are shown without the domain they share: ${labels.domain}`">
                                        <i class="fas fa-globe mr-1" aria-hidden="true"></i>.{{ labels.domain }}
                                    </span>
                                </div>
                            </th>
                            <th
                                v-for="server in servers"
                                :key="server.id"
                                scope="col"
                                class="col-server"
                                :data-server="server.id"
                                :title="serverTitle(server)"
                            >
                                <div class="server-head">
                                    <router-link :to="{ name: 'servers.view', params: { server_id: server.id } }" class="server-name">
                                        {{ label(server) }}
                                    </router-link>
                                    <span v-if="server.unavailable" class="server-state is-unavailable">
                                        <i class="fas fa-plug-circle-xmark" aria-hidden="true"></i>
                                        <span :class="{ 'sr-only': compact }">{{ server.unavailable }}</span>
                                    </span>
                                    <span v-else-if="server.drift > 0" class="server-state is-drift">
                                        {{ server.drift }}<span :class="{ 'sr-only': compact }"> drifting</span>
                                    </span>
                                    <span v-else class="server-state is-ok">
                                        <i class="fas fa-check" aria-hidden="true"></i>
                                        <span :class="{ 'sr-only': compact }">In line</span>
                                    </span>
                                </div>
                            </th>
                            <th v-if="servers.length === 0" scope="col" class="col-server col-empty">No server in this fleet</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="rule in rules"
                            :id="`baseline-rule-${rule.id}`"
                            :key="rule.id"
                            :class="['rule-row', `sev-${rule.severity}`, { highlighted: rule.id === highlightRuleId }]"
                        >
                            <th scope="row" class="col-rule">
                                <div class="rule-cell">
                                    <i :class="['rule-type', typeMeta(rule).icon]" :title="typeMeta(rule).label" aria-hidden="true"></i>
                                    <div class="rule-text">
                                        <div class="rule-title">
                                            <span :class="{ 'rule-mono': monoTitle(rule) }" :title="ruleTooltip(rule)">{{ title(rule) }}</span>
                                        </div>
                                        <div class="rule-meta">
                                            <span class="sr-only">{{ typeMeta(rule).label }}, {{ severityLabel(rule) }}: </span>
                                            <span :class="['rule-expected', { 'rule-mono': rule.type === 'setting' || rule.type === 'version_min' }]" :title="expected(rule)">{{ expected(rule) }}</span>
                                            <span v-if="subtitle(rule)" class="rule-key" :title="subtitle(rule)">{{ subtitle(rule) }}</span>
                                            <i v-if="rule.note" class="fas fa-note-sticky rule-note" :title="rule.note" aria-hidden="true"></i>
                                            <span v-if="rule.note" class="sr-only">Note: {{ rule.note }}</span>
                                        </div>
                                    </div>
                                    <span
                                        v-if="tallies[rule.id].drift > 0"
                                        class="rule-tally is-drift"
                                        :title="tallyTitle(rule)"
                                    >
                                        <i class="fas fa-xmark" aria-hidden="true"></i>{{ tallies[rule.id].drift }}
                                        <span class="sr-only">{{ tallyTitle(rule) }}</span>
                                    </span>
                                    <span
                                        v-else-if="tallies[rule.id].unknown > 0"
                                        class="rule-tally is-unknown"
                                        :title="tallyTitle(rule)"
                                    >
                                        <i class="fas fa-question" aria-hidden="true"></i>{{ tallies[rule.id].unknown }}
                                        <span class="sr-only">{{ tallyTitle(rule) }}</span>
                                    </span>
                                    <span class="rule-severity" :title="`${severityLabel(rule)} when a server drifts`">
                                        <i :class="severityIcon(rule)" aria-hidden="true"></i>
                                    </span>
                                    <div class="rule-actions">
                                        <button
                                            v-if="rule.remediable && tallies[rule.id].drift > 0"
                                            type="button"
                                            class="rule-action is-fix"
                                            :title="fixRowText(rule)"
                                            :aria-label="`${fixRowText(rule)}: ${title(rule)}`"
                                            @click="$emit('fix', { rule_ids: [rule.id] })"
                                        >
                                            <i class="fas fa-wrench" aria-hidden="true"></i>
                                        </button>
                                        <button type="button" class="rule-action" :title="`Edit rule ${title(rule)}`" :aria-label="`Edit rule ${title(rule)}`" @click="$emit('edit', rule)">
                                            <i class="fas fa-pen" aria-hidden="true"></i>
                                        </button>
                                        <button type="button" class="rule-action is-danger" :title="`Remove rule ${title(rule)}`" :aria-label="`Remove rule ${title(rule)}`" @click="$emit('delete', rule)">
                                            <i class="fas fa-trash-can" aria-hidden="true"></i>
                                        </button>
                                    </div>
                                </div>
                            </th>
                            <td
                                v-for="server in servers"
                                :key="server.id"
                                :data-server="server.id"
                                :class="['cell', `is-${cellState(rule, server)}`, { stale: cell(rule, server).stale }]"
                                :title="cellTitle(rule, server)"
                            >
                                <span class="sr-only">{{ cellTitle(rule, server) }}</span>
                                <template v-if="cellState(rule, server) === 'match'">
                                    <i class="fas fa-check" aria-hidden="true"></i>
                                </template>
                                <template v-else-if="cellState(rule, server) === 'drift'">
                                    <i class="fas fa-xmark" aria-hidden="true"></i>
                                    <span v-if="!compact" class="cell-value" aria-hidden="true">{{ actual(rule, server) }}</span>
                                    <button
                                        v-if="rule.remediable"
                                        type="button"
                                        class="cell-fix"
                                        :aria-label="`Fix ${title(rule)} on ${label(server)}`"
                                        @click="$emit('fix', { items: [{ server_id: server.id, rule_id: rule.id }] })"
                                    >
                                        <i :class="['fas fa-wrench', { 'mr-1': !compact }]" aria-hidden="true"></i><template v-if="!compact">Fix</template>
                                    </button>
                                </template>
                                <template v-else>
                                    <i :class="cell(rule, server).stale ? 'fas fa-clock-rotate-left' : 'fas fa-question'" aria-hidden="true"></i>
                                </template>
                            </td>
                            <td v-if="servers.length === 0" class="cell col-empty"></td>
                        </tr>
                    </tbody>
                </table>
                <!-- The column under the pointer, drawn once rather than by re-rendering every cell -->
                <div ref="band" class="column-band" aria-hidden="true"></div>
            </div>
        </div>
    </div>
</template>

<script>
import moment from "moment"
import { SEVERITY_META } from "@/views/attention/healthLabels"
import {
    TYPE_META, actualText, expectedText, isItemType, ruleSubtitle, ruleTally, ruleTitle, serverLabels, tallyText,
} from "./baselineFormat"

const UNKNOWN_CELL = { state: "unknown", actual: null, reason: "Not evaluated yet" }
// Widths, in pixels, of the rule column and of a server column that shows the values found. When the servers do
// not fit that way in the width available, their columns only show the state, and the values go in the tooltips
const RULE_COLUMN_PX = 352
const VALUE_COLUMN_PX = 144
const DEFAULT_WIDTH_PX = 1200

export default {
    name: "DriftMatrix",
    props: {
        rules: { type: Array, required: true },
        servers: { type: Array, required: true },
        highlightRuleId: { type: Number, default: null },
        refreshing: { type: Boolean, default: false },
        // Width the matrix may take (0: not measured yet)
        availableWidth: { type: Number, default: 0 },
    },
    data() {
        return {
            compact: false,
        }
    },
    computed: {
        labels() {
            return serverLabels(this.servers)
        },
        tallies() {
            const tallies = {}
            this.rules.forEach((rule) => {
                tallies[rule.id] = ruleTally(rule, this.servers)
            })
            return tallies
        },
    },
    watch: {
        // Watched rather than computed: the matrix renders again only when the layout changes, not at every pixel
        availableWidth: "pickLayout",
        "servers.length": "pickLayout",
    },
    created() {
        // Not reactive: hovering a column must not render the matrix again
        this.hoverServer = null
        this.pickLayout()
    },
    updated() {
        this.setHover(null)
    },
    methods: {
        pickLayout() {
            const width = this.availableWidth || DEFAULT_WIDTH_PX
            this.compact = this.servers.length > 0 && RULE_COLUMN_PX + this.servers.length * VALUE_COLUMN_PX > width
        },
        label(server) {
            return this.labels.labels.get(server.id) || server.name
        },
        typeMeta(rule) {
            return TYPE_META[rule.type] || { label: rule.type, icon: "fas fa-circle" }
        },
        title(rule) {
            return ruleTitle(rule)
        },
        subtitle(rule) {
            return ruleSubtitle(rule)
        },
        // The subtitle is left out of compact rows: it goes with the title
        ruleTooltip(rule) {
            const subtitle = this.subtitle(rule)
            return subtitle ? `${this.title(rule)}\n${subtitle}` : this.title(rule)
        },
        // Setting names and UUIDs read as code; names of things do not
        monoTitle(rule) {
            if (rule.type === "setting") {
                return !this.subtitle(rule)
            }
            return (rule.type === "galaxy_enabled" || rule.type === "object_template_active") && !rule.label
        },
        expected(rule) {
            return expectedText(rule)
        },
        severityLabel(rule) {
            return (SEVERITY_META[rule.severity] || SEVERITY_META.info).label
        },
        severityIcon(rule) {
            return (SEVERITY_META[rule.severity] || SEVERITY_META.info).icon
        },
        cell(rule, server) {
            return server.results[String(rule.id)] || UNKNOWN_CELL
        },
        cellState(rule, server) {
            return this.cell(rule, server).state
        },
        tallyTitle(rule) {
            return tallyText(this.tallies[rule.id], this.servers.length)
        },
        fixRowText(rule) {
            const count = this.tallies[rule.id].drift
            return count === 1 ? "Fix on the drifting server" : `Fix on the ${count} drifting servers`
        },
        actual(rule, server) {
            const cell = this.cell(rule, server)
            // What differs on an organisation, sharing group or galaxy is too long for a cell: it is in the title
            if (isItemType(rule.type)) {
                return cell.actual === null || cell.actual === undefined ? "absent" : "differs"
            }
            return actualText(rule, cell)
        },
        cellTitle(rule, server) {
            const cell = this.cell(rule, server)
            let text = cell.reason || "Unknown"
            if (cell.state === "match") {
                text = `In line: ${actualText(rule, cell)}`
            } else if (cell.state === "drift") {
                text = isItemType(rule.type)
                    ? `Drift: ${cell.actual === null || cell.actual === undefined ? "not on this server" : actualText(rule, cell)}`
                    : `Drift: expected ${expectedText(rule)}, found ${actualText(rule, cell)}`
            }
            return `${this.label(server)} · ${text}`
        },
        serverTitle(server) {
            const parts = [server.name]
            if (server.url && server.url !== server.name) {
                parts.push(server.url)
            }
            if (server.unavailable) {
                parts.push(server.unavailable)
            } else {
                parts.push(server.drift > 0 ? `${server.drift} drifting` : "In line")
            }
            if (server.refreshed_at) {
                parts.push(`Refreshed ${moment.unix(server.refreshed_at).fromNow()}`)
            }
            if (server.content_checked_at) {
                parts.push(`Content listed ${moment.unix(server.content_checked_at).fromNow()}`)
            }
            return parts.join("\n")
        },
        onPointer(event) {
            const target = event.target && event.target.closest ? event.target.closest("[data-server]") : null
            this.setHover(target ? target.getAttribute("data-server") : null)
        },
        onFocusOut(event) {
            if (!event.relatedTarget || !this.$el.contains(event.relatedTarget)) {
                this.setHover(null)
            }
        },
        headerOf(serverId) {
            return this.$el.querySelector(`thead th[data-server="${serverId}"]`)
        },
        // Highlights a server's header and draws the band over its column
        setHover(serverId) {
            if (serverId === this.hoverServer) {
                return
            }
            const previous = this.hoverServer !== null ? this.headerOf(this.hoverServer) : null
            if (previous) {
                previous.classList.remove("is-hover")
            }
            this.hoverServer = serverId
            const band = this.$refs.band
            const header = serverId !== null ? this.headerOf(serverId) : null
            if (!band) {
                return
            }
            if (!header) {
                band.style.display = "none"
                return
            }
            header.classList.add("is-hover")
            const origin = this.$refs.inner.getBoundingClientRect()
            const box = header.getBoundingClientRect()
            band.style.left = `${box.left - origin.left}px`
            band.style.width = `${box.width}px`
            band.style.display = "block"
        },
    },
}
</script>

<style scoped>
.matrix-wrap {
    position: relative;
    /* As wide as the table, up to the page: a small fleet does not stretch one column across the screen */
    display: inline-block;
    max-width: 100%;
    vertical-align: top;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.matrix-wrap.is-refreshing::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    height: 2px;
    width: 30%;
    background: var(--var-color-lapislazuli);
    animation: matrix-refresh 1s ease-in-out infinite;
    z-index: 4;
}

@keyframes matrix-refresh {
    from { left: -30%; }
    to { left: 100%; }
}

.matrix-scroll {
    overflow: auto;
    max-height: calc(100vh - 250px);
    min-height: 10rem;
}

.matrix-scroll:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

.matrix-inner {
    position: relative;
    width: max-content;
}

.matrix {
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.875rem;
}

.matrix thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f6f7f9;
    border-bottom: 1px solid var(--health-rule);
    padding: 0.5rem 0.6rem;
    vertical-align: bottom;
    font-weight: 600;
}

.matrix .col-rule {
    position: sticky;
    left: 0;
    z-index: 1;
    width: 22rem;
    min-width: 16rem;
    max-width: 26rem;
    background: #fff;
    border-right: 1px solid var(--health-rule);
    text-align: left;
}

.matrix thead .col-rule {
    z-index: 3;
    background: #f6f7f9;
}

.matrix-corner {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.8rem;
    color: #4a5260;
}

.matrix-domain {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 400;
    font-size: 0.75rem;
    color: #6c737d;
}

.col-server {
    min-width: 8.5rem;
    max-width: 11rem;
    text-align: center;
    border-left: 1px solid #f0f2f5;
}

.col-empty {
    color: #5a6270;
    font-weight: 400 !important;
}

.server-name {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--var-color-yankeesblue);
}

.server-state {
    display: block;
    margin-top: 0.1rem;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.server-state.is-drift {
    color: var(--health-critical-ink);
}

.server-state.is-ok {
    color: var(--health-ok-ink);
}

.server-state.is-unavailable {
    color: #6c737d;
}

.matrix thead th.is-hover {
    background: #e7f0f6;
    box-shadow: inset 0 -2px 0 var(--var-color-lapislazuli);
}

.matrix thead th.is-hover .server-name {
    color: var(--var-color-lapislazuli);
}

/* Under the sticky rule column and header, over the cells; clicks go through */
.column-band {
    display: none;
    position: absolute;
    top: 0;
    bottom: 0;
    z-index: 0;
    pointer-events: none;
    background: rgba(41, 120, 160, 0.06);
    box-shadow: inset 1px 0 0 rgba(41, 120, 160, 0.35), inset -1px 0 0 rgba(41, 120, 160, 0.35);
}

.rule-row th,
.rule-row td {
    border-bottom: 1px solid #f0f2f5;
}

.rule-row:last-child th,
.rule-row:last-child td {
    border-bottom: none;
}

.rule-row th.col-rule {
    --row-bg: #fff;
    padding: 0.4rem 0.6rem 0.4rem 0.75rem;
    font-weight: 400;
}

.rule-row:hover th.col-rule,
.rule-row:hover td {
    --row-bg: #fafbfc;
    background-color: #fafbfc;
}

.rule-row.highlighted th.col-rule,
.rule-row.highlighted td {
    --row-bg: var(--health-focus-bg);
    background-color: var(--health-focus-bg);
}

.rule-row.highlighted th.col-rule {
    box-shadow: inset 3px 0 0 var(--var-color-lapislazuli);
    animation: rule-flash 1.6s ease-out 1;
}

@keyframes rule-flash {
    0%, 30% { background-color: #d6e8f5; }
    100% { background-color: var(--health-focus-bg); }
}

.rule-cell {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    min-width: 0;
    /* Table cells ignore max-width: their content holds the column to it */
    max-width: 25rem;
}

.rule-type {
    flex: 0 0 1.1rem;
    text-align: center;
    color: #6c737d;
    font-size: 0.85rem;
}

.rule-text {
    flex: 1 1 auto;
    min-width: 0;
}

.rule-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--var-color-yankeesblue);
    font-weight: 600;
}

.rule-mono,
.cell-value {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.rule-title .rule-mono {
    font-size: 0.82rem;
}

.rule-meta {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    min-width: 0;
    font-size: 0.78rem;
    color: #5a6270;
}

.rule-expected {
    flex: 0 0 auto;
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #364156;
}

.rule-key {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rule-note {
    flex: 0 0 auto;
    color: #8a919c;
}

/* How many servers drift on the rule (or are unknown), whatever the columns in view */
.rule-tally {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.05rem 0.45rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1.4;
    cursor: default;
}

.rule-tally i {
    font-size: 0.65rem;
}

.rule-tally.is-drift {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
}

.sev-warning .rule-tally.is-drift {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
}

.sev-info .rule-tally.is-drift {
    color: var(--health-info-ink);
    background: var(--health-info-tint);
}

.rule-tally.is-unknown {
    color: #6c737d;
    background: #f0f2f5;
}

.rule-severity {
    flex: 0 0 auto;
    font-size: 0.8rem;
}

.sev-critical .rule-severity {
    color: var(--health-critical);
}

.sev-warning .rule-severity {
    color: #d9a400;
}

.sev-info .rule-severity {
    color: var(--health-info);
}

/* Over the end of the rule cell, so they take no room until needed */
.rule-actions {
    position: absolute;
    top: 50%;
    right: 0.4rem;
    transform: translateY(-50%);
    display: flex;
    gap: 0.1rem;
    padding-left: 1rem;
    background: linear-gradient(to right, transparent, var(--row-bg) 0.9rem);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.12s;
}

.col-rule:hover .rule-actions,
.col-rule:focus-within .rule-actions,
.rule-row.highlighted .rule-actions {
    opacity: 1;
    pointer-events: auto;
}

.rule-action {
    border: none;
    background: var(--row-bg);
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 4px;
    color: #5a6270;
    font-size: 0.8rem;
}

.rule-action:hover {
    background: #eef0f3;
    color: var(--var-color-yankeesblue);
}

.rule-action.is-danger:hover {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.rule-action:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 0;
}

.cell {
    text-align: center;
    padding: 0.3rem 0.4rem;
    border-left: 1px solid #f0f2f5;
    white-space: nowrap;
    cursor: default;
}

.cell.is-match {
    color: var(--health-ok);
}

.cell.is-drift {
    color: var(--health-critical-ink);
    font-weight: 600;
}

.sev-warning .cell.is-drift {
    color: var(--health-warning-ink);
}

.sev-info .cell.is-drift {
    color: var(--health-info-ink);
}

.rule-row .cell.is-drift,
.rule-row:hover .cell.is-drift {
    background-color: var(--health-critical-tint);
}

.rule-row.sev-warning .cell.is-drift,
.rule-row.sev-warning:hover .cell.is-drift {
    background-color: var(--health-warning-tint);
}

.rule-row.sev-info .cell.is-drift,
.rule-row.sev-info:hover .cell.is-drift {
    background-color: var(--health-info-tint);
}

.cell-value {
    display: inline-block;
    max-width: 7rem;
    margin-left: 0.3rem;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: bottom;
    font-size: 0.78rem;
}

/* Fix covers the drifting cell when the cell is hovered or the button has the focus */
.cell.is-drift {
    position: relative;
}

.cell-fix {
    position: absolute;
    inset: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 1px solid currentColor;
    border-radius: 4px;
    background: #fff;
    font-size: 0.78rem;
    font-weight: 600;
    color: inherit;
    opacity: 0;
    transition: opacity 0.1s;
}

.cell.is-drift:hover .cell-fix,
.cell-fix:focus-visible {
    opacity: 1;
}

.cell-fix:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 0;
}

.rule-action.is-fix:hover {
    background: var(--health-focus-bg);
    color: var(--var-color-lapislazuli);
}

.cell.is-unknown {
    color: #a0a6ae;
    font-size: 0.8rem;
}

/* Compact: one narrow column per server, its name written upwards; values are in the tooltips and the tallies */
.is-compact .col-server,
.is-compact .cell {
    width: 1.75rem;
    min-width: 1.75rem;
    max-width: 1.75rem;
}

.is-compact thead .col-server {
    padding: 0.45rem 0 0.4rem;
}

.is-compact .server-head {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
}

.is-compact .server-name {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    max-height: 9rem;
    font-size: 0.78rem;
    line-height: 1.2;
}

.is-compact .server-state {
    margin-top: 0;
    font-size: 0.66rem;
    letter-spacing: -0.02em;
}

.is-compact .cell {
    padding: 0.3rem 0;
    font-size: 0.78rem;
}

/* One line per rule, in a column of fixed width: the room goes to the servers */
.is-compact .rule-cell {
    max-width: 21rem;
}

.is-compact .rule-row th.col-rule {
    padding-top: 0.2rem;
    padding-bottom: 0.2rem;
}

.is-compact .rule-text {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
}

/* The title gives way first; the expected value keeps up to half the line */
.is-compact .rule-title {
    flex: 0 1 auto;
    min-width: 0;
}

.is-compact .rule-meta {
    flex: 0 0 auto;
    max-width: 50%;
}

.is-compact .rule-expected {
    flex: 0 1 auto;
    min-width: 0;
    max-width: none;
}

.is-compact .rule-key {
    display: none;
}

.is-compact .cell-fix {
    inset: 2px;
    font-size: 0.72rem;
}
</style>
