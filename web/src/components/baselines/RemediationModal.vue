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
                <p v-if="plan.servers.length === 0" class="fix-state">
                    <i class="fas fa-circle-check text-success mr-1" aria-hidden="true"></i>
                    Nothing drifts here any more.
                </p>

                <template v-else>
                    <div :class="['fix-summary', { 'is-manual-only': applyCount === 0 }]">
                        <div class="fix-summary-main">
                            <template v-if="applyCount > 0">
                                <span class="fix-summary-count">{{ number(applyCount) }}</span>
                                <span class="fix-summary-label">
                                    {{ applyCount === 1 ? "value to fix" : "values to fix" }}
                                    <span class="fix-summary-where">{{ whereText }}</span>
                                </span>
                            </template>
                            <span v-else class="fix-summary-label">
                                <i class="fas fa-hand mr-1" aria-hidden="true"></i>Nothing here can be fixed from Fleet Commander
                            </span>
                        </div>
                        <ul v-if="manualCount > 0 || plan.excluded.length > 0" class="fix-summary-notes">
                            <li v-if="manualCount > 0">
                                <i class="fas fa-hand fa-fw" aria-hidden="true"></i>
                                {{ number(manualCount) }} {{ manualCount === 1 ? "value has" : "values have" }} to be changed on the servers themselves{{ applyCount > 0 ? ", not included" : "" }}
                            </li>
                            <li v-if="plan.excluded.length > 0">
                                <i class="fas fa-plug-circle-xmark fa-fw" aria-hidden="true"></i>
                                {{ plan.excluded.length === 1 ? "1 server is not included: its values are" : `${plan.excluded.length} servers are not included: their values are` }} not known now
                            </li>
                        </ul>
                        <p v-if="applyCount > 0" class="fix-summary-how">{{ howText }}</p>
                    </div>

                    <div v-if="canGroup || groups.length > FILTER_FROM" class="fix-toolbar">
                        <b-button-group v-if="canGroup" size="sm" role="group" aria-label="Group the changes">
                            <b-button
                                :variant="mode === 'rule' ? 'primary' : 'outline-primary'"
                                :aria-pressed="mode === 'rule' ? 'true' : 'false'"
                                @click="setMode('rule')"
                            ><i class="fas fa-list-check mr-1" aria-hidden="true"></i>By rule <span class="fix-toggle-count">{{ ruleGroups.length }}</span></b-button>
                            <b-button
                                :variant="mode === 'server' ? 'primary' : 'outline-primary'"
                                :aria-pressed="mode === 'server' ? 'true' : 'false'"
                                @click="setMode('server')"
                            ><i class="fas fa-server mr-1" aria-hidden="true"></i>By server <span class="fix-toggle-count">{{ serverGroups.length }}</span></b-button>
                        </b-button-group>
                        <b-input-group v-if="groups.length > FILTER_FROM" size="sm" class="fix-filter">
                            <b-input-group-prepend is-text><i class="fas fa-magnifying-glass" aria-hidden="true"></i></b-input-group-prepend>
                            <b-form-input
                                v-model="filter"
                                type="search"
                                debounce="150"
                                :placeholder="mode === 'rule' ? 'Filter rules' : 'Filter servers'"
                                :aria-label="mode === 'rule' ? 'Filter rules' : 'Filter servers'"
                            ></b-form-input>
                        </b-input-group>
                    </div>

                    <p v-if="visibleGroups.length === 0" class="fix-state fix-no-match">
                        No {{ mode === 'rule' ? 'rule' : 'server' }} matches “{{ filter }}”.
                    </p>

                    <ul v-else-if="singleServer" class="fix-groups fix-items is-flat" :aria-label="`Changes on ${singleServer.server.name}`">
                        <li v-for="item in shownDetail(singleServer)" :key="item.rule_id" :class="['fix-item', `is-${item.action}`]">
                            <i :class="['fix-type', typeIcon(item)]" :title="typeLabel(item)" aria-hidden="true"></i>
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
                        <li v-if="detailHidden(singleServer) > 0" class="fix-item fix-flat-more">
                            <b-button size="sm" variant="link" class="fix-more" @click="showAllDetail(singleServer)">Show {{ detailHidden(singleServer) }} more</b-button>
                        </li>
                    </ul>

                    <ul v-else class="fix-groups" :aria-label="mode === 'rule' ? 'Changes by rule' : 'Changes by server'">
                        <li
                            v-for="group in shownGroups"
                            :key="group.key"
                            :class="['fix-group', { 'is-open': isOpen(group), 'is-manual': group.applyCount === 0 }]"
                        >
                            <button
                                type="button"
                                class="fix-group-head"
                                :aria-expanded="isOpen(group) ? 'true' : 'false'"
                                @click="toggle(group)"
                            >
                                <i :class="['fas', isOpen(group) ? 'fa-chevron-down' : 'fa-chevron-right', 'fix-chevron']" aria-hidden="true"></i>
                                <template v-if="mode === 'rule'">
                                    <i :class="['fix-type', typeIcon(group.rule)]" :title="typeLabel(group.rule)" aria-hidden="true"></i>
                                    <span class="fix-name" :title="group.rule.key">{{ name(group.rule) }}</span>
                                    <span v-if="group.applyCount > 0" class="fix-change">
                                        <span :class="['fix-current', { 'is-varied': group.currentText === null }]">{{ group.currentText === null ? "varies" : group.currentText }}</span>
                                        <i class="fas fa-arrow-right fix-arrow" aria-label="becomes"></i>
                                        <span class="fix-expected">{{ target(group.rule) }}</span>
                                    </span>
                                    <span v-else class="fix-manual-tag"><i class="fas fa-hand mr-1" aria-hidden="true"></i>By hand</span>
                                </template>
                                <template v-else>
                                    <i class="fas fa-server fix-type" aria-hidden="true"></i>
                                    <span class="fix-name">{{ group.server.name }}</span>
                                </template>
                                <span class="fix-group-count">{{ groupCountText(group) }}</span>
                            </button>

                            <div v-if="isOpen(group)" class="fix-group-body">
                                <!-- By rule: the servers it is fixed on -->
                                <template v-if="mode === 'rule'">
                                    <p v-if="group.manualCount > 0 && group.reasonText" class="fix-reason">
                                        <i class="fas fa-hand mr-1" aria-hidden="true"></i>By hand on {{ group.manualCount === 1 ? "this server" : `${group.manualCount} servers` }}: {{ group.reasonText }}
                                    </p>
                                    <ul class="fix-servers">
                                        <li
                                            v-for="entry in shownDetail(group)"
                                            :key="entry.server.id"
                                            :class="['fix-server-chip', { 'is-manual': entry.item.action !== 'apply' }]"
                                            :title="entry.item.action === 'apply' ? '' : entry.item.reason"
                                        >
                                            <i v-if="entry.item.action !== 'apply' && group.applyCount > 0" class="fas fa-hand" aria-label="By hand:"></i>
                                            {{ entry.server.name }}
                                            <span v-if="group.currentText === null && entry.item.action === 'apply'" class="fix-chip-value">{{ current(entry.item) }}</span>
                                            <span v-if="entry.item.action !== 'apply' && !group.reasonText" class="fix-chip-value">{{ entry.item.reason }}</span>
                                        </li>
                                    </ul>
                                </template>

                                <!-- By server: its values, in the order they are applied -->
                                <ul v-else class="fix-items">
                                    <li v-for="item in shownDetail(group)" :key="item.rule_id" :class="['fix-item', `is-${item.action}`]">
                                        <i :class="['fix-type', typeIcon(item)]" :title="typeLabel(item)" aria-hidden="true"></i>
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

                                <b-button
                                    v-if="detailHidden(group) > 0"
                                    size="sm"
                                    variant="link"
                                    class="fix-more"
                                    @click="showAllDetail(group)"
                                >Show {{ detailHidden(group) }} more</b-button>
                            </div>
                        </li>
                    </ul>

                    <div v-if="hiddenGroups > 0" class="fix-more-groups">
                        <span>{{ hiddenGroups }} more {{ mode === 'rule' ? (hiddenGroups === 1 ? 'rule' : 'rules') : (hiddenGroups === 1 ? 'server' : 'servers') }}</span>
                        <b-button size="sm" variant="link" class="fix-more" @click="groupLimit += GROUP_STEP">
                            Show {{ Math.min(GROUP_STEP, hiddenGroups) }} more
                        </b-button>
                    </div>

                    <b-alert :show="plan.excluded.length > 0" variant="secondary" class="fix-excluded">
                        <strong>Not included:</strong> {{ excludedText }}.
                    </b-alert>
                </template>
            </template>
        </template>

        <template #modal-footer="{ cancel }">
            <template v-if="job">
                <b-button variant="secondary" @click="cancel()">Close</b-button>
            </template>
            <template v-else>
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
import {
    applyItems, currentText, fixRequest, itemName, ruleGroups, serverGroups, targetText, typeIcon, typeLabel,
} from "./remediationPlan"

// Groups shown at first, and how many more each "Show more" adds; values or servers listed in an open group
const GROUP_LIMIT = 60
const GROUP_STEP = 100
const DETAIL_LIMIT = 40
// A filter box from this many groups
const FILTER_FROM = 8
// Servers named in the "not included" note
const EXCLUDED_NAMED = 10

// Fixing drift: what would change, grouped by rule or by server (a whole fleet can drift on thousands of values),
// then the job that applies it
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
            groupBy: null,
            filter: "",
            expanded: {},
            detailLimits: {},
            groupLimit: GROUP_LIMIT,
            GROUP_STEP,
            FILTER_FROM,
        }
    },
    computed: {
        job() {
            return this.jobId === null ? null : this.$store.getters["jobs/job"](this.jobId)
        },
        applyItems() {
            return this.plan ? applyItems(this.plan) : []
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
        applyRules() {
            return new Set(this.applyItems.map(item => item.rule_id)).size
        },
        whereText() {
            const servers = this.singleServer
                ? this.singleServer.server.name
                : `${this.number(this.applyServers)} ${this.applyServers === 1 ? "server" : "servers"}`
            if (this.applyRules <= 1) {
                return `on ${servers}`
            }
            return `on ${servers}, from ${this.number(this.applyRules)} rules`
        },
        howText() {
            if (this.applyCount === 1) {
                return "The value is set, then read back from MISP. The drift matrix updates when it is done."
            }
            if (this.applyServers === 1) {
                return "The values are set one after the other, then read back from MISP. The drift matrix updates when the server is done."
            }
            return "Each server gets its values one after the other, read back from MISP afterwards. The drift matrix updates as each server is done."
        },
        // `name (reason), …`, the first ones only
        excludedText() {
            const excluded = this.plan ? this.plan.excluded : []
            const named = excluded.slice(0, EXCLUDED_NAMED).map(server => `${server.name} (${server.reason.toLowerCase()})`)
            const more = excluded.length - named.length
            return named.join(", ") + (more > 0 ? ` and ${more} more` : "")
        },
        // One server (a cell, or a fleet where only one drifts): its values are listed without a group around them
        singleServer() {
            return this.serverGroups.length === 1 ? this.serverGroups[0] : null
        },
        ruleGroups() {
            return this.plan ? ruleGroups(this.plan) : []
        },
        serverGroups() {
            return this.plan ? serverGroups(this.plan) : []
        },
        // Both groupings only make sense with several servers and several rules
        canGroup() {
            return this.serverGroups.length > 1 && this.ruleGroups.length > 1
        },
        mode() {
            if (this.groupBy !== null && this.canGroup) {
                return this.groupBy
            }
            return this.serverGroups.length > 1 ? "rule" : "server"
        },
        groups() {
            return this.mode === "rule" ? this.ruleGroups : this.serverGroups
        },
        visibleGroups() {
            const search = this.filter.trim().toLowerCase()
            return search === "" ? this.groups : this.groups.filter(group => group.search.includes(search))
        },
        shownGroups() {
            return this.visibleGroups.slice(0, this.groupLimit)
        },
        hiddenGroups() {
            return Math.max(0, this.visibleGroups.length - this.groupLimit)
        },
        confirmLabel() {
            if (this.applyCount === 0) {
                return "Nothing to fix"
            }
            const values = `${this.number(this.applyCount)} value${this.applyCount === 1 ? "" : "s"}`
            return this.applyServers > 1 ? `Fix ${values} on ${this.number(this.applyServers)} servers` : `Fix ${values}`
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
    watch: {
        filter() {
            this.groupLimit = GROUP_LIMIT
        },
    },
    methods: {
        onShow() {
            this.jobId = null
            this.groupBy = null
            this.filter = ""
            this.expanded = {}
            this.detailLimits = {}
            this.groupLimit = GROUP_LIMIT
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
                .then((plan) => { this.plan = Object.freeze(plan) })
                .catch((error) => { this.error = error.message })
                .finally(() => { this.loading = false })
        },
        confirm() {
            this.starting = true
            api.remediate(this.fleetId, fixRequest(this.plan, this.scope))
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
        setMode(mode) {
            if (this.groupBy !== mode) {
                this.groupBy = mode
                this.groupLimit = GROUP_LIMIT
            }
        },
        // A group alone is open from the start (one cell, one rule, one server)
        isOpen(group) {
            const state = this.expanded[group.key]
            return state !== undefined ? state : this.groups.length === 1
        },
        toggle(group) {
            this.$set(this.expanded, group.key, !this.isOpen(group))
        },
        shownDetail(group) {
            return group.details.slice(0, this.detailLimits[group.key] || DETAIL_LIMIT)
        },
        detailHidden(group) {
            return Math.max(0, group.details.length - (this.detailLimits[group.key] || DETAIL_LIMIT))
        },
        showAllDetail(group) {
            this.$set(this.detailLimits, group.key, group.details.length)
        },
        groupCountText(group) {
            const parts = []
            if (this.mode === "rule") {
                if (group.applyCount > 0) {
                    parts.push(`${this.number(group.applyCount)} ${group.applyCount === 1 ? "server" : "servers"}`)
                }
                if (group.manualCount > 0) {
                    parts.push(group.applyCount > 0 ? `${this.number(group.manualCount)} by hand` : `${this.number(group.manualCount)} ${group.manualCount === 1 ? "server" : "servers"}`)
                }
            } else {
                if (group.applyCount > 0) {
                    parts.push(`${this.number(group.applyCount)} to fix`)
                }
                if (group.manualCount > 0) {
                    parts.push(`${this.number(group.manualCount)} by hand`)
                }
            }
            return parts.join(" · ")
        },
        number(value) {
            return Number(value).toLocaleString()
        },
        typeIcon,
        typeLabel,
        name: itemName,
        current: currentText,
        target: targetText,
    },
}
</script>

<style scoped>
.fix-state {
    padding: 1rem 0;
    color: #4a5260;
}

/* Summary */
.fix-summary {
    margin-bottom: 1rem;
    padding: 0.85rem 1rem;
    border: 1px solid var(--health-rule);
    border-left: 4px solid var(--var-color-lapislazuli);
    border-radius: 6px;
    background: #f8fafc;
}

.fix-summary.is-manual-only {
    border-left-color: #adb5bd;
}

.fix-summary-main {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.25rem 0.6rem;
}

.fix-summary-count {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.1;
    color: var(--var-color-yankeesblue);
    font-variant-numeric: tabular-nums;
}

.fix-summary-label {
    font-size: 1rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.fix-summary-where {
    font-weight: 400;
    color: #4a5260;
}

.fix-summary-notes {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    font-size: 0.85rem;
    color: #4a5260;
}

.fix-summary-notes li + li {
    margin-top: 0.15rem;
}

.fix-summary-notes i {
    color: #6c737d;
}

.fix-summary-how {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: #6c737d;
}

/* Toolbar */
.fix-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.6rem;
}

.fix-toggle-count {
    margin-left: 0.2rem;
    font-weight: 400;
    opacity: 0.8;
    font-variant-numeric: tabular-nums;
}

.fix-filter {
    flex: 0 1 15rem;
    margin-left: auto;
}

.fix-no-match {
    text-align: center;
}

/* Groups */
.fix-groups {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.fix-group + .fix-group {
    border-top: 1px solid var(--health-rule);
}

.fix-group-head {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    width: 100%;
    padding: 0.45rem 0.75rem;
    border: 0;
    background: #fff;
    text-align: left;
    font-size: 0.875rem;
    cursor: pointer;
}

.fix-group-head:hover {
    background: #f6f8fa;
}

.fix-group-head:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

.fix-group.is-open > .fix-group-head {
    background: #f3f6f9;
    border-bottom: 1px solid var(--health-rule);
}

.fix-chevron {
    flex: 0 0 0.75rem;
    font-size: 0.7rem;
    color: #8a919c;
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

.fix-group.is-manual .fix-name {
    color: #5a6270;
}

.fix-group-count {
    flex: 0 0 auto;
    min-width: 5.5rem;
    text-align: right;
    font-size: 0.8rem;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

.fix-group-body {
    padding: 0.5rem 0.75rem 0.6rem 2.1rem;
    background: #fcfdfe;
}

.fix-reason {
    margin: 0 0 0.4rem;
    font-size: 0.8rem;
    color: #5a6270;
}

/* By rule: the servers */
.fix-servers {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    list-style: none;
    margin: 0;
    padding: 0;
}

.fix-server-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    max-width: 100%;
    padding: 0.1rem 0.5rem;
    border: 1px solid #dfe3e8;
    border-radius: 999px;
    background: #fff;
    font-size: 0.8rem;
    color: var(--var-color-yankeesblue);
    white-space: nowrap;
}

.fix-server-chip.is-manual {
    border-style: dashed;
    color: #5a6270;
}

.fix-chip-value {
    overflow: hidden;
    text-overflow: ellipsis;
    padding-left: 0.35rem;
    border-left: 1px solid #dfe3e8;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.75rem;
    color: var(--health-critical-ink);
}

.fix-server-chip.is-manual .fix-chip-value {
    font-family: inherit;
    color: #5a6270;
}

/* By server: the values */
.fix-items {
    list-style: none;
    margin: 0;
    padding: 0;
}

.fix-items.is-flat .fix-item {
    padding: 0.45rem 0.75rem;
}

.fix-flat-more {
    padding-top: 0.1rem !important;
}

.fix-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.35rem 0;
    border-top: 1px solid #f0f2f5;
    font-size: 0.875rem;
}

.fix-item:first-child {
    border-top: none;
}

.fix-item.is-manual .fix-name {
    color: #5a6270;
}

/* Values */
.fix-change {
    flex: 0 1 auto;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    max-width: 45%;
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

.fix-current.is-varied {
    background: #f1f3f5;
    color: #5a6270;
    text-decoration: none;
    font-family: inherit;
    font-style: italic;
}

.fix-expected {
    background: #eaf6ef;
    color: var(--health-ok-ink);
}

.fix-arrow {
    color: #8a919c;
    font-size: 0.75rem;
}

.fix-manual,
.fix-manual-tag {
    flex: 0 1 auto;
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.8rem;
    color: #5a6270;
}

.fix-more {
    padding: 0.2rem 0 0;
    font-size: 0.8rem;
    font-weight: 600;
}

.fix-more-groups {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.4rem 0.25rem 0;
    font-size: 0.85rem;
    color: #6c737d;
}

.fix-excluded {
    margin-top: 1rem;
    font-size: 0.875rem;
}

@media (max-width: 575.98px) {
    .fix-group-head {
        flex-wrap: wrap;
    }

    .fix-change,
    .fix-manual-tag {
        order: 3;
        max-width: 100%;
        margin-left: 1.6rem;
    }

    .fix-filter {
        flex: 1 1 100%;
        margin-left: 0;
    }
}
</style>
