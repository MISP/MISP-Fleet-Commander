<template>
<div class="org-admin">
    <header class="org-head">
        <div class="org-head-text">
            <h6 class="org-title">Organisations</h6>
            <span v-if="listed" class="org-head-note" :title="listedTitle">{{ listedLabel }}</span>
        </div>
        <div class="org-head-actions">
            <button
                type="button"
                class="btn btn-link refresh-button"
                :disabled="loading || comparing"
                title="List the organisations again, here and on the other servers of the fleet"
                aria-label="List the organisations again"
                @click="reload(true)"
            >
                <i :class="['fas', 'fa-sync', { 'fa-spin': loading || comparing }]" aria-hidden="true"></i>
            </button>
            <b-button size="sm" variant="primary" class="add-button" @click="openForm(null)">
                <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add organisation
            </b-button>
        </div>
    </header>

    <div v-if="hasFleet" :class="['fleet-strip', `fleet-strip-${fleetStripTone}`]" role="status">
        <i :class="['fas', fleetStripIcon, { 'fa-spin': comparing && !comparison }]" aria-hidden="true"></i>
        <span v-if="comparing && !comparison">
            Comparing with the {{ otherServerCount }} other server{{ otherServerCount === 1 ? "" : "s" }} of
            <strong>{{ fleetName }}</strong>…
        </span>
        <span v-else-if="comparisonError">Could not compare with the rest of the fleet: {{ comparisonError }}</span>
        <span v-else-if="comparison">
            Compared by UUID with {{ comparison.compared.length }} other server{{ comparison.compared.length === 1 ? "" : "s" }}
            of <strong>{{ fleetName }}</strong>.
            <template v-if="mismatchCount > 0">
                <button type="button" class="btn btn-link inline-link" @click="showAttentionOnly">
                    {{ mismatchCount }} organisation{{ mismatchCount === 1 ? "" : "s" }} differ{{ mismatchCount === 1 ? "s" : "" }}
                </button>.
            </template>
            <template v-else> No name or UUID differs.</template>
            <template v-if="comparison.unavailable.length > 0">
                <span class="fleet-unavailable" :title="unavailableTitle">{{ comparison.unavailable.length }} server{{ comparison.unavailable.length === 1 ? "" : "s" }} could not be listed</span>.
            </template>
        </span>
    </div>

    <div class="org-toolbar">
        <div class="scope-segments" role="group" aria-label="Which organisations">
            <button
                v-for="option in scopeOptions"
                :key="option.value"
                type="button"
                :class="['scope-segment', { active: scope === option.value }]"
                :aria-pressed="scope === option.value ? 'true' : 'false'"
                @click="scope = option.value"
            >
                {{ option.label }}<span class="segment-count">{{ counts[option.value] }}</span>
            </button>
        </div>
        <button
            type="button"
            :class="['attention-toggle', { active: attentionOnly, empty: attentionCount === 0 }]"
            :aria-pressed="attentionOnly ? 'true' : 'false'"
            :disabled="attentionCount === 0 && !attentionOnly"
            title="Names or UUIDs that differ in the fleet, local organisations without users, likely duplicates"
            @click="attentionOnly = !attentionOnly"
        >
            <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
            Needs attention<span class="segment-count">{{ attentionCount }}</span>
        </button>
        <div class="search-box">
            <i class="fas fa-search" aria-hidden="true"></i>
            <input
                v-model="search"
                type="search"
                class="form-control form-control-sm"
                placeholder="Name, UUID, type, sector…"
                aria-label="Search the organisations"
            >
        </div>
    </div>

    <div v-if="loading && !listed" class="org-state" role="status">
        <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Listing the organisations of {{ server.name }}…
    </div>
    <div v-else-if="error && !listed" class="org-state org-error" role="alert">
        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
        Could not list the organisations: {{ error }}
        <button type="button" class="btn btn-link inline-link" @click="reload(true)">Try again</button>
    </div>
    <template v-else-if="listed">
        <div class="table-frame">
            <table class="org-table">
                <thead>
                    <tr>
                        <th v-for="column in visibleColumns" :key="column.key" :class="['col-' + column.key]" scope="col"
                            :aria-sort="sort.key === column.key ? (sort.desc ? 'descending' : 'ascending') : 'none'">
                            <button type="button" class="sort-button" @click="sortBy(column.key)">
                                {{ column.label }}
                                <i :class="['fas', sortIcon(column.key)]" aria-hidden="true"></i>
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-if="pageRows.length === 0">
                        <td :colspan="visibleColumns.length" class="no-rows">
                            {{ rows.length === 0 ? "This server has no organisations." : "No organisation matches." }}
                            <button v-if="filtersActive" type="button" class="btn btn-link inline-link" @click="clearFilters">Clear the filters</button>
                        </td>
                    </tr>
                    <tr
                        v-for="row in pageRows"
                        :key="row.org.uuid"
                        :class="['org-row', { 'just-saved': row.org.uuid === highlightUuid }]"
                        tabindex="0"
                        @click="openDetail(row)"
                        @keydown.enter.prevent="openDetail(row)"
                    >
                        <td class="col-name">
                            <div class="name-line">
                                <span class="org-name">{{ row.org.name }}</span>
                                <span :class="['kind-badge', row.org.local ? 'kind-local' : 'kind-external']">{{ row.org.local ? "Local" : "External" }}</span>
                                <span v-if="row.sync.length > 0" class="sync-badge" :title="row.sync.map(reason => reason.text).join('\n')">
                                    <i class="fas fa-sync-alt" aria-hidden="true"></i> Sync
                                </span>
                            </div>
                            <ul v-if="row.flags.length > 0" class="flag-list">
                                <li v-for="(flag, index) in row.flags.slice(0, 2)" :key="flag.code + index" :class="['flag', `flag-${flag.tone}`]">
                                    <i :class="['fas', flag.tone === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle']" aria-hidden="true"></i>
                                    {{ flag.text }}
                                </li>
                                <li v-if="row.flags.length > 2" class="flag flag-more">+{{ row.flags.length - 2 }} more</li>
                            </ul>
                        </td>
                        <td class="col-uuid"><code :title="row.org.uuid">{{ row.org.uuid.slice(0, 8) }}</code></td>
                        <td class="col-type">{{ row.org.type || "—" }}</td>
                        <td class="col-sector">{{ row.org.sector || "—" }}</td>
                        <td class="col-nationality">{{ row.org.nationality || "—" }}</td>
                        <td class="col-users">
                            <span v-if="row.users === null" class="muted">—</span>
                            <span v-else :class="{ muted: row.users === 0 }">{{ row.users }}</span>
                        </td>
                        <td v-if="hasFleet" class="col-fleet">
                            <span v-if="!row.standing && comparing" class="fleet-chip fleet-loading" aria-label="Comparing">
                                <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i>
                            </span>
                            <span v-else-if="!row.standing" class="muted">—</span>
                            <span
                                v-else
                                :class="['fleet-chip', `fleet-${row.standing.tone}`]"
                                :title="fleetChipTitle(row.standing)"
                            >
                                <i v-if="row.standing.tone === 'warning'" class="fas fa-exclamation-triangle" aria-hidden="true"></i>
                                <i v-else-if="row.standing.tone === 'ok'" class="fas fa-check" aria-hidden="true"></i>
                                {{ row.standing.present }}/{{ row.standing.known }}
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <footer v-if="filteredRows.length > perPage" class="org-pager">
            <span class="pager-note">{{ pageStart + 1 }}–{{ Math.min(pageStart + perPage, filteredRows.length) }} of {{ filteredRows.length }}</span>
            <b-pagination
                v-model="currentPage"
                class="mb-0"
                size="sm"
                :per-page="perPage"
                :total-rows="filteredRows.length"
                aria-label="Pages of organisations"
            ></b-pagination>
        </footer>
    </template>

    <OrganisationDetailModal
        :server="server"
        :row="selectedRow"
        :has-fleet="hasFleet"
        :comparing="comparing"
        @show-users="showUsers"
        @edit="openForm"
        @copy="openCopy"
        @baseline="openBaseline"
    ></OrganisationDetailModal>
    <OrganisationFormModal
        :server="server"
        :org="formOrg"
        :organisations="organisations"
        :sync-reasons="formOrg ? syncOf(formOrg) : []"
        @saved="onSaved"
    ></OrganisationFormModal>
    <OrganisationCopyModal
        :server="server"
        :row="copyRow"
        :comparison="comparison"
        @done="onCopyDone"
    ></OrganisationCopyModal>
    <OrganisationBaselineModal
        :server="server"
        :org="baselineOrg"
    ></OrganisationBaselineModal>
</div>
</template>

<script>
import { mapGetters } from "vuex"
import api from "@/api/organisations"
import {
    attentionFlags, fleetStanding, matchesSearch, nearDuplicates, syncIndex, syncReasonsFrom, userCountOf,
    usersByOrganisation,
} from "@/helpers/organisations"
import OrganisationDetailModal from "@/views/servers/elements/mispRemoteAdministration/organisations/OrganisationDetailModal.vue"
import OrganisationFormModal from "@/views/servers/elements/mispRemoteAdministration/organisations/OrganisationFormModal.vue"
import OrganisationCopyModal from "@/views/servers/elements/mispRemoteAdministration/organisations/OrganisationCopyModal.vue"
import OrganisationBaselineModal from "@/views/servers/elements/mispRemoteAdministration/organisations/OrganisationBaselineModal.vue"

const COLUMNS = [
    { key: "name", label: "Name" },
    { key: "uuid", label: "UUID" },
    { key: "type", label: "Type" },
    { key: "sector", label: "Sector" },
    { key: "nationality", label: "Nationality" },
    { key: "users", label: "Users" },
    { key: "fleet", label: "Fleet" },
]

export default {
    name: "orgAdministration",
    components: {
        OrganisationDetailModal,
        OrganisationFormModal,
        OrganisationCopyModal,
        OrganisationBaselineModal,
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            listed: null,
            loading: false,
            error: null,
            comparison: null,
            comparing: false,
            comparisonError: null,
            users: null,
            scope: "all",
            attentionOnly: false,
            search: "",
            sort: { key: "name", desc: false },
            currentPage: 1,
            perPage: 50,
            selectedUuid: null,
            // The organisation just added or edited, shown and highlighted once listed again
            highlightUuid: null,
            highlightTimer: null,
            formOrg: null,
            copyRow: null,
            baselineOrg: null,
            now: Math.floor(Date.now() / 1000),
            clock: null,
        }
    },
    computed: {
        ...mapGetters({
            linksOfServer: "connections/linksOfServer",
        }),
        organisations() {
            return this.listed ? this.listed.organisations : []
        },
        fleetName() {
            return (this.server.fleet && this.server.fleet.name) || "this fleet"
        },
        // Known from the store before the comparison answers; the comparison is authoritative once there
        otherServerCount() {
            if (this.comparison) {
                return this.comparison.compared.length + this.comparison.unavailable.length
            }
            const fleetID = this.server.fleet && this.server.fleet.id
            return Object.values(this.$store.state.servers.servers)
                .filter(other => other.id !== this.server.id && other.fleet && other.fleet.id === fleetID).length
        },
        hasFleet() {
            return this.otherServerCount > 0
        },
        serverNames() {
            const names = {}
            if (this.comparison) {
                this.comparison.compared.concat(this.comparison.unavailable).forEach(other => { names[other.id] = other.name })
            }
            return names
        },
        links() {
            return this.linksOfServer(this.server.id)
        },
        userCounts() {
            return this.users ? usersByOrganisation(this.users) : null
        },
        duplicates() {
            return nearDuplicates(this.organisations)
        },
        syncReasonIndex() {
            return syncIndex({
                outgoing: this.links.outgoing,
                incoming: this.links.incoming,
                users: this.users || [],
                serverNames: this.serverNames,
            })
        },
        rows() {
            return this.organisations.map((org) => {
                const standing = fleetStanding(org, this.comparison, this.serverNames)
                const users = userCountOf(org, this.userCounts)
                return Object.freeze({
                    org,
                    standing,
                    users,
                    sync: this.syncOf(org),
                    flags: attentionFlags(org, { standing, userCount: users, duplicates: this.duplicates[org.id] || [] }),
                })
            })
        },
        counts() {
            const local = this.organisations.filter(org => org.local).length
            return { all: this.organisations.length, local, external: this.organisations.length - local }
        },
        scopeOptions() {
            return [
                { value: "all", label: "All" },
                { value: "local", label: "Local" },
                { value: "external", label: "External" },
            ]
        },
        attentionCount() {
            return this.rows.filter(row => row.flags.length > 0).length
        },
        mismatchCount() {
            return this.rows.filter(row => row.standing && row.standing.mismatches > 0).length
        },
        filtersActive() {
            return this.scope !== "all" || this.attentionOnly || this.search.trim() !== ""
        },
        filteredRows() {
            const rows = this.rows.filter(row =>
                (this.scope === "all" || (this.scope === "local") === row.org.local) &&
                (!this.attentionOnly || row.flags.length > 0) &&
                matchesSearch(row.org, this.search))
            const key = this.sort.key
            const value = (row) => {
                if (key === "users") {
                    return row.users === null ? -1 : row.users
                }
                if (key === "fleet") {
                    return row.standing ? row.standing.rank : Infinity
                }
                return String(row.org[key] || "").toLowerCase()
            }
            const direction = this.sort.desc ? -1 : 1
            return rows.slice().sort((a, b) => {
                const left = value(a)
                const right = value(b)
                const order = typeof left === "number" ? left - right : left.localeCompare(right)
                return order * direction || a.org.name.localeCompare(b.org.name)
            })
        },
        pageStart() {
            return (this.currentPage - 1) * this.perPage
        },
        pageRows() {
            return this.filteredRows.slice(this.pageStart, this.pageStart + this.perPage)
        },
        visibleColumns() {
            return COLUMNS.filter(column => column.key !== "fleet" || this.hasFleet)
        },
        selectedRow() {
            return this.selectedUuid === null ? null : this.rows.find(row => row.org.uuid === this.selectedUuid) || null
        },
        listedLabel() {
            if (!this.listed) {
                return ""
            }
            const seconds = Math.max(0, this.now - this.listed.fetched_at)
            if (seconds < 60) {
                return "listed just now"
            }
            const minutes = Math.round(seconds / 60)
            return minutes < 60 ? `listed ${minutes} min ago` : `listed ${Math.round(minutes / 60)} h ago`
        },
        listedTitle() {
            return this.listed ? `Listed from MISP on ${new Date(this.listed.fetched_at * 1000).toLocaleString()}. Lists are kept 10 minutes; the refresh button lists them again.` : ""
        },
        fleetStripTone() {
            if (this.comparisonError) {
                return "error"
            }
            if (this.comparison && this.mismatchCount > 0) {
                return "warning"
            }
            return "neutral"
        },
        fleetStripIcon() {
            if (this.comparing && !this.comparison) {
                return "fa-circle-notch"
            }
            if (this.comparisonError || this.mismatchCount > 0) {
                return "fa-exclamation-triangle"
            }
            return "fa-network-wired"
        },
        unavailableTitle() {
            return this.comparison ? this.comparison.unavailable.map(other => `${other.name}: ${other.error}`).join("\n") : ""
        },
    },
    watch: {
        scope() {
            this.currentPage = 1
        },
        attentionOnly() {
            this.currentPage = 1
        },
        search() {
            this.currentPage = 1
        },
        "server.id"() {
            this.reload(false)
        },
    },
    methods: {
        syncOf(org) {
            return syncReasonsFrom(this.syncReasonIndex, org)
        },
        reload(refresh) {
            this.loadOrganisations(refresh)
            this.loadComparison(refresh)
            this.loadUsers()
        },
        loadOrganisations(refresh = false) {
            this.loading = true
            this.error = null
            return api.index(this.server.id, { refresh })
                .then((listed) => {
                    listed.organisations = Object.freeze(listed.organisations)
                    this.listed = listed
                    this.now = Math.floor(Date.now() / 1000)
                })
                .catch((error) => {
                    this.error = error.message
                    if (this.listed) {
                        this.$bvToast.toast(error.message, { title: "Could not list the organisations again", variant: "danger" })
                    }
                })
                .finally(() => { this.loading = false })
        },
        // Asked even when the store knows no other server of the fleet (page opened directly): the answer says
        loadComparison(refresh = false) {
            this.comparing = true
            this.comparisonError = null
            return api.fleet(this.server.id, { refresh })
                .then((comparison) => { this.comparison = Object.freeze(comparison) })
                .catch((error) => { this.comparisonError = error.message })
                .finally(() => { this.comparing = false })
        },
        loadUsers() {
            // For the user counts MISP may not give, and for the sync marks: the tab works without them
            this.$store.dispatch("servers/getUsers", this.server.id)
                .then(() => {
                    const users = this.$store.state.servers.server_users[this.server.id]
                    this.users = Array.isArray(users) ? Object.freeze(users.slice()) : null
                })
                .catch(() => { this.users = null })
            this.$store.dispatch("connections/getConnections").catch(() => {})
        },
        sortBy(key) {
            if (this.sort.key === key) {
                this.sort = { key, desc: !this.sort.desc }
            } else {
                this.sort = { key, desc: key === "users" }
            }
        },
        sortIcon(key) {
            if (this.sort.key !== key) {
                return "fa-sort sort-idle"
            }
            return this.sort.desc ? "fa-sort-down" : "fa-sort-up"
        },
        fleetChipTitle(standing) {
            const parts = [`On ${standing.present} of the ${standing.known} servers compared, this one included`]
            if (standing.mismatches > 0) {
                parts.push(`${standing.mismatches} with another name or UUID`)
            }
            if (standing.unknown > 0) {
                parts.push(`${standing.unknown} more could not be listed`)
            }
            return parts.join(" · ")
        },
        showAttentionOnly() {
            this.attentionOnly = true
        },
        clearFilters() {
            this.scope = "all"
            this.attentionOnly = false
            this.search = ""
        },
        openDetail(row) {
            this.selectedUuid = row.org.uuid
            this.$nextTick(() => this.$bvModal.show("modal-organisation-detail"))
        },
        openForm(org) {
            this.formOrg = org
            this.$nextTick(() => this.$bvModal.show("modal-organisation-form"))
        },
        openCopy(row) {
            this.copyRow = row
            this.$nextTick(() => this.$bvModal.show("modal-organisation-copy"))
        },
        openBaseline(org) {
            this.baselineOrg = org
            this.$nextTick(() => this.$bvModal.show("modal-organisation-baseline"))
        },
        showUsers(org) {
            this.$bvModal.hide("modal-organisation-detail")
            this.$emit("show-users", { id: org.id, name: org.name })
        },
        onSaved(saved) {
            // The backend dropped its cached list: list again, and compare again (a name or UUID may have changed)
            this.loadOrganisations(false).then(() => {
                if (saved && saved.uuid) {
                    this.reveal(saved.uuid)
                }
            })
            this.loadComparison(false)
        },
        // Bring an organisation into view: its page (filters cleared if they hide it), highlighted, its detail open
        reveal(uuid) {
            let index = this.filteredRows.findIndex(row => row.org.uuid === uuid)
            if (index === -1 && this.rows.some(row => row.org.uuid === uuid)) {
                this.clearFilters()
                index = this.filteredRows.findIndex(row => row.org.uuid === uuid)
            }
            if (index === -1) {
                return
            }
            this.$nextTick(() => {
                this.currentPage = Math.floor(index / this.perPage) + 1
                this.highlightUuid = uuid
                clearTimeout(this.highlightTimer)
                this.highlightTimer = setTimeout(() => { this.highlightUuid = null }, 2500)
                this.selectedUuid = uuid
                this.$bvModal.show("modal-organisation-detail")
            })
        },
        onCopyDone() {
            this.loadComparison(false)
        },
    },
    created() {
        this.reload(false)
        this.clock = setInterval(() => { this.now = Math.floor(Date.now() / 1000) }, 30000)
    },
    beforeDestroy() {
        clearInterval(this.clock)
        clearTimeout(this.highlightTimer)
    },
}
</script>

<style scoped>
.org-admin {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.org-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    margin-bottom: 0.6rem;
}

.org-head-text {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.75rem;
    min-width: 0;
}

.org-title {
    margin: 0;
    font-size: 1.1em;
    font-weight: 700;
}

.org-head-note {
    color: #6c757d;
    font-variant-numeric: tabular-nums;
}

.org-head-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.refresh-button {
    padding: 0.15rem 0.45rem;
    color: #6c757d;
}

.refresh-button:hover,
.refresh-button:focus {
    color: var(--var-color-lapislazuli);
}

.add-button {
    white-space: nowrap;
}

.fleet-strip {
    display: flex;
    align-items: baseline;
    gap: 0.55em;
    margin-bottom: 0.75rem;
    padding: 0.45rem 0.75rem;
    border-left: 3px solid var(--health-info);
    border-radius: 0 0.25rem 0.25rem 0;
    background: var(--health-info-tint);
    color: #2f3b45;
}

.fleet-strip > i {
    color: var(--health-info-ink);
}

.fleet-strip-warning {
    border-left-color: var(--health-warning);
    background: var(--health-warning-tint);
}

.fleet-strip-warning > i {
    color: var(--health-warning-ink);
}

.fleet-strip-error {
    border-left-color: var(--health-critical);
    background: var(--health-critical-tint);
}

.fleet-strip-error > i {
    color: var(--health-critical-ink);
}

.fleet-unavailable {
    margin-left: 0.25em;
    color: #6c757d;
    text-decoration: underline dotted;
    cursor: help;
}

.inline-link {
    padding: 0;
    border: 0;
    font-size: inherit;
    vertical-align: baseline;
}

.org-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin-bottom: 0.6rem;
}

.scope-segments {
    display: inline-flex;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    overflow: hidden;
}

.scope-segment,
.attention-toggle {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25rem 0.65rem;
    border: 0;
    background: #fff;
    color: #495057;
    font-size: 0.8125rem;
    line-height: 1.5;
}

.scope-segment + .scope-segment {
    border-left: 1px solid #ced4da;
}

.scope-segment:hover {
    background: #f4f6f8;
}

.scope-segment.active {
    background: var(--var-color-lapislazuli);
    color: #fff;
}

.segment-count {
    min-width: 1.4em;
    padding: 0 0.35em;
    border-radius: 0.6em;
    background: rgba(0, 0, 0, 0.07);
    font-size: 0.9em;
    font-variant-numeric: tabular-nums;
    text-align: center;
}

.active .segment-count {
    background: rgba(255, 255, 255, 0.22);
}

.attention-toggle {
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
}

.attention-toggle i {
    color: var(--health-warning-ink);
}

.attention-toggle:hover:not(:disabled) {
    background: var(--health-warning-tint);
}

.attention-toggle.active {
    border-color: var(--health-warning);
    background: var(--health-warning-tint);
    color: #5c4300;
    font-weight: 600;
}

.attention-toggle:disabled {
    opacity: 0.55;
}

.attention-toggle.empty i {
    color: inherit;
}

.search-box {
    position: relative;
    flex: 1 1 14rem;
    max-width: 22rem;
    margin-left: auto;
}

.search-box > i {
    position: absolute;
    top: 50%;
    left: 0.6rem;
    transform: translateY(-50%);
    color: #9aa1a7;
    font-size: 0.8em;
    pointer-events: none;
}

.search-box input {
    padding-left: 1.8rem;
}

.org-state {
    padding: 1.5rem 0.5rem;
    color: #6c757d;
    text-align: center;
}

.org-error {
    color: var(--health-critical-ink);
}

.table-frame {
    overflow-x: auto;
    border: 1px solid var(--health-rule);
    border-radius: 0.25rem;
}

.org-table {
    width: 100%;
    border-collapse: collapse;
}

.org-table th {
    position: sticky;
    top: 0;
    padding: 0;
    border-bottom: 1px solid #d5dae0;
    background: #f7f8fa;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #5a6270;
    white-space: nowrap;
}

.sort-button {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    width: 100%;
    padding: 0.45rem 0.6rem;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    letter-spacing: inherit;
    text-transform: inherit;
    text-align: left;
}

.sort-button:hover {
    color: var(--var-color-yankeesblue);
}

.sort-idle {
    opacity: 0.3;
}

.org-table td {
    padding: 0.45rem 0.6rem;
    border-top: 1px solid var(--health-rule);
    vertical-align: top;
}

.org-row {
    cursor: pointer;
}

.org-row:hover,
.org-row:focus {
    background: var(--health-focus-bg);
    outline: none;
}

.org-row.just-saved {
    animation: just-saved 2.5s ease-out;
}

@keyframes just-saved {
    0%, 40% {
        background: #e3f1e8;
    }
    100% {
        background: transparent;
    }
}

.org-row:focus-visible {
    box-shadow: inset 3px 0 0 var(--var-color-lapislazuli);
}

.col-name {
    min-width: 14rem;
}

.name-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem 0.45rem;
}

.org-name {
    font-weight: 600;
    overflow-wrap: anywhere;
}

.kind-badge,
.sync-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    padding: 0 0.45em;
    border-radius: 0.2rem;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.6;
    white-space: nowrap;
}

.kind-local {
    background: #e7f0f7;
    color: #1f5a7f;
}

.kind-external {
    background: #f1f3f5;
    color: #5f6873;
}

.sync-badge {
    background: #efeaf7;
    color: #553d82;
    cursor: help;
}

.flag-list {
    margin: 0.2rem 0 0;
    padding: 0;
    list-style: none;
}

.flag {
    font-size: 0.8rem;
    line-height: 1.45;
}

.flag i {
    width: 1em;
    margin-right: 0.15em;
    font-size: 0.85em;
}

.flag-warning {
    color: var(--health-warning-ink);
}

.flag-info {
    color: var(--health-info-ink);
}

.flag-more {
    color: #6c757d;
}

.col-uuid code {
    color: #5f6873;
    font-size: 0.8rem;
}

.col-users {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

th.col-users .sort-button {
    justify-content: flex-end;
}

.muted {
    color: #9aa1a7;
}

.fleet-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    padding: 0 0.5em;
    border: 1px solid #d5dae0;
    border-radius: 1em;
    background: #fff;
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    cursor: help;
}

.fleet-ok {
    border-color: #b9dfc7;
    background: #ebf6ef;
    color: var(--health-ok-ink);
}

.fleet-warning {
    border-color: #f3d27a;
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
    font-weight: 600;
}

.fleet-partial {
    color: #5f6873;
}

.fleet-loading {
    border-style: dashed;
    color: #9aa1a7;
}

.no-rows {
    padding: 1.5rem 0.5rem !important;
    color: #6c757d;
    text-align: center;
}

.org-pager {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.6rem;
}

.pager-note {
    color: #6c757d;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 1199.98px) {
    .col-sector,
    .col-nationality {
        display: none;
    }
}

@media (max-width: 767.98px) {
    .col-uuid,
    .col-type {
        display: none;
    }

    .col-name {
        min-width: 10rem;
    }

    .search-box {
        flex-basis: 100%;
        max-width: none;
        margin-left: 0;
    }
}

@media (max-width: 575.98px) {
    .col-users {
        display: none;
    }

    .col-name {
        min-width: 0;
    }
}
</style>
