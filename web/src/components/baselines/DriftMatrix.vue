<template>
    <div class="matrix-wrap" :class="{ 'is-refreshing': refreshing }">
        <div class="matrix-scroll" tabindex="0" role="region" aria-label="Drift: rules against servers">
            <table class="matrix">
                <thead>
                    <tr>
                        <th scope="col" class="col-rule">
                            <span class="matrix-corner">Rule <span class="text-muted font-weight-normal">· expected</span></span>
                        </th>
                        <th v-for="server in servers" :key="server.id" scope="col" class="col-server" :title="serverTitle(server)">
                            <router-link :to="{ name: 'servers.view', params: { server_id: server.id } }" class="server-name">
                                {{ server.name }}
                            </router-link>
                            <span v-if="server.unavailable" class="server-state is-unavailable">
                                <i class="fas fa-plug-circle-xmark" aria-hidden="true"></i> {{ server.unavailable }}
                            </span>
                            <span v-else-if="server.drift > 0" class="server-state is-drift">{{ server.drift }} drifting</span>
                            <span v-else class="server-state is-ok"><i class="fas fa-check" aria-hidden="true"></i> In line</span>
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
                                        <span :class="{ 'rule-mono': monoTitle(rule) }" :title="title(rule)">{{ title(rule) }}</span>
                                    </div>
                                    <div class="rule-meta">
                                        <span class="sr-only">{{ typeMeta(rule).label }}, {{ severityLabel(rule) }}: </span>
                                        <span :class="['rule-expected', { 'rule-mono': rule.type === 'setting' || rule.type === 'version_min' }]">{{ expected(rule) }}</span>
                                        <span v-if="subtitle(rule)" class="rule-key" :title="subtitle(rule)">{{ subtitle(rule) }}</span>
                                        <i v-if="rule.note" class="fas fa-note-sticky rule-note" :title="rule.note" aria-hidden="true"></i>
                                        <span v-if="rule.note" class="sr-only">Note: {{ rule.note }}</span>
                                    </div>
                                </div>
                                <span class="rule-severity" :title="`${severityLabel(rule)} when a server drifts`">
                                    <i :class="severityIcon(rule)" aria-hidden="true"></i>
                                </span>
                                <div class="rule-actions">
                                    <button
                                        v-if="rule.remediable && driftCount(rule) > 0"
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
                            :class="['cell', `is-${cellState(rule, server)}`, { stale: cell(rule, server).stale }]"
                            :title="cellTitle(rule, server)"
                        >
                            <span class="sr-only">{{ server.name }}: {{ cellTitle(rule, server) }}</span>
                            <template v-if="cellState(rule, server) === 'match'">
                                <i class="fas fa-check" aria-hidden="true"></i>
                            </template>
                            <template v-else-if="cellState(rule, server) === 'drift'">
                                <i class="fas fa-xmark" aria-hidden="true"></i>
                                <span class="cell-value" aria-hidden="true">{{ actual(rule, server) }}</span>
                                <button
                                    v-if="rule.remediable"
                                    type="button"
                                    class="cell-fix"
                                    :aria-label="`Fix ${title(rule)} on ${server.name}`"
                                    @click="$emit('fix', { items: [{ server_id: server.id, rule_id: rule.id }] })"
                                >
                                    <i class="fas fa-wrench mr-1" aria-hidden="true"></i>Fix
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
        </div>
    </div>
</template>

<script>
import moment from "moment"
import { SEVERITY_META } from "@/views/attention/healthLabels"
import { TYPE_META, actualText, expectedText, ruleSubtitle, ruleTitle } from "./baselineFormat"

const UNKNOWN_CELL = { state: "unknown", actual: null, reason: "Not evaluated yet" }

export default {
    name: "DriftMatrix",
    props: {
        rules: { type: Array, required: true },
        servers: { type: Array, required: true },
        highlightRuleId: { type: Number, default: null },
        refreshing: { type: Boolean, default: false },
    },
    methods: {
        typeMeta(rule) {
            return TYPE_META[rule.type] || { label: rule.type, icon: "fas fa-circle" }
        },
        title(rule) {
            return ruleTitle(rule)
        },
        subtitle(rule) {
            return ruleSubtitle(rule)
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
        fixRowText(rule) {
            const count = this.driftCount(rule)
            return count === 1 ? "Fix on the drifting server" : `Fix on the ${count} drifting servers`
        },
        driftCount(rule) {
            return this.servers.filter(server => this.cellState(rule, server) === "drift").length
        },
        actual(rule, server) {
            return actualText(rule, this.cell(rule, server))
        },
        cellTitle(rule, server) {
            const cell = this.cell(rule, server)
            if (cell.state === "match") {
                return `In line: ${actualText(rule, cell)}`
            }
            if (cell.state === "drift") {
                return `Drift: expected ${expectedText(rule)}, found ${actualText(rule, cell)}`
            }
            return cell.reason || "Unknown"
        },
        serverTitle(server) {
            const parts = [server.url]
            if (server.refreshed_at) {
                parts.push(`Refreshed ${moment.unix(server.refreshed_at).fromNow()}`)
            }
            if (server.content_checked_at) {
                parts.push(`Content listed ${moment.unix(server.content_checked_at).fromNow()}`)
            }
            return parts.join("\n")
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
    font-size: 0.8rem;
    color: #4a5260;
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

.rule-row th,
.rule-row td {
    border-bottom: 1px solid #f0f2f5;
}

.rule-row:last-child th,
.rule-row:last-child td {
    border-bottom: none;
}

.rule-row th.col-rule {
    padding: 0.4rem 0.6rem 0.4rem 0.75rem;
    font-weight: 400;
}

.rule-row:hover th.col-rule,
.rule-row:hover td {
    background-color: #fafbfc;
}

.rule-row.highlighted th.col-rule,
.rule-row.highlighted td {
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

.rule-actions {
    display: flex;
    gap: 0.1rem;
    flex: 0 0 auto;
    opacity: 0;
    transition: opacity 0.12s;
}

.rule-row:hover .rule-actions,
.rule-row:focus-within .rule-actions,
.rule-row.highlighted .rule-actions {
    opacity: 1;
}

.rule-action {
    border: none;
    background: none;
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
</style>
