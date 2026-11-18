<template>
<Layout name="LayoutDefault">
    <div class="page-container attention-page">
        <header class="attention-header">
            <div>
                <h1 class="attention-title">Needs attention</h1>
                <p class="attention-subtitle">{{ subtitle }}</p>
            </div>
            <b-button-group size="sm" class="grouping" role="group" aria-label="Group issues">
                <b-button
                    :variant="groupBy === 'server' ? 'primary' : 'outline-primary'"
                    :aria-pressed="groupBy === 'server' ? 'true' : 'false'"
                    @click="setGroupBy('server')"
                ><i class="fas fa-server mr-1" aria-hidden="true"></i>By server</b-button>
                <b-button
                    :variant="groupBy === 'rule' ? 'primary' : 'outline-primary'"
                    :aria-pressed="groupBy === 'rule' ? 'true' : 'false'"
                    @click="setGroupBy('rule')"
                ><i class="fas fa-layer-group mr-1" aria-hidden="true"></i>By issue type</b-button>
            </b-button-group>
        </header>

        <div v-if="!loaded && loading" class="attention-state" aria-live="polite">
            <b-spinner small class="mr-2"></b-spinner>Checking your servers
        </div>

        <b-alert v-else-if="!loaded && error" show variant="danger" class="attention-error">
            <strong>Could not load the health of your servers.</strong> {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="reload">Try again</b-button>
        </b-alert>

        <div v-else-if="loaded && allServers.length === 0" class="attention-state attention-empty">
            <i class="fas fa-server state-icon" aria-hidden="true"></i>
            <h2>No servers to watch yet</h2>
            <p>Add MISP servers to a fleet: their issues will show up here.</p>
            <b-button variant="primary" :to="{ name: 'home' }">Go to your fleets</b-button>
        </div>

        <template v-else-if="loaded">
            <section class="overview" aria-label="Overview">
                <div class="severity-filters" role="group" aria-label="Filter by severity">
                    <button
                        v-for="severity in severities"
                        :key="severity"
                        type="button"
                        :class="['severity-toggle', `sev-${severity}`, { active: selectedSeverities.includes(severity), empty: scopeCounts[severity] === 0 }]"
                        :aria-pressed="selectedSeverities.includes(severity) ? 'true' : 'false'"
                        @click="toggle(selectedSeverities, severity)"
                    >
                        <i :class="[severityMeta[severity].icon, 'toggle-icon']" aria-hidden="true"></i>
                        <span class="toggle-count">{{ scopeCounts[severity] }}</span>
                        <span class="toggle-label">{{ scopeCounts[severity] === 1 ? severityMeta[severity].label : severityMeta[severity].plural }}</span>
                    </button>
                </div>
                <div class="fleet-pulse">
                    <div class="pulse-caption">
                        <strong>{{ healthyCount }}</strong> of {{ scopeServers.length }} {{ scopeServers.length === 1 ? "server" : "servers" }} healthy
                    </div>
                    <div class="pulse-cells" role="group" aria-label="Servers, by their most severe issue">
                        <template v-for="server in pulseServers">
                            <button
                                v-if="server.worst"
                                :key="server.id"
                                type="button"
                                :class="['pulse-cell', `sev-${server.worst}`]"
                                :title="`${server.name}: ${severityMeta[server.worst].label.toLowerCase()}`"
                                :aria-label="`${server.name}: ${severityMeta[server.worst].label.toLowerCase()}. Show its issues`"
                                @click="jumpToServer(server.id)"
                            ></button>
                            <span
                                v-else
                                :key="server.id"
                                class="pulse-cell healthy"
                                :title="`${server.name}: healthy`"
                                :aria-label="`${server.name}: healthy`"
                            ></span>
                        </template>
                    </div>
                </div>
            </section>

            <div class="filter-bar">
                <b-dropdown
                    size="sm"
                    variant="outline-secondary"
                    class="fleet-filter"
                    :text="fleetFilterText"
                >
                    <b-dropdown-form form-class="px-3 py-2">
                        <b-form-checkbox
                            v-for="fleet in fleetOptions"
                            :key="fleet.id"
                            :checked="selectedFleets.includes(fleet.id)"
                            class="text-nowrap mb-1"
                            @change="toggle(selectedFleets, fleet.id)"
                        >
                            {{ fleet.name }}
                            <span class="text-muted small ml-1">{{ fleet.serverCount }} {{ fleet.serverCount === 1 ? "server" : "servers" }}</span>
                        </b-form-checkbox>
                    </b-dropdown-form>
                    <b-dropdown-divider v-if="selectedFleets.length > 0"></b-dropdown-divider>
                    <b-dropdown-item-button v-if="selectedFleets.length > 0" @click="selectedFleets = []">Show all fleets</b-dropdown-item-button>
                </b-dropdown>

                <div v-if="categoryOptions.length > 0" class="category-chips" role="group" aria-label="Filter by category">
                    <button
                        v-for="category in categoryOptions"
                        :key="category.name"
                        type="button"
                        :class="['chip', { active: selectedCategories.includes(category.name) }]"
                        :aria-pressed="selectedCategories.includes(category.name) ? 'true' : 'false'"
                        @click="toggle(selectedCategories, category.name)"
                    >
                        {{ category.label }} <span class="chip-count">{{ category.count }}</span>
                    </button>
                </div>

                <b-form-checkbox
                    v-model="showAcked"
                    switch
                    class="acked-switch"
                    :disabled="scopeAckedCount === 0 && !showAcked"
                >
                    Show acknowledged <span class="text-muted">({{ scopeAckedCount }})</span>
                </b-form-checkbox>
            </div>

            <div v-if="scopeServers.length === 0" class="attention-state attention-empty">
                <i class="fas fa-server state-icon" aria-hidden="true"></i>
                <h2>{{ selectedFleets.length === 1 ? "This fleet has no servers" : "These fleets have no servers" }}</h2>
                <b-button variant="outline-primary" size="sm" @click="selectedFleets = []">Show all fleets</b-button>
            </div>

            <div v-else-if="scopeActiveIssues.length === 0 && !showAcked" class="attention-state attention-healthy">
                <i class="fas fa-circle-check state-icon" aria-hidden="true"></i>
                <h2>{{ scopeServers.length === 1 ? "Your server is healthy" : `All ${scopeServers.length} servers are healthy` }}</h2>
                <p v-if="newestRefresh">
                    <span :title="newestRefreshTitle">Last refreshed {{ newestRefreshText }}.</span>
                    Servers are tested and refreshed in the background.
                </p>
                <b-button v-if="scopeAckedCount > 0" variant="link" @click="showAcked = true">
                    Show {{ scopeAckedCount }} acknowledged {{ scopeAckedCount === 1 ? "issue" : "issues" }}
                </b-button>
            </div>

            <div v-else-if="visibleIssues.length === 0" class="attention-state">
                <h2>No issues match these filters</h2>
                <b-button variant="outline-primary" size="sm" @click="clearFilters">Clear filters</b-button>
            </div>

            <ul v-else-if="groupBy === 'server'" class="attention-list" aria-label="Issues by server" @keydown="navigate">
                <li
                    v-for="group in serverGroups"
                    :key="group.server_id"
                    :id="`attention-server-${group.server_id}`"
                    :class="['server-group', `sev-${group.worst}`]"
                >
                    <div class="group-header" tabindex="0" data-nav-item
                        :aria-label="`${group.server_name}, ${group.countsText}`"
                        @keydown.enter.self="openServer(group.server_id)">
                        <div class="group-title">
                            <router-link :to="serverLink(group.server_id)" class="server-name" tabindex="-1">{{ group.server_name }}</router-link>
                            <span class="group-fleet">{{ group.fleet_name }}</span>
                            <span :class="['group-counts', `ink-${group.worst}`]">{{ group.countsText }}</span>
                        </div>
                        <div class="group-actions">
                            <b-button size="sm" variant="link" :disabled="!!pending[group.server_id]" @click="testConnection(group.server_id)">
                                <i :class="pending[group.server_id] === 'test_connection' ? 'fas fa-circle-notch fa-spin fa-fw' : 'fas fa-plug fa-fw'" aria-hidden="true"></i>
                                Test connection
                            </b-button>
                            <b-button size="sm" variant="link" :disabled="!!pending[group.server_id]" @click="refresh(group.server_id)">
                                <i :class="pending[group.server_id] === 'refresh' ? 'fas fa-circle-notch fa-spin fa-fw' : 'fas fa-rotate fa-fw'" aria-hidden="true"></i>
                                Refresh
                            </b-button>
                            <b-button size="sm" variant="link" :to="serverLink(group.server_id)">
                                <i class="fas fa-server fa-fw" aria-hidden="true"></i>
                                Open server
                            </b-button>
                        </div>
                    </div>
                    <ul class="issue-list">
                        <IssueRow
                            v-for="issue in shownIssues(group)"
                            :key="issue.id"
                            :issue="issue"
                            :now="now"
                            :pending="pending[issue.server_id] || null"
                            @action="runAction"
                            @open="openIssue"
                            @ack="openAck"
                            @unack="unacknowledge"
                        ></IssueRow>
                        <li v-if="hiddenCount(group) > 0" class="issue-more">
                            <span class="issue-more-count">{{ hiddenCount(group) }} more {{ hiddenCount(group) === 1 ? "issue" : "issues" }}</span>
                            <b-button size="sm" variant="link" class="issue-more-button" @click="showMore(group)">
                                Show {{ Math.min(moreStep, hiddenCount(group)) }} more
                            </b-button>
                        </li>
                    </ul>
                </li>
            </ul>

            <ul v-else class="attention-list" aria-label="Issues by type" @keydown="navigate">
                <li
                    v-for="group in ruleGroups"
                    :key="group.rule"
                    :class="['server-group', `sev-${group.worst}`]"
                >
                    <button
                        type="button"
                        class="group-header type-header"
                        data-nav-item
                        :aria-expanded="isExpanded(group.rule) ? 'true' : 'false'"
                        @click="toggle(expandedRules, group.rule)"
                    >
                        <i :class="['fas', isExpanded(group.rule) ? 'fa-chevron-down' : 'fa-chevron-right', 'chevron']" aria-hidden="true"></i>
                        <span class="group-title">
                            <span class="server-name">{{ group.label }}</span>
                            <span class="group-fleet">{{ group.serverCount }} {{ group.serverCount === 1 ? "server" : "servers" }}</span>
                            <span :class="['group-counts', `ink-${group.worst}`]">{{ group.countsText }}</span>
                        </span>
                    </button>
                    <ul v-if="isExpanded(group.rule)" class="issue-list">
                        <IssueRow
                            v-for="issue in shownIssues(group)"
                            :key="issue.id"
                            :issue="issue"
                            :now="now"
                            show-server
                            :pending="pending[issue.server_id] || null"
                            @action="runAction"
                            @open="openIssue"
                            @ack="openAck"
                            @unack="unacknowledge"
                        ></IssueRow>
                        <li v-if="hiddenCount(group) > 0" class="issue-more">
                            <span class="issue-more-count">{{ hiddenCount(group) }} more {{ hiddenCount(group) === 1 ? "issue" : "issues" }}</span>
                            <b-button size="sm" variant="link" class="issue-more-button" @click="showMore(group)">
                                Show {{ Math.min(moreStep, hiddenCount(group)) }} more
                            </b-button>
                        </li>
                    </ul>
                </li>
            </ul>
        </template>

        <!-- Inside the page: the layout only renders its first child -->
        <AckModal :issue="ackTarget"></AckModal>
        <AddModal
            v-if="serverToEdit"
            :key="serverToEdit.id"
            modalAction="Edit"
            :serverForm="serverToEdit"
            @addition-success="handleEdited"
            @update:modalAction="serverToEdit = null"
        ></AddModal>
    </div>
</Layout>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import AddModal from "@/views/servers/AddModal.vue"
import moment from "moment"
import { websocketMixin } from "@/helpers/websocketMixin"
import serversApi from "@/api/servers"
import { SEVERITIES, CATEGORIES, severityRank, worstSeverity, compareIssues } from "@/store/modules/health"
import { SEVERITY_META, CATEGORY_LABELS, RULE_LABELS, countsText } from "./healthLabels"
import IssueRow from "./IssueRow.vue"
import AckModal from "./AckModal.vue"

const GROUP_BY_STORAGE_KEY = "mfc.attention.groupBy"
const NOW_TICK_MS = 30 * 1000
// Rows rendered per group at first, and how many more each "Show more" adds: a baseline drifting on every server
// can give thousands of issues, and rendering them all froze the page
const ROWS_PER_GROUP = 10
const MORE_STEP = 50

function readStoredGroupBy() {
    try {
        const value = window.localStorage.getItem(GROUP_BY_STORAGE_KEY)
        return value === "rule" ? "rule" : "server"
    } catch (e) {
        return "server"
    }
}

function countBySeverity(issues) {
    const counts = { critical: 0, warning: 0, info: 0 }
    issues.forEach((issue) => { counts[issue.severity] += 1 })
    return counts
}

export default {
    name: "TheAttention",
    mixins: [websocketMixin],
    components: {
        Layout,
        AddModal,
        IssueRow,
        AckModal,
    },
    data() {
        return {
            severities: SEVERITIES,
            severityMeta: SEVERITY_META,
            groupBy: readStoredGroupBy(),
            selectedSeverities: [],
            selectedCategories: [],
            selectedFleets: this.fleetsFromQuery(),
            showAcked: false,
            expandedRules: [],
            shownRows: {},  // group key -> rows shown, when more than ROWS_PER_GROUP
            moreStep: MORE_STEP,
            ackTarget: null,
            serverToEdit: null,
            now: Math.floor(Date.now() / 1000),
            nowTimer: null,
        }
    },
    computed: {
        ...mapState({
            summary: state => state.health.summary,
            loaded: state => state.health.loaded,
            loading: state => state.health.loading,
            error: state => state.health.error,
            pending: state => state.health.pending,
            issuesByServer: state => state.health.issuesByServer,
        }),
        ...mapGetters({
            allIssues: "health/allIssues",
            serverWorst: "health/serverWorst",
            fleetList: "fleets/fleetList",
        }),
        // Every server of the user: from the summary, plus any server that reported issues since
        allServers() {
            const servers = {}
            const summaryServers = (this.summary && this.summary.servers) || {}
            Object.entries(summaryServers).forEach(([id, server]) => {
                servers[id] = { id: Number(id), name: server.name, fleet_id: server.fleet_id }
            })
            this.allIssues.forEach((issue) => {
                if (servers[issue.server_id] === undefined) {
                    servers[issue.server_id] = { id: issue.server_id, name: issue.server_name, fleet_id: issue.fleet_id }
                }
            })
            return Object.values(servers)
        },
        scopeServers() {
            return this.allServers.filter(server => this.inFleetScope(server.fleet_id))
        },
        scopeIssues() {
            return this.allIssues.filter(issue => this.inFleetScope(issue.fleet_id))
        },
        scopeActiveIssues() {
            return this.scopeIssues.filter(issue => issue.ack === null)
        },
        scopeAckedCount() {
            return this.scopeIssues.length - this.scopeActiveIssues.length
        },
        scopeCounts() {
            return countBySeverity(this.scopeActiveIssues)
        },
        healthyCount() {
            return this.scopeServers.filter(server => !this.serverWorst[server.id]).length
        },
        pulseServers() {
            return this.scopeServers
                .map(server => Object.assign({}, server, { worst: this.serverWorst[server.id] || null }))
                .sort((a, b) => severityRank(a.worst) - severityRank(b.worst) || a.name.localeCompare(b.name))
        },
        candidateIssues() {
            const pool = this.showAcked ? this.scopeIssues : this.scopeActiveIssues
            return pool.filter(issue => this.selectedSeverities.length === 0 || this.selectedSeverities.includes(issue.severity))
        },
        categoryOptions() {
            const counts = {}
            this.candidateIssues.forEach((issue) => { counts[issue.category] = (counts[issue.category] || 0) + 1 })
            this.selectedCategories.forEach((category) => { counts[category] = counts[category] || 0 })
            return CATEGORIES
                .filter(category => counts[category] !== undefined)
                .map(category => ({ name: category, label: CATEGORY_LABELS[category] || category, count: counts[category] }))
        },
        visibleIssues() {
            return this.candidateIssues
                .filter(issue => this.selectedCategories.length === 0 || this.selectedCategories.includes(issue.category))
        },
        serverGroups() {
            const groups = {}
            this.visibleIssues.forEach((issue) => {
                if (groups[issue.server_id] === undefined) {
                    groups[issue.server_id] = {
                        key: `server:${issue.server_id}`,
                        server_id: issue.server_id, server_name: issue.server_name, fleet_name: issue.fleet_name, issues: [],
                    }
                }
                groups[issue.server_id].issues.push(issue)
            })
            return Object.values(groups)
                .map((group) => {
                    group.issues.sort(compareIssues)
                    const active = group.issues.filter(issue => issue.ack === null)
                    group.worst = worstSeverity(active.length > 0 ? active : group.issues)
                    group.countsText = countsText(countBySeverity(group.issues))
                    return group
                })
                // Stable order: live updates only move a server when its worst severity changes
                .sort((a, b) => severityRank(a.worst) - severityRank(b.worst) || a.server_name.localeCompare(b.server_name) || a.server_id - b.server_id)
        },
        ruleGroups() {
            const groups = {}
            this.visibleIssues.forEach((issue) => {
                if (groups[issue.rule] === undefined) {
                    groups[issue.rule] = { key: `rule:${issue.rule}`, rule: issue.rule, label: RULE_LABELS[issue.rule] || issue.title, issues: [] }
                }
                groups[issue.rule].issues.push(issue)
            })
            return Object.values(groups)
                .map((group) => {
                    group.issues.sort((a, b) => compareIssues(a, b) || a.server_name.localeCompare(b.server_name))
                    group.worst = worstSeverity(group.issues)
                    group.serverCount = new Set(group.issues.map(issue => issue.server_id)).size
                    group.countsText = countsText(countBySeverity(group.issues))
                    return group
                })
                .sort((a, b) => severityRank(a.worst) - severityRank(b.worst) || b.serverCount - a.serverCount || a.label.localeCompare(b.label))
        },
        fleetOptions() {
            const serverCounts = {}
            this.allServers.forEach((server) => { serverCounts[server.fleet_id] = (serverCounts[server.fleet_id] || 0) + 1 })
            const fleets = {}
            this.fleetList.forEach((fleet) => { fleets[fleet.id] = fleet.name })
            this.allIssues.forEach((issue) => {
                if (fleets[issue.fleet_id] === undefined) {
                    fleets[issue.fleet_id] = issue.fleet_name
                }
            })
            return Object.entries(fleets)
                .map(([id, name]) => ({ id: Number(id), name, serverCount: serverCounts[id] || 0 }))
                .sort((a, b) => a.name.localeCompare(b.name))
        },
        fleetFilterText() {
            if (this.selectedFleets.length === 0) {
                return "All fleets"
            }
            if (this.selectedFleets.length === 1) {
                const fleet = this.fleetOptions.find(option => option.id === this.selectedFleets[0])
                return fleet ? fleet.name : "1 fleet"
            }
            return `${this.selectedFleets.length} fleets`
        },
        newestRefresh() {
            return this.summary ? this.summary.newest_refresh : null
        },
        newestRefreshText() {
            return moment.unix(this.newestRefresh).from(moment.unix(Math.max(this.now, this.newestRefresh)))
        },
        newestRefreshTitle() {
            return moment.unix(this.newestRefresh).format("LLL")
        },
        subtitle() {
            if (!this.loaded) {
                return "Issues across all your fleets, most severe first."
            }
            const fleetCount = new Set(this.allServers.map(server => server.fleet_id)).size
            const servers = `${this.allServers.length} ${this.allServers.length === 1 ? "server" : "servers"}`
            const fleets = `${fleetCount} ${fleetCount === 1 ? "fleet" : "fleets"}`
            return `Issues across your ${servers} in ${fleets}, most severe first. Updated as servers are tested and refreshed.`
        },
    },
    watch: {
        selectedFleets(fleets) {
            const query = Object.assign({}, this.$route.query)
            if (fleets.length > 0) {
                query.fleet_id = fleets.join(",")
            } else {
                delete query.fleet_id
            }
            if (query.fleet_id !== this.$route.query.fleet_id) {
                this.$router.replace({ query }).catch(() => {})
            }
        },
        "$route.query.fleet_id"() {
            const fleets = this.fleetsFromQuery()
            if (fleets.join(",") !== this.selectedFleets.join(",")) {
                this.selectedFleets = fleets
            }
        },
        "$route.query.server_id"() {
            this.jumpFromQuery()
        },
        loaded() {
            this.jumpFromQuery()
        },
    },
    mounted() {
        this.$store.dispatch("health/init")
        this.jumpFromQuery()
        this.$store.dispatch("fleets/initFetch", { use_cache: true }).catch(() => {})
        this.nowTimer = setInterval(() => {
            this.now = Math.floor(Date.now() / 1000)
        }, NOW_TICK_MS)
    },
    beforeDestroy() {
        clearInterval(this.nowTimer)
    },
    methods: {
        fleetsFromQuery() {
            const value = this.$route.query.fleet_id
            if (!value) {
                return []
            }
            return String(value).split(",").map(id => parseInt(id, 10)).filter(id => !Number.isNaN(id))
        },
        inFleetScope(fleet_id) {
            return this.selectedFleets.length === 0 || this.selectedFleets.includes(fleet_id)
        },
        toggle(list, value) {
            const index = list.indexOf(value)
            if (index === -1) {
                list.push(value)
            } else {
                list.splice(index, 1)
            }
        },
        isExpanded(rule) {
            return this.expandedRules.includes(rule)
        },
        shownIssues(group) {
            return group.issues.slice(0, this.shownRows[group.key] || ROWS_PER_GROUP)
        },
        hiddenCount(group) {
            return Math.max(0, group.issues.length - (this.shownRows[group.key] || ROWS_PER_GROUP))
        },
        showMore(group) {
            this.$set(this.shownRows, group.key, (this.shownRows[group.key] || ROWS_PER_GROUP) + MORE_STEP)
        },
        setGroupBy(groupBy) {
            this.groupBy = groupBy
            try {
                window.localStorage.setItem(GROUP_BY_STORAGE_KEY, groupBy)
            } catch (e) {
                // Only a convenience
            }
        },
        clearFilters() {
            this.selectedSeverities = []
            this.selectedCategories = []
            this.selectedFleets = []
        },
        reload() {
            this.$store.dispatch("health/fetch")
        },
        // `org`: the organisation to show in the Organisations tab
        serverLink(server_id, tab, org) {
            const link = { name: "servers.view", params: { server_id } }
            if (tab) {
                link.query = org ? { tab, org } : { tab }
            }
            return link
        },
        openServer(server_id, tab, org) {
            this.$router.push(this.serverLink(server_id, tab, org)).catch(() => {})
        },
        openIssue(issue) {
            const action = issue.action || {}
            if (action.kind === "open_baseline") {
                this.openBaseline(issue.fleet_id, action.rule_id)
                return
            }
            if (action.kind === "open_tab") {
                this.openServer(issue.server_id, action.target, action.uuid)
                return
            }
            this.openServer(issue.server_id)
        },
        // The fleet page's Baseline tab, on the drifting rule
        openBaseline(fleet_id, rule_id) {
            this.$router.push({
                name: "fleet.view",
                params: { fleet_id },
                query: { tab: "baseline", rule: String(rule_id) },
            }).catch(() => {})
        },
        // `?server_id=` (from a health badge) opens the page on that server, once
        jumpFromQuery() {
            const server_id = parseInt(this.$route.query.server_id, 10)
            if (!this.loaded || Number.isNaN(server_id)) {
                return
            }
            const query = Object.assign({}, this.$route.query)
            delete query.server_id
            this.$router.replace({ query }).catch(() => {})
            const server = this.allServers.find(item => item.id === server_id)
            if (server && !this.inFleetScope(server.fleet_id)) {
                this.selectedFleets = []
            }
            this.jumpToServer(server_id)
        },
        jumpToServer(server_id) {
            if (this.groupBy !== "server") {
                this.setGroupBy("server")
            }
            const issues = this.issuesByServer[server_id] || []
            if (issues.length > 0 && issues.every(issue => issue.ack !== null)) {
                this.showAcked = true
            }
            this.selectedSeverities = []
            this.selectedCategories = []
            this.$nextTick(() => {
                const element = document.getElementById(`attention-server-${server_id}`)
                if (element) {
                    element.scrollIntoView({ block: "start", behavior: "smooth" })
                    const header = element.querySelector(".group-header")
                    if (header) {
                        header.focus({ preventScroll: true })
                    }
                }
            })
        },
        testConnection(server_id) {
            this.wsServerConnectionTest(server_id)
            this.$store.dispatch("health/markPending", { server_id, kind: "test_connection" })
        },
        refresh(server_id) {
            this.wsServerRefresh(server_id)
            this.$store.dispatch("health/markPending", { server_id, kind: "refresh" })
        },
        runAction(issue) {
            const action = issue.action || {}
            switch (action.kind) {
                case "test_connection":
                    this.testConnection(issue.server_id)
                    break
                case "refresh":
                    this.refresh(issue.server_id)
                    break
                case "edit_server":
                    this.openEdit(issue.server_id)
                    break
                default:
                    this.openIssue(issue)
            }
        },
        openEdit(server_id) {
            serversApi.get(
                server_id,
                (server) => {
                    this.serverToEdit = Object.assign({ authkey: "" }, server)
                    this.$nextTick(() => this.$bvModal.show("modal-add"))
                },
                (error) => {
                    this.$bvToast.toast(error, { title: "Could not open the server", variant: "danger" })
                },
            )
        },
        handleEdited() {
            // Check the new settings right away: the issue clears as soon as the test passes
            if (this.serverToEdit) {
                this.testConnection(this.serverToEdit.id)
            }
        },
        openAck(issue) {
            this.ackTarget = issue
            this.$nextTick(() => this.$bvModal.show("modal-ack-issue"))
        },
        unacknowledge(issue) {
            this.$store.dispatch("health/unacknowledge", issue)
                .catch((error) => {
                    this.$bvToast.toast(error, { title: "Could not show the issue again", variant: "danger" })
                })
        },
        // Arrow keys move between servers and issues; Enter opens the focused one
        navigate(event) {
            const keys = ["ArrowDown", "ArrowUp", "Home", "End"]
            if (!keys.includes(event.key) || !event.target.hasAttribute("data-nav-item")) {
                return
            }
            const items = Array.from(this.$el.querySelectorAll(".attention-list [data-nav-item]"))
                .filter(item => item.offsetParent !== null)
            const index = items.indexOf(event.target)
            let next = index
            if (event.key === "ArrowDown") next = Math.min(items.length - 1, index + 1)
            if (event.key === "ArrowUp") next = Math.max(0, index - 1)
            if (event.key === "Home") next = 0
            if (event.key === "End") next = items.length - 1
            if (items[next]) {
                event.preventDefault()
                items[next].focus()
            }
        },
    },
}
</script>

<style scoped>
.attention-page {
    max-width: 1180px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.attention-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1.25rem;
}

.attention-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0;
}

.attention-subtitle {
    color: #5a6270;
    margin: 0.2rem 0 0;
    max-width: 62ch;
}

/* Overview: severity counts that filter, and every server as one cell */
.overview {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 1.5rem;
    align-items: center;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}

.severity-filters {
    display: flex;
    gap: 0.5rem;
}

.severity-toggle {
    display: grid;
    grid-template-columns: auto auto;
    grid-template-areas: "icon count" "label label";
    column-gap: 0.4rem;
    align-items: center;
    min-width: 6.5rem;
    padding: 0.5rem 0.75rem;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    text-align: left;
    cursor: pointer;
    transition: background-color .12s, border-color .12s;
}

.severity-toggle:hover {
    border-color: #c5ccd6;
}

.severity-toggle:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 2px;
}

.toggle-icon {
    grid-area: icon;
    font-size: 1.1rem;
}

.toggle-count {
    grid-area: count;
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    color: var(--var-color-yankeesblue);
}

.toggle-label {
    grid-area: label;
    font-size: 0.8125rem;
    color: #5a6270;
}

.severity-toggle.sev-critical .toggle-icon { color: var(--health-critical-ink); }
.severity-toggle.sev-warning .toggle-icon { color: var(--health-warning-ink); }
.severity-toggle.sev-info .toggle-icon { color: var(--health-info-ink); }

.severity-toggle.sev-critical.active { background: var(--health-critical-tint); border-color: var(--health-critical); }
.severity-toggle.sev-warning.active { background: var(--health-warning-tint); border-color: var(--health-warning); }
.severity-toggle.sev-info.active { background: var(--health-info-tint); border-color: var(--health-info); }

.severity-toggle.empty:not(.active) .toggle-icon,
.severity-toggle.empty:not(.active) .toggle-count {
    color: #adb5bd;
}

.fleet-pulse {
    min-width: 0;
}

.pulse-caption {
    font-size: 0.875rem;
    color: #5a6270;
    margin-bottom: 0.4rem;
}

.pulse-caption strong {
    color: var(--var-color-yankeesblue);
    font-variant-numeric: tabular-nums;
}

.pulse-cells {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
}

.pulse-cell {
    display: block;
    width: 14px;
    height: 26px;
    border: 0;
    border-radius: 3px;
    padding: 0;
}

button.pulse-cell {
    cursor: pointer;
}

button.pulse-cell:hover {
    transform: translateY(-2px);
}

button.pulse-cell:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 2px;
}

.pulse-cell.sev-critical { background: var(--health-critical); }
.pulse-cell.sev-warning { background: var(--health-warning); }
.pulse-cell.sev-info { background: var(--health-info); }
.pulse-cell.healthy { background: var(--health-ok); opacity: 0.55; }

@media (prefers-reduced-motion: no-preference) {
    button.pulse-cell {
        transition: transform .12s;
    }
}

/* Filters */
.filter-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    margin-bottom: 1rem;
}

.category-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}

.chip {
    border: 1px solid #ced4da;
    background: #fff;
    border-radius: 999px;
    padding: 0.15rem 0.7rem;
    font-size: 0.8125rem;
    color: #495057;
    cursor: pointer;
}

.chip:hover {
    border-color: #9aa3ad;
}

.chip:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.chip.active {
    background: var(--var-color-yankeesblue);
    border-color: var(--var-color-yankeesblue);
    color: #fff;
}

.chip-count {
    font-variant-numeric: tabular-nums;
    opacity: 0.75;
    margin-left: 0.15rem;
}

.acked-switch {
    margin-left: auto;
    font-size: 0.875rem;
}

/* Lists */
.attention-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.attention-list ::v-deep .issue-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.issue-more {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.35rem 0.75rem 0.35rem 3.25rem;
    border-top: 1px dashed var(--health-rule);
    background: #fafbfc;
}

.issue-more-count {
    color: #6c757d;
    font-size: 0.875rem;
    font-variant-numeric: tabular-nums;
}

.issue-more-button {
    padding-top: 0.15rem;
    padding-bottom: 0.15rem;
    font-weight: 600;
}

.server-group {
    background: #fff;
    border: 1px solid var(--health-rule);
    border-left: 4px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.server-group.sev-critical { border-left-color: var(--health-critical); }
.server-group.sev-warning { border-left-color: var(--health-warning); }
.server-group.sev-info { border-left-color: var(--health-info); }

.group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    flex-wrap: wrap;
    padding: 0.55rem 0.75rem 0.55rem 1rem;
    background: #fafbfc;
    outline: none;
}

.group-header:focus-visible {
    box-shadow: inset 0 0 0 2px var(--var-color-lapislazuli);
}

.type-header {
    width: 100%;
    border: 0;
    justify-content: flex-start;
    text-align: left;
    cursor: pointer;
}

.type-header:hover {
    background: #f3f5f8;
}

.chevron {
    width: 1rem;
    color: #6c757d;
}

.group-title {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.25rem 0.75rem;
    min-width: 0;
}

.server-name {
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--var-color-yankeesblue);
}

a.server-name:hover {
    color: var(--var-color-lapislazuli);
}

.group-fleet {
    color: #6c757d;
    font-size: 0.875rem;
}

.group-counts {
    font-size: 0.875rem;
    font-weight: 600;
}

.ink-critical { color: var(--health-critical-ink); }
.ink-warning { color: var(--health-warning-ink); }
.ink-info { color: var(--health-info-ink); }

.group-actions {
    display: flex;
    flex-wrap: wrap;
}

.group-actions .btn-link {
    color: #495057;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}

.group-actions .btn-link:hover,
.group-actions .btn-link:focus {
    color: var(--var-color-lapislazuli);
}

/* States */
.attention-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #5a6270;
}

.attention-state h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin-bottom: 0.4rem;
}

.attention-healthy,
.attention-empty {
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
}

.state-icon {
    font-size: 2.5rem;
    margin-bottom: 0.75rem;
    color: #adb5bd;
}

.attention-healthy .state-icon {
    color: var(--health-ok);
}

@media (max-width: 991.98px) {
    .overview {
        grid-template-columns: minmax(0, 1fr);
        gap: 1rem;
    }
}

@media (max-width: 575.98px) {
    .attention-page {
        padding: 1rem 0.75rem 2rem;
    }

    .severity-filters {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .severity-toggle {
        min-width: 0;
    }

    .acked-switch {
        margin-left: 0;
    }
}
</style>
