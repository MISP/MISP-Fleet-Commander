<template>
    <b-modal
        id="modal-baseline-fix"
        :title="title"
        size="lg"
        scrollable
        @show="onShow"
        @hidden="onHidden"
    >
        <JobRunPanel
            v-if="job"
            :job="job"
            :servers="jobServers"
            @navigate="$bvModal.hide('modal-baseline-fix')"
            @retried="followJob"
        ></JobRunPanel>

        <template v-else>
            <div v-if="loading" class="fix-state" role="status">
                <b-spinner small class="mr-2"></b-spinner>Working out what would change…
            </div>
            <b-alert :show="!!error" variant="danger">
                {{ error }}
                <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
            </b-alert>

            <template v-if="plan && !loading">
                <p v-if="applyCount > 0" class="fix-intro">
                    Each server gets its values in this order. Values are read back from MISP afterwards, and the drift
                    matrix updates as each server is done.
                </p>
                <p v-else-if="plan.servers.length > 0" class="fix-intro">
                    None of this can be changed from here: it has to be done on the servers themselves.
                </p>
                <p v-else class="fix-state">
                    <i class="fas fa-circle-check text-success mr-1" aria-hidden="true"></i>
                    Nothing drifts here any more.
                </p>

                <section v-for="server in plan.servers" :key="server.id" class="fix-server" :aria-label="server.name">
                    <h3 class="fix-server-name">
                        <i class="fas fa-server mr-1" aria-hidden="true"></i>{{ server.name }}
                        <span class="fix-server-count">{{ serverCountText(server) }}</span>
                    </h3>
                    <ul class="fix-items">
                        <li v-for="item in server.items" :key="item.rule_id" :class="['fix-item', `is-${item.action}`]">
                            <i :class="['fix-type', typeIcon(item)]" aria-hidden="true"></i>
                            <span class="fix-name" :title="item.key">{{ name(item) }}</span>
                            <span v-if="item.action === 'apply'" class="fix-change">
                                <span class="fix-current">{{ current(item) }}</span>
                                <i class="fas fa-arrow-right fix-arrow" aria-label="becomes"></i>
                                <span class="fix-expected">{{ target(item) }}</span>
                            </span>
                            <span v-else class="fix-manual" :title="item.reason">
                                <i class="fas fa-hand mr-1" aria-hidden="true"></i>By hand: {{ item.reason }}
                            </span>
                        </li>
                    </ul>
                </section>

                <b-alert :show="plan.excluded.length > 0" variant="secondary" class="fix-excluded">
                    <strong>Not included:</strong>
                    <span v-for="(server, index) in plan.excluded" :key="server.id">
                        {{ server.name }} ({{ server.reason.toLowerCase() }}){{ index < plan.excluded.length - 1 ? ', ' : '' }}
                    </span>.
                    Their values are not known now.
                </b-alert>
            </template>
        </template>

        <template #modal-footer="{ cancel }">
            <template v-if="job">
                <b-button variant="secondary" @click="cancel()">Close</b-button>
            </template>
            <template v-else>
                <span v-if="manualCount > 0 && applyCount > 0" class="fix-footer-note">{{ manualCount }} to do by hand, not included</span>
                <b-button variant="outline-secondary" @click="cancel()">Cancel</b-button>
                <b-button variant="primary" :disabled="applyCount === 0 || starting" @click="confirm">
                    <b-spinner v-if="starting" small class="mr-1"></b-spinner>
                    <i v-else class="fas fa-wrench mr-1" aria-hidden="true"></i>{{ confirmLabel }}
                </b-button>
            </template>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/baselines"
import JobRunPanel from "@/components/jobs/JobRunPanel.vue"
import { TYPE_META, actualText, expectedText, formatValue, isContentType } from "./baselineFormat"

// Fixing drift: a preview of `server · rule · current → expected`, then the job that applies it
export default {
    name: "RemediationModal",
    components: { JobRunPanel },
    props: {
        fleetId: { type: Number, required: true },
        // What to fix: {} for every drifting value, {rule_ids}, {server_ids} or {items: [{server_id, rule_id}]}
        scope: { type: Object, default: () => ({}) },
    },
    data() {
        return {
            plan: null,
            loading: false,
            error: null,
            starting: false,
            jobId: null,
        }
    },
    computed: {
        job() {
            return this.jobId === null ? null : this.$store.getters["jobs/job"](this.jobId)
        },
        applyItems() {
            if (!this.plan) {
                return []
            }
            return this.plan.servers.flatMap(server => server.items
                .filter(item => item.action === "apply")
                .map(item => ({ server_id: server.id, rule_id: item.rule_id })))
        },
        applyCount() {
            return this.applyItems.length
        },
        manualCount() {
            return this.plan ? this.plan.counts.manual : 0
        },
        applyServers() {
            return new Set(this.applyItems.map(item => item.server_id)).size
        },
        confirmLabel() {
            if (this.applyCount === 0) {
                return "Nothing to fix"
            }
            const values = `${this.applyCount} value${this.applyCount === 1 ? "" : "s"}`
            return this.applyServers > 1 ? `Fix ${values} on ${this.applyServers} servers` : `Fix ${values}`
        },
        title() {
            if (this.job) {
                return "Fixing drift"
            }
            if (this.scope.items && this.scope.items.length === 1) {
                return "Fix this value"
            }
            if (this.scope.rule_ids) {
                return "Fix this rule on every drifting server"
            }
            return "Fix all drift"
        },
        jobServers() {
            return this.plan ? this.plan.servers.map(server => ({ id: server.id, name: server.name })) : []
        },
    },
    methods: {
        onShow() {
            this.jobId = null
            this.load()
        },
        onHidden() {
            this.plan = null
            this.error = null
        },
        load() {
            this.loading = true
            this.error = null
            api.remediationPreview(this.fleetId, this.scope)
                .then((plan) => { this.plan = plan })
                .catch((error) => { this.error = error.message })
                .finally(() => { this.loading = false })
        },
        confirm() {
            this.starting = true
            api.remediate(this.fleetId, this.applyItems)
                .then((data) => {
                    this.$store.commit("jobs/track", data.job_id)
                    this.$store.commit("jobs/setJob", data.job)
                    this.jobId = data.job_id
                    this.$emit("started", data.job)
                })
                .catch((error) => {
                    if (error.status === 409) {
                        this.load()
                    }
                    this.$bvToast.toast(error.message, { title: "Could not start the fix", variant: "danger" })
                })
                .finally(() => { this.starting = false })
        },
        followJob(job) {
            this.jobId = job.id
        },
        serverCountText(server) {
            const apply = server.items.filter(item => item.action === "apply").length
            const manual = server.items.length - apply
            const parts = []
            if (apply > 0) {
                parts.push(`${apply} to fix`)
            }
            if (manual > 0) {
                parts.push(`${manual} by hand`)
            }
            return parts.join(" · ")
        },
        typeIcon(item) {
            return (TYPE_META[item.type] || {}).icon || "fas fa-circle"
        },
        name(item) {
            if (item.type === "version_min") {
                return "MISP version"
            }
            return item.label || item.key
        },
        current(item) {
            return actualText(item, { actual: item.current })
        },
        target(item) {
            if (isContentType(item.type)) {
                return expectedText(item)
            }
            return formatValue(item.expected)
        },
    },
}
</script>

<style scoped>
.fix-state {
    padding: 1rem 0;
    color: #4a5260;
}

.fix-intro {
    color: #4a5260;
    font-size: 0.9rem;
}

.fix-server {
    margin-bottom: 1rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.fix-server-name {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0;
    padding: 0.45rem 0.75rem;
    background: #f6f7f9;
    border-bottom: 1px solid var(--health-rule);
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.fix-server-count {
    margin-left: auto;
    font-size: 0.78rem;
    font-weight: 500;
    color: #5a6270;
}

.fix-items {
    list-style: none;
    margin: 0;
    padding: 0;
}

.fix-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0.75rem;
    border-top: 1px solid #f0f2f5;
    font-size: 0.875rem;
}

.fix-item:first-child {
    border-top: none;
}

.fix-type {
    flex: 0 0 1rem;
    text-align: center;
    color: #6c737d;
}

.fix-name {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--var-color-yankeesblue);
}

.fix-change {
    flex: 0 1 auto;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    max-width: 55%;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.8rem;
}

.fix-current,
.fix-expected {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0 0.35rem;
    border-radius: 3px;
}

.fix-current {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
    text-decoration: line-through;
    text-decoration-color: rgba(181, 42, 55, 0.45);
}

.fix-expected {
    background: #eaf6ef;
    color: var(--health-ok-ink);
}

.fix-arrow {
    color: #8a919c;
    font-size: 0.75rem;
}

.fix-item.is-manual .fix-name {
    color: #5a6270;
}

.fix-manual {
    flex: 0 1 auto;
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.8rem;
    color: #5a6270;
}

.fix-excluded {
    font-size: 0.875rem;
}

.fix-footer-note {
    margin-right: auto;
    font-size: 0.85rem;
    color: #5a6270;
}
</style>
