<template>
<div class="ra-tab">
    <header class="ra-head">
        <div class="ra-head-text">
            <h6 class="ra-title">Organisations</h6>
            <span v-if="listed" class="ra-head-note" :title="listedTitle">{{ listedLabel }}</span>
        </div>
        <div class="ra-head-actions">
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

    <div class="ra-toolbar">
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

    <div v-if="loading && !listed" class="ra-state" role="status">
        <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Listing the organisations of {{ server.name }}…
    </div>
    <div v-else-if="error && !listed" class="ra-state ra-error" role="alert">
        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
        Could not list the organisations: {{ error }}
        <button type="button" class="btn btn-link inline-link" @click="reload(true)">Try again</button>
    </div>
    <template v-else-if="listed">
        <div class="table-frame">
            <table class="ra-table">
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
                        :class="['ra-row', { 'just-saved': row.org.uuid === highlightUuid }]"
                        tabindex="0"
                        @click="openDetail(row)"
                        @keydown.enter.prevent="openDetail(row)"
                    >
                        <td class="col-name">
                            <div class="name-line">
                                <span class="ra-name">{{ row.org.name }}</span>
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
        <footer v-if="filteredRows.length > perPage" class="ra-pager">
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
        },
        // `{uuid}`: an organisation to show (asked by the Sharing groups tab)
        revealRequest: {
            type: Object,
            default: null
        },
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
            // Asked to show before the list was there
            pendingReveal: null,
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
        revealRequest(request) {
            if (request && request.uuid) {
                this.revealWhenListed(request.uuid)
            }
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
                    if (this.pendingReveal) {
                        const uuid = this.pendingReveal
                        this.pendingReveal = null
                        this.$nextTick(() => this.reveal(uuid))
                    }
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
        revealWhenListed(uuid) {
            if (this.listed && !this.loading) {
                this.reveal(uuid)
            } else {
                this.pendingReveal = uuid
            }
        },
    },
    created() {
        if (this.revealRequest && this.revealRequest.uuid) {
            this.pendingReveal = this.revealRequest.uuid
        }
        this.reload(false)
        this.clock = setInterval(() => { this.now = Math.floor(Date.now() / 1000) }, 30000)
    },
    beforeDestroy() {
        clearInterval(this.clock)
        clearTimeout(this.highlightTimer)
    },
}
</script>

<style scoped src="./remoteAdminList.css"></style>

<style scoped>
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

.col-users {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

th.col-users .sort-button {
    justify-content: flex-end;
}

@media (max-width: 1199.98px) {
    .col-sector,
    .col-nationality {
        display: none;
    }
}

@media (max-width: 767.98px) {
    .col-type {
        display: none;
    }
}

@media (max-width: 575.98px) {
    .col-users {
        display: none;
    }
}
</style>
