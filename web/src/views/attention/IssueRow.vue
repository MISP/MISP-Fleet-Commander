<template>
    <li
        :class="['issue-row', `sev-${issue.severity}`, { 'is-acked': issue.ack !== null, selectable, 'is-selected': selectable && selected }]"
        tabindex="0"
        data-nav-item
        :aria-label="`${severityMeta.label}: ${issue.title}, ${issue.server_name}`"
        @keydown.enter.self="$emit('open', issue)"
        @keydown.space.self="onSpace"
    >
        <label v-if="selectable" class="issue-check">
            <input
                type="checkbox"
                :checked="selected"
                :aria-label="`Select ${issue.title}, ${issue.server_name}`"
                @click="onCheck"
            >
        </label>
        <i :class="['issue-icon', severityMeta.icon]" :title="severityMeta.label" aria-hidden="true"></i>
        <div class="issue-main">
            <div class="issue-title">
                <span>{{ issue.title }}</span>
                <span v-if="showServer" class="issue-server">
                    <router-link :to="serverLink" tabindex="-1">{{ issue.server_name }}</router-link>
                    <span class="text-muted"> in {{ issue.fleet_name }}</span>
                </span>
            </div>
            <div v-if="issue.detail" class="issue-detail">{{ issue.detail }}</div>
            <div v-if="issue.ack !== null" class="issue-ack">
                <i class="fas fa-bell-slash mr-1" aria-hidden="true"></i>
                <span>{{ ackText }}</span>
                <span v-if="issue.ack.note" class="issue-ack-note">{{ issue.ack.note }}</span>
            </div>
        </div>
        <div class="issue-since" :title="firstSeenTitle">
            for {{ since }}
        </div>
        <div class="issue-actions">
            <b-button
                v-if="action"
                size="sm"
                variant="outline-secondary"
                class="action-button"
                :href="actionHref"
                :target="actionHref ? '_blank' : null"
                :rel="actionHref ? 'noopener' : null"
                :disabled="actionPending"
                @click="onAction"
            >
                <i v-if="actionPending" class="fas fa-circle-notch fa-spin fa-fw" aria-hidden="true"></i>
                <i v-else :class="[action.icon, 'fa-fw']" aria-hidden="true"></i>
                <span>{{ action.label }}</span>
            </b-button>
            <b-button
                v-if="issue.ack === null"
                size="sm"
                variant="link"
                class="ack-button"
                @click="$emit('ack', issue)"
            >Acknowledge</b-button>
            <b-button
                v-else
                size="sm"
                variant="link"
                class="ack-button"
                @click="$emit('unack', issue)"
            >Show again</b-button>
        </div>
    </li>
</template>

<script>
import moment from "moment"
import { SEVERITY_META, actionMeta } from "./healthLabels"

export default {
    name: "IssueRow",
    props: {
        issue: { type: Object, required: true },
        now: { type: Number, required: true },
        showServer: { type: Boolean, default: false },
        pending: { type: String, default: null },
        // A checkbox to select the row, for acting on many issues at once
        selectable: { type: Boolean, default: false },
        selected: { type: Boolean, default: false },
    },
    computed: {
        severityMeta() {
            return SEVERITY_META[this.issue.severity]
        },
        action() {
            return actionMeta(this.issue.action)
        },
        actionPending() {
            const kind = this.issue.action && this.issue.action.kind
            return this.pending !== null && (kind === "test_connection" || kind === "refresh")
        },
        actionHref() {
            const action = this.issue.action
            if (action && action.kind === "open_misp" && this.issue.server_url) {
                return `${this.issue.server_url.replace(/\/+$/, "")}${action.path || ""}`
            }
            return null
        },
        serverLink() {
            return { name: "servers.view", params: { server_id: this.issue.server_id } }
        },
        since() {
            if (!this.issue.first_seen) {
                return "now"
            }
            // `now` ticks, so that the relative time stays current
            return moment.unix(this.issue.first_seen).from(moment.unix(Math.max(this.now, this.issue.first_seen)), true)
        },
        firstSeenTitle() {
            return this.issue.first_seen ? `First seen ${moment.unix(this.issue.first_seen).format("LLL")}` : ""
        },
        ackText() {
            const ack = this.issue.ack
            if (ack.until) {
                return `Acknowledged until ${moment.unix(ack.until).calendar()}.`
            }
            return "Acknowledged until it clears."
        },
    },
    methods: {
        // `select` carries the new state and the shift key, for selecting a range of rows
        onCheck(event) {
            this.$emit("select", { issue: this.issue, checked: event.target.checked, shift: event.shiftKey })
        },
        onSpace(event) {
            if (!this.selectable) {
                return
            }
            event.preventDefault()
            this.$emit("select", { issue: this.issue, checked: !this.selected, shift: event.shiftKey })
        },
        onAction() {
            if (!this.actionHref) {
                this.$emit("action", this.issue)
            }
        },
    },
}
</script>

<style scoped>
.issue-row {
    display: grid;
    /* Fixed side columns, so that times and actions line up from one row to the next */
    grid-template-columns: 1.5rem minmax(0, 1fr) 6.5rem 17rem;
    grid-template-areas: "icon main since actions";
    column-gap: 0.75rem;
    align-items: start;
    padding: 0.6rem 0.75rem 0.6rem 1rem;
    border-top: 1px solid var(--health-rule);
    outline: none;
}

.issue-row.selectable {
    grid-template-columns: 1.25rem 1.5rem minmax(0, 1fr) 6.5rem 17rem;
    grid-template-areas: "check icon main since actions";
    padding-left: 0.75rem;
}

.issue-row.is-selected {
    background-color: var(--health-selected-bg);
}

.issue-row:focus-visible {
    box-shadow: inset 0 0 0 2px var(--var-color-lapislazuli);
    background-color: var(--health-focus-bg);
}

.issue-row.is-selected:focus-visible {
    background-color: var(--health-selected-bg);
}

/* The whole cell is the target: easier to hit, and shift-click selects a range */
.issue-check {
    grid-area: check;
    display: flex;
    justify-content: center;
    align-self: stretch;
    margin: -0.6rem 0;
    padding-top: 0.85rem;
    cursor: pointer;
}

.issue-check input {
    width: 1rem;
    height: 1rem;
    margin: 0;
    cursor: pointer;
    accent-color: var(--var-color-lapislazuli);
}

.issue-icon {
    grid-area: icon;
    font-size: 1.05rem;
    margin-top: 0.15rem;
    text-align: center;
}

.sev-critical .issue-icon { color: var(--health-critical-ink); }
.sev-warning .issue-icon { color: var(--health-warning-ink); }
.sev-info .issue-icon { color: var(--health-info-ink); }

.issue-main {
    grid-area: main;
    min-width: 0;
}

.issue-title {
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    overflow-wrap: anywhere;
}

.issue-server {
    font-weight: 400;
    margin-left: 0.4rem;
}

.issue-detail {
    color: #5a6270;
    font-size: 0.875rem;
    margin-top: 0.1rem;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
}

.issue-ack {
    font-size: 0.8125rem;
    color: #5a6270;
    margin-top: 0.2rem;
}

.issue-ack-note {
    font-style: italic;
    margin-left: 0.3rem;
}

.issue-since {
    grid-area: since;
    font-size: 0.8125rem;
    color: #6c757d;
    text-align: right;
    white-space: nowrap;
    padding-top: 0.2rem;
    font-variant-numeric: tabular-nums;
}

.issue-actions {
    grid-area: actions;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.25rem;
    white-space: nowrap;
}

/* Every state is set here: a white background alone would win over Bootstrap's hover, which turns the text white */
.action-button {
    background-color: #fff;
    color: #495057;
    border-color: #adb5bd;
}

.action-button:hover,
.action-button:focus,
.action-button:not(:disabled):not(.disabled):active {
    background-color: #eef3f8;
    color: var(--var-color-yankeesblue);
    border-color: var(--var-color-lapislazuli);
}

.action-button:focus,
.action-button:not(:disabled):not(.disabled):active:focus {
    box-shadow: 0 0 0 0.2rem rgba(41, 120, 160, 0.25);
}

.action-button i {
    margin-right: 0.3rem;
}

.ack-button {
    color: #5a6270;
    padding-left: 0.4rem;
    padding-right: 0.4rem;
}

.ack-button:hover,
.ack-button:focus {
    color: var(--var-color-yankeesblue);
}

.is-acked .issue-title,
.is-acked .issue-icon {
    opacity: 0.55;
}

@media (max-width: 991.98px) {
    .issue-row {
        grid-template-columns: 1.5rem minmax(0, 1fr);
        grid-template-areas:
            "icon main"
            ". since"
            ". actions";
        row-gap: 0.35rem;
    }

    .issue-row.selectable {
        grid-template-columns: 1.25rem 1.5rem minmax(0, 1fr);
        grid-template-areas:
            "check icon main"
            ". . since"
            ". . actions";
    }

    .issue-since {
        padding-top: 0;
        text-align: left;
    }

    .issue-actions {
        flex-wrap: wrap;
        justify-content: flex-start;
    }
}
</style>
