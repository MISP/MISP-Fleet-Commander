<template>
    <div class="server-issues">
        <div v-if="!loaded" class="issues-state" role="status">
            <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Loading health…
        </div>
        <template v-else>
            <p v-if="active.length === 0" class="issues-state issues-healthy">
                <i class="fas fa-check-circle" aria-hidden="true"></i>
                No open issue<span v-if="acknowledgedCount > 0"> ({{ acknowledgedCount }} acknowledged)</span>.
            </p>
            <ul v-else class="issue-list">
                <li v-for="issue in active" :key="issue.id" :class="['issue', `sev-${issue.severity}`]">
                    <i :class="['issue-icon', severityMeta(issue).icon]" :title="severityMeta(issue).label" aria-hidden="true"></i>
                    <div class="issue-main">
                        <div class="issue-title">
                            <span class="sr-only">{{ severityMeta(issue).label }}:</span>
                            {{ issue.title }}
                        </div>
                        <div v-if="issue.detail" class="issue-detail" :title="issue.detail">{{ issue.detail }}</div>
                    </div>
                    <span class="issue-since" :title="firstSeenTitle(issue)">for {{ since(issue) }}</span>
                </li>
            </ul>
            <div class="issues-footer">
                <span v-if="active.length > 0 && acknowledgedCount > 0" class="text-muted">{{ acknowledgedCount }} acknowledged, not shown.</span>
                <router-link :to="attentionLink" class="attention-link">
                    Open in Needs attention <i class="fas fa-arrow-right" aria-hidden="true"></i>
                </router-link>
            </div>
        </template>
    </div>
</template>

<script>
import { mapState } from "vuex"
import moment from "moment"
import { compareIssues } from "@/store/modules/health"
import { SEVERITY_META } from "@/views/attention/healthLabels"

// The open issues of one server, compact (side panels). Acknowledging and actions stay on the Needs attention page
export default {
    name: "ServerIssueList",
    props: {
        server_id: { type: Number, required: true },
        fleet_id: { type: [Number, String], default: null },
    },
    data() {
        return {
            now: Date.now(),
            ticker: null,
        }
    },
    computed: {
        ...mapState({
            loaded: state => state.health.loaded,
            issuesByServer: state => state.health.issuesByServer,
        }),
        issues() {
            return this.issuesByServer[this.server_id] || []
        },
        active() {
            return this.issues.filter(issue => issue.ack === null).sort(compareIssues)
        },
        acknowledgedCount() {
            return this.issues.length - this.active.length
        },
        attentionLink() {
            const query = { server_id: String(this.server_id) }
            if (this.fleet_id !== null) {
                query.fleet_id = String(this.fleet_id)
            }
            return { name: "attention", query }
        },
    },
    methods: {
        severityMeta(issue) {
            return SEVERITY_META[issue.severity] || SEVERITY_META.info
        },
        since(issue) {
            if (!issue.first_seen) {
                return "now"
            }
            return moment.unix(issue.first_seen).from(moment(Math.max(this.now, issue.first_seen * 1000)), true)
        },
        firstSeenTitle(issue) {
            return issue.first_seen ? `First seen ${moment.unix(issue.first_seen).format("LLL")}` : ""
        },
    },
    mounted() {
        this.ticker = setInterval(() => { this.now = Date.now() }, 30 * 1000)
    },
    beforeDestroy() {
        clearInterval(this.ticker)
    },
}
</script>

<style scoped>
.server-issues {
    font-size: 0.875rem;
}

.issues-state {
    margin: 0;
    padding: 0.5rem 0.75rem;
    color: #5a6270;
}

.issues-healthy i {
    color: var(--health-ok);
    margin-right: 0.2rem;
}

.issue-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.issue {
    display: grid;
    grid-template-columns: 1.1rem minmax(0, 1fr) auto;
    column-gap: 0.5rem;
    align-items: start;
    padding: 0.45rem 0.75rem;
    border-top: 1px solid var(--health-rule);
}

.issue:first-child {
    border-top: 0;
}

.issue-icon {
    margin-top: 0.15rem;
    text-align: center;
}

.sev-critical .issue-icon {
    color: var(--health-critical-ink);
}

.sev-warning .issue-icon {
    color: var(--health-warning-ink);
}

.sev-info .issue-icon {
    color: var(--health-info-ink);
}

.issue-main {
    min-width: 0;
}

.issue-title {
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    overflow-wrap: anywhere;
}

.issue-detail {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: #5a6270;
    font-size: 0.8125rem;
    overflow-wrap: anywhere;
}

.issue-since {
    color: #6c757d;
    font-size: 0.75rem;
    white-space: nowrap;
    padding-top: 0.15rem;
    font-variant-numeric: tabular-nums;
}

.issues-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.25rem 0.75rem;
    padding: 0.4rem 0.75rem 0.5rem;
    border-top: 1px solid var(--health-rule);
    font-size: 0.8125rem;
}

.attention-link {
    margin-left: auto;
    font-weight: 600;
}

.attention-link i {
    font-size: 0.75rem;
}
</style>
