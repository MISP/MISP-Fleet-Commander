<template>
<div class="ra-tab">
    <header class="ra-head">
        <div class="ra-head-text">
            <h6 class="ra-title">Sharing groups</h6>
            <span v-if="listed" class="ra-head-note" :title="listedTitle">{{ listedLabel }}</span>
        </div>
        <div class="ra-head-actions">
            <button
                type="button"
                class="btn btn-link refresh-button"
                :disabled="loading || comparing"
                title="List the sharing groups again, here and on the other servers of the fleet"
                aria-label="List the sharing groups again"
                @click="reload(true)"
            >
                <i :class="['fas', 'fa-sync', { 'fa-spin': loading || comparing }]" aria-hidden="true"></i>
            </button>
            <b-button size="sm" variant="primary" class="add-button" @click="openForm(null)">
                <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add sharing group
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
                <button type="button" class="btn btn-link inline-link" @click="differsOnly = true">
                    {{ mismatchCount }} sharing group{{ mismatchCount === 1 ? "" : "s" }} differ{{ mismatchCount === 1 ? "s" : "" }}
                </button>.
            </template>
            <template v-else> None differs.</template>
            <template v-if="comparison.unavailable.length > 0">
                <span class="fleet-unavailable" :title="unavailableTitle">{{ comparison.unavailable.length }} server{{ comparison.unavailable.length === 1 ? "" : "s" }} could not be listed</span>.
            </template>
        </span>
    </div>

    <div class="ra-toolbar">
        <div class="scope-segments" role="group" aria-label="Which sharing groups">
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
            v-if="hasFleet"
            type="button"
            :class="['attention-toggle', { active: differsOnly, empty: mismatchCount === 0 }]"
            :aria-pressed="differsOnly ? 'true' : 'false'"
            :disabled="mismatchCount === 0 && !differsOnly"
            title="Groups that another server of the fleet has with other members, flags or name, or under another UUID"
            @click="differsOnly = !differsOnly"
        >
            <i class="fas fa-exchange-alt" aria-hidden="true"></i>
            Differs in the fleet<span class="segment-count">{{ mismatchCount }}</span>
        </button>
        <div class="search-box">
            <i class="fas fa-search" aria-hidden="true"></i>
            <input
                v-model="search"
                type="search"
                class="form-control form-control-sm"
                placeholder="Name, UUID, member, releasability…"
                aria-label="Search the sharing groups"
            >
        </div>
    </div>

    <div v-if="loading && !listed" class="ra-state" role="status">
        <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Listing the sharing groups of {{ server.name }}…
    </div>
    <div v-else-if="error && !listed" class="ra-state ra-error" role="alert">
        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
        Could not list the sharing groups: {{ error }}
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
                            {{ rows.length === 0 ? "This server has no sharing groups." : "No sharing group matches." }}
                            <button v-if="filtersActive" type="button" class="btn btn-link inline-link" @click="clearFilters">Clear the filters</button>
                        </td>
                    </tr>
                    <tr
                        v-for="row in pageRows"
                        :key="row.group.uuid"
                        :class="['ra-row', { 'just-saved': row.group.uuid === highlightUuid, 'is-inactive': !row.group.active }]"
                        tabindex="0"
                        @click="openDetail(row)"
                        @keydown.enter.prevent="openDetail(row)"
                    >
                        <td class="col-name">
                            <div class="name-line">
                                <span class="ra-name">{{ row.group.name }}</span>
                                <span v-if="!row.group.active" class="kind-badge badge-inactive" title="Cannot be chosen for new events or attributes. Data already shared with it still syncs.">Inactive</span>
                            </div>
                            <div v-if="row.description" class="sub-line" :title="row.description">{{ row.description }}</div>
                        </td>
                        <td class="col-uuid"><code :title="row.group.uuid">{{ row.group.uuid.slice(0, 8) }}</code></td>
                        <td class="col-creator">{{ row.group.creator ? row.group.creator.name : "—" }}</td>
                        <td class="col-members" :title="membersTitle(row.group)">
                            <span :class="{ muted: row.group.members.length === 0 }">{{ row.group.members.length }}</span>
                            <span v-if="row.extend > 0" class="extend-note">· {{ row.extend }} may extend</span>
                        </td>
                        <td class="col-servers">
                            <span :class="{ muted: row.servers === 'No server' }" :title="row.group.roaming ? 'Its events go to any sync server whose organisation is a member, whatever its server list' : ''">{{ row.servers }}</span>
                        </td>
                        <td class="col-releasability">
                            <span v-if="row.group.releasability" class="clip" :title="row.group.releasability">{{ row.group.releasability }}</span>
                            <span v-else class="muted">—</span>
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
                aria-label="Pages of sharing groups"
            ></b-pagination>
        </footer>
    </template>

    <SharingGroupDetailModal
        :server="server"
        :row="selectedRow"
        :has-fleet="hasFleet"
        :comparing="comparing"
        @edit="openForm"
        @copy="openCopy"
        @baseline="openBaseline"
        @delete="openDelete"
        @show-organisation="showOrganisation"
    ></SharingGroupDetailModal>
    <SharingGroupFormModal
        :server="server"
        :group="formGroup"
        :groups="groups"
        @saved="onSaved"
        @changed="onSaved(null)"
    ></SharingGroupFormModal>
    <SharingGroupCopyModal
        :server="server"
        :row="copyRow"
        @done="onCopyDone"
    ></SharingGroupCopyModal>
    <SharingGroupBaselineModal
        :server="server"
        :group="baselineGroup"
    ></SharingGroupBaselineModal>
    <SharingGroupDeleteModal
        :server="server"
        :group="deleteGroup"
        @deleted="onDeleted"
    ></SharingGroupDeleteModal>
</div>
</template>

<script>
import api from "@/api/sharingGroups"
import { normalisedName } from "@/helpers/organisations"
import { extendCount, fleetStanding, matchesSearch, serversSummary } from "@/helpers/sharingGroups"
import SharingGroupDetailModal from "@/views/servers/elements/mispRemoteAdministration/sharingGroups/SharingGroupDetailModal.vue"
import SharingGroupFormModal from "@/views/servers/elements/mispRemoteAdministration/sharingGroups/SharingGroupFormModal.vue"
import SharingGroupCopyModal from "@/views/servers/elements/mispRemoteAdministration/sharingGroups/SharingGroupCopyModal.vue"
import SharingGroupBaselineModal from "@/views/servers/elements/mispRemoteAdministration/sharingGroups/SharingGroupBaselineModal.vue"
import SharingGroupDeleteModal from "@/views/servers/elements/mispRemoteAdministration/sharingGroups/SharingGroupDeleteModal.vue"

const COLUMNS = [
    { key: "name", label: "Name" },
    { key: "uuid", label: "UUID" },
    { key: "creator", label: "Creator" },
    { key: "members", label: "Members" },
    { key: "servers", label: "Servers" },
    { key: "releasability", label: "Releasable to" },
    { key: "fleet", label: "Fleet" },
]

export default {
    name: "sgAdministration",
    components: {
        SharingGroupDetailModal,
        SharingGroupFormModal,
        SharingGroupCopyModal,
        SharingGroupBaselineModal,
        SharingGroupDeleteModal,
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
            scope: "all",
            differsOnly: false,
            search: "",
            sort: { key: "name", desc: false },
            currentPage: 1,
            perPage: 50,
            selectedUuid: null,
            // The group just added or edited, shown and highlighted once listed again
            highlightUuid: null,
            highlightTimer: null,
            formGroup: null,
            copyRow: null,
            baselineGroup: null,
            deleteGroup: null,
            now: Math.floor(Date.now() / 1000),
            clock: null,
        }
    },
    computed: {
        groups() {
            return this.listed ? this.listed.sharing_groups : []
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
        rows() {
            return this.groups.map(group => Object.freeze({
                group,
                standing: fleetStanding(group, this.comparison, this.serverNames),
                servers: serversSummary(group),
                extend: extendCount(group),
                // Shown under the name, unless it only repeats it
                description: normalisedName(group.description) === normalisedName(group.name) ? "" : group.description,
            }))
        },
        counts() {
            const active = this.groups.filter(group => group.active).length
            return { all: this.groups.length, active, inactive: this.groups.length - active }
        },
        scopeOptions() {
            return [
                { value: "all", label: "All" },
                { value: "active", label: "Active" },
                { value: "inactive", label: "Inactive" },
            ]
        },
        mismatchCount() {
            return this.rows.filter(row => row.standing && row.standing.mismatches > 0).length
        },
        filtersActive() {
            return this.scope !== "all" || this.differsOnly || this.search.trim() !== ""
        },
        filteredRows() {
            const rows = this.rows.filter(row =>
                (this.scope === "all" || (this.scope === "active") === row.group.active) &&
                (!this.differsOnly || (row.standing && row.standing.mismatches > 0)) &&
                matchesSearch(row.group, this.search))
            const key = this.sort.key
            const value = (row) => {
                if (key === "members") {
                    return row.group.members.length
                }
                if (key === "fleet") {
                    return row.standing ? row.standing.rank : Infinity
                }
                if (key === "creator") {
                    return String(row.group.creator ? row.group.creator.name : "").toLowerCase()
                }
                if (key === "servers") {
                    return row.servers.toLowerCase()
                }
                return String(row.group[key] || "").toLowerCase()
            }
            const direction = this.sort.desc ? -1 : 1
            return rows.slice().sort((a, b) => {
                const left = value(a)
                const right = value(b)
                const order = typeof left === "number" ? left - right : left.localeCompare(right)
                return order * direction || a.group.name.localeCompare(b.group.name)
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
            return this.selectedUuid === null ? null : this.rows.find(row => row.group.uuid === this.selectedUuid) || null
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
        differsOnly() {
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
        reload(refresh) {
            this.loadGroups(refresh)
            this.loadComparison(refresh)
            // The server picker of the form lists the server's sync connections
            this.$store.dispatch("connections/getConnections").catch(() => {})
        },
        loadGroups(refresh = false) {
            this.loading = true
            this.error = null
            return api.index(this.server.id, { refresh })
                .then((listed) => {
                    listed.sharing_groups = Object.freeze(listed.sharing_groups)
                    this.listed = listed
                    this.now = Math.floor(Date.now() / 1000)
                })
                .catch((error) => {
                    this.error = error.message
                    if (this.listed) {
                        this.$bvToast.toast(error.message, { title: "Could not list the sharing groups again", variant: "danger" })
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
        sortBy(key) {
            if (this.sort.key === key) {
                this.sort = { key, desc: !this.sort.desc }
            } else {
                this.sort = { key, desc: key === "members" }
            }
        },
        sortIcon(key) {
            if (this.sort.key !== key) {
                return "fa-sort sort-idle"
            }
            return this.sort.desc ? "fa-sort-down" : "fa-sort-up"
        },
        membersTitle(group) {
            if (group.members.length === 0) {
                return "No member"
            }
            const names = group.members.map(member => member.extend ? `${member.name} (may extend)` : member.name)
            return names.length > 15 ? `${names.slice(0, 15).join("\n")}\n… and ${names.length - 15} more` : names.join("\n")
        },
        fleetChipTitle(standing) {
            const parts = [`On ${standing.present} of the ${standing.known} servers compared, this one included`]
            if (standing.mismatches > 0) {
                parts.push(`${standing.mismatches} with other members, flags, name or UUID`)
            }
            if (standing.unknown > 0) {
                parts.push(`${standing.unknown} more could not be listed`)
            }
            return parts.join(" · ")
        },
        clearFilters() {
            this.scope = "all"
            this.differsOnly = false
            this.search = ""
        },
        openDetail(row) {
            this.selectedUuid = row.group.uuid
            this.$nextTick(() => this.$bvModal.show("modal-sharing-group-detail"))
        },
        openForm(group) {
            this.formGroup = group
            this.$nextTick(() => this.$bvModal.show("modal-sharing-group-form"))
        },
        openCopy(row) {
            this.copyRow = row
            this.$nextTick(() => this.$bvModal.show("modal-sharing-group-copy"))
        },
        openBaseline(group) {
            this.baselineGroup = group
            this.$nextTick(() => this.$bvModal.show("modal-sharing-group-baseline"))
        },
        openDelete(group) {
            this.deleteGroup = group
            this.$nextTick(() => this.$bvModal.show("modal-sharing-group-delete"))
        },
        showOrganisation(member) {
            this.$bvModal.hide("modal-sharing-group-detail")
            this.$emit("show-organisation", member)
        },
        onSaved(saved) {
            // The backend dropped its cached list: list again, and compare again (members or flags may have changed)
            this.loadGroups(false).then(() => {
                if (saved && saved.uuid) {
                    this.reveal(saved.uuid)
                }
            })
            this.loadComparison(false)
        },
        onDeleted() {
            this.selectedUuid = null
            this.loadGroups(false)
            this.loadComparison(false)
        },
        // Bring a group into view: its page (filters cleared if they hide it), highlighted, its detail open
        reveal(uuid) {
            let index = this.filteredRows.findIndex(row => row.group.uuid === uuid)
            if (index === -1 && this.rows.some(row => row.group.uuid === uuid)) {
                this.clearFilters()
                index = this.filteredRows.findIndex(row => row.group.uuid === uuid)
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
                this.$bvModal.show("modal-sharing-group-detail")
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

<style scoped src="./remoteAdminList.css"></style>

<style scoped>
.badge-inactive {
    background: #fdf3dc;
    color: #7a5600;
    cursor: help;
}

.ra-row.is-inactive .ra-name {
    color: #5f6873;
}

/* Never wider than the name: a long description must not widen the column */
.sub-line {
    width: 0;
    min-width: 100%;
    overflow: hidden;
    color: #6c757d;
    font-size: 0.8rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.col-members {
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}

.extend-note {
    margin-left: 0.4em;
    color: #6c757d;
    font-size: 0.8rem;
}

.col-servers {
    white-space: nowrap;
}

.col-releasability {
    max-width: 14rem;
}

.clip {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

@media (max-width: 1199.98px) {
    .col-creator,
    .col-releasability {
        display: none;
    }
}

@media (max-width: 575.98px) {
    .col-servers,
    .extend-note {
        display: none;
    }
}
</style>
