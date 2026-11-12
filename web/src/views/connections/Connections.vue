<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <div class="connections-toolbar">
            <b-pagination
                class="mb-0"
                v-model="table.currentPage"
                size="sm"
                :per-page="table.perPage"
                :total-rows="shownCount"
                aria-controls="connection-table"
            ></b-pagination>
            <div class="toolbar-end">
                <b-form-checkbox
                    v-model="problemsOnly"
                    switch
                    class="problems-switch"
                    title="Only the broken and degraded links in use"
                >
                    Problems only
                    <span :class="['problems-count', { 'has-problems': problemCount > 0 }]">{{ problemCount }}</span>
                </b-form-checkbox>
                <b-input-group size="sm" class="search-group">
                    <b-form-input
                        v-model="table.filter"
                        type="search"
                        id="filterInput"
                        placeholder="Search servers, reasons, versions"
                        aria-label="Search the connections"
                        debounce="150"
                    ></b-form-input>
                </b-input-group>
                <b-button variant="primary" size="sm" title="Reload the connections" aria-label="Reload the connections" @click="refreshConnections()">
                    <i :class="{'fas fa-sync-alt': true, 'fa-spin': refreshInProgress}" aria-hidden="true"></i>
                </b-button>
            </div>
        </div>

        <b-table
            striped outlined show-empty small
            table-class="table-auto-hide-action connection-table"
            responsive
            id="connection-table"
            ref="connectionTable"
            :per-page="table.perPage"
            :current-page="table.currentPage"
            :busy.sync="table.isBusy"
            :items="visibleConnections"
            :fields="table.fields"
            :filter="table.filter"
            :filter-function="filterConnection"
            :sort-by.sync="table.sortBy"
            :sort-desc.sync="table.sortDesc"
            :sort-compare="sortCompare"
            :sort-icon-left="true"
            :tbody-tr-class="rowClass"
            primary-key="vid"
            @filtered="onFiltered"
            @sort-changed="onSorted"
        >
            <template v-slot:table-busy>
                <div class="text-center text-danger my-2">
                    <b-spinner class="align-middle"></b-spinner>
                    <strong class="ml-2">Loading...</strong>
                </div>
            </template>

            <template #empty>
                <div v-if="problemsOnly && connectionCount > 0" class="table-empty is-healthy">
                    <i class="fas fa-check" aria-hidden="true"></i> No broken or degraded link in use
                    <b-button variant="link" size="sm" class="p-0 align-baseline" @click="problemsOnly = false">Show all {{ connectionCount }} links</b-button>
                </div>
                <div v-else class="table-empty">This fleet has no sync links</div>
            </template>

            <template #emptyfiltered>
                <div class="table-empty">No link matches “{{ table.filter }}”</div>
            </template>

            <template v-slot:cell(health)="row">
                <div class="health-cell">
                    <LinkHealthLevel :level="linkLevel(row.item)" :unused="linkIsUnused(row.item)"></LinkHealthLevel>
                    <ul v-if="linkReasons(row.item).length > 0" class="health-reasons">
                        <li
                            v-for="reason in linkReasons(row.item)"
                            :key="reason.code + reason.message"
                            :class="`reason-${reason.level}`"
                        >{{ reason.message }}</li>
                    </ul>
                    <div v-if="testStateOf(row.item).error" class="test-error" role="status">
                        <i class="fas fa-exclamation-circle" aria-hidden="true"></i> Could not test: {{ testStateOf(row.item).error }}
                    </div>
                </div>
            </template>

            <template v-slot:cell(source)="row">
                <span>{{ row.value.name }} </span>
                <small><b-link :href="row.value.url" target="_blank">{{ row.value.url }} <sup class="fa fa-external-link-alt"></sup></b-link></small>
            </template>

            <template v-slot:cell(destination)="row">
                <span>{{ row.value.Server !== undefined ? row.value.Server.name : '' }} </span>
                <small>
                    <b-link :href="row.value.Server !== undefined ? row.value.Server.url : '#'" target="_blank">
                        {{ row.value.Server !== undefined ? row.value.Server.url : '' }} <sup class="fa fa-external-link-alt"></sup>
                    </b-link>
                </small>
            </template>

            <template v-slot:cell(destination.connectionUser)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <syncUserSummary
                        :user="row.value"
                    ></syncUserSummary>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(pull)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <b-button :id="`pull-rule-${row.index}`" variant="link" size="xs" class="m-0 text-dark" href="#" tabindex="0">
                        <i
                            :class="['method-status', 'fa', row.value ? 'fa-check' : 'fa-times']"
                        ></i>
                        <small>
                            ({{ row.item.filtering_rules.pull_rule_number }} pull rules)
                        </small>
                    </b-button>
                    <b-popover
                        :target="`pull-rule-${row.index}`"
                        triggers="focus"
                        title="Pull rules"
                    >
                        <template v-slot:title>
                            <div class="d-flex">
                                <span>Pull rules</span>
                                <b-button variant="link" size="sm" class="ml-auto p-0 m-0"
                                    @click="toggleRulesTreeMode"
                                >
                                    <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
                                </b-button>
                            </div>
                        </template>
                        <jsonViewer
                            :tree="rulesTreeMode"
                            :item="row.item.filtering_rules.pull_rules"
                            rootKeyName="Pull rules"
                            :open="true"
                        ></jsonViewer>
                    </b-popover>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(push)="row">
                <loaderPlaceholder :loading="!row.value._loading">
                    <b-button :id="`push-rule-${row.index}`" variant="link" size="xs" class="m-0 text-dark" href="#" tabindex="0">
                        <i
                            :class="['method-status', 'fa', row.value ? 'fa-check' : 'fa-times']"
                        ></i>
                        <small>
                            ({{ row.item.filtering_rules.push_rule_number }} push rules)
                        </small>
                    </b-button>
                    <b-popover
                        :target="`push-rule-${row.index}`"
                        triggers="focus"
                        title="Push rules"
                    >
                        <template v-slot:title>
                            <div class="d-flex">
                                <span>Push rules</span>
                                <b-button variant="link" size="sm" class="ml-auto p-0 m-0"
                                    @click="toggleRulesTreeMode"
                                >
                                    <i :class="['fas', rulesTreeMode ? 'fa-code' : 'fa-stream']"></i>
                                </b-button>
                            </div>
                        </template>
                        <jsonViewer
                            :tree="rulesTreeMode"
                            :item="row.item.filtering_rules.push_rules"
                            rootKeyName="Push rules"
                            :open="true"
                        ></jsonViewer>
                    </b-popover>
                </loaderPlaceholder>
            </template>

            <template v-slot:cell(push_galaxy_clusters)="row">
                <i :class="['fa', row.item.destination.Server.push_galaxy_clusters ? 'fa-check text-success' : 'fa-times']"></i>
            </template>

            <template v-slot:cell(pull_galaxy_clusters)="row">
                <i :class="['fa', row.item.destination.Server.pull_galaxy_clusters ? 'fa-check text-success' : 'fa-times']"></i>
            </template>

            <template v-slot:cell(local_version)="row">
                <span
                    v-if="versionsOf(row.item).local"
                    :class="['version', versionsOf(row.item).behind === 'local' ? `is-behind behind-${versionsOf(row.item).behindLevel}` : '']"
                    :title="versionsOf(row.item).behind === 'local' ? versionsOf(row.item).title : null"
                >
                    <i v-if="versionsOf(row.item).behind === 'local'" class="fas fa-arrow-circle-up" aria-hidden="true"></i>
                    {{ versionsOf(row.item).local }}
                    <span v-if="versionsOf(row.item).behind === 'local'" class="sr-only">(should be updated)</span>
                </span>
                <span v-else class="text-muted n-a">N/A</span>
            </template>

            <template v-slot:cell(remote_version)="row">
                <span
                    v-if="versionsOf(row.item).remote"
                    :class="['version', versionsOf(row.item).behind === 'remote' ? `is-behind behind-${versionsOf(row.item).behindLevel}` : '']"
                    :title="versionsOf(row.item).behind === 'remote' ? versionsOf(row.item).title : null"
                >
                    <i v-if="versionsOf(row.item).behind === 'remote'" class="fas fa-arrow-circle-up" aria-hidden="true"></i>
                    {{ versionsOf(row.item).remote }}
                    <span v-if="versionsOf(row.item).behind === 'remote'" class="sr-only">(should be updated)</span>
                </span>
                <span v-else class="text-muted n-a">N/A</span>
            </template>

            <template v-slot:cell(tested_at)="row">
                <span v-if="testStateOf(row.item).testing" class="tested-at is-testing" role="status">
                    <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Testing…
                </span>
                <span v-else-if="linkTestedAt(row.item)" class="tested-at" :title="testedTitle(row.item)">{{ agoLabel(linkTestedAt(row.item), now) }}</span>
                <span v-else class="tested-at text-muted">Never</span>
            </template>

            <template v-slot:cell(last_refresh)="row">
                <span class="d-block" style="width: 90px;">
                    <span :class="forcedHidden == row.index ? 'd-none' : 'hide-on-hover'">
                        <loaderPlaceholder :loading="!row.value._loading">
                            <timeSinceRefresh
                                :timestamp="row.value"
                                :server_id="row.item.source.id"
                            ></timeSinceRefresh>
                        </loaderPlaceholder>
                    </span>

                    <span :class="forcedHidden == row.index ? '' : 'reveal-on-hover'">
                        <div class="btn-group">
                            <b-button
                                size="xs" variant ="link"
                                :title="row.detailsShowing ? 'Hide the details' : 'Show the details'"
                                @click="toggleConnectionInfo(row.item)"
                            >
                                <i :class="['text-secondary', 'fas', `fa-${row.detailsShowing ? 'compress-alt' : 'expand-alt'}`]"></i>
                            </b-button>
                            <b-dropdown
                                variant="link" size="xs" class="ml-1"
                                @hidden="clearForcedHidden"
                                right no-caret lazy
                            >
                                <template v-slot:button-content>
                                    <i
                                        class="fas fa-ellipsis-v"
                                        @click="forceHidden(row.index)"
                                    ></i>
                                    <span class="sr-only">Actions</span>
                                </template>
                                <contextualMenu
                                    :menu="genContextualMenu(row.item)"
                                    @test-link="handleTestLink"
                                    @view-in-server="viewInServer"
                                    @view-in-strategic-view="viewInStrategicView"
                                ></contextualMenu>
                            </b-dropdown>
                        </div>
                    </span>
                </span>
            </template>

            <template v-slot:row-details="row">
                <RowDetails
                    :connection="row.item"
                    :serverSource="row.item.source"
                    :serverDestination="row.item.destination"
                    :refreshing="linkTestState(row.item.source.id, row.item.destination.Server.id).testing"
                    @actionRefresh="handleRefreshInfo({connection: row.item, method: $event})"
                    @actionClose="row.toggleDetails"
                ></RowDetails>
            </template>

            <template v-slot:table-caption>{{ captionText }}</template>
        </b-table>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import contextualMenu from "@/components/ui/elements/contextualMenu.vue"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import RowDetails from "@/views/connections/elements/RowDetails.vue"
import syncUserSummary from "@/views/servers/elements/syncUserSummary.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import LinkHealthLevel from "@/components/health/LinkHealthLevel.vue"
import { isProblemLink } from "@/store/modules/connections"
import {
    LINK_LEVEL_META, agoLabel, compareVersions, linkHealthRank, linkIsUnused, linkLevel, linkReasons, linkTestedAt,
    linkTestMixin, linkVersionReasons,
} from "@/helpers/linkHealth"

const PROBLEMS_ONLY_KEY = "mfc.connections.problemsOnly"

function readProblemsOnly() {
    try {
        return window.localStorage.getItem(PROBLEMS_ONLY_KEY) === "1"
    } catch (e) {
        return false
    }
}

function destinationName(link) {
    const remote = (link.destination && link.destination.Server) || {}
    return remote.name || remote.url || ""
}

function linkTest(link) {
    return (link.destination && link.destination.connectionTest) || {}
}

export default {
    name: "TheConnections",
    mixins: [linkTestMixin],
    components: {
        Layout,
        loaderPlaceholder,
        contextualMenu,
        timeSinceRefresh,
        jsonViewer,
        RowDetails,
        syncUserSummary,
        LinkHealthLevel,
    },
    data: function () {
        return {
            refreshInProgress: false,
            reloadTimer: null,
            rulesTreeMode: true,
            forcedHidden: -1,
            problemsOnly: readProblemsOnly(),
            table: {
                isBusy: false,
                filter: "",
                filteredCount: 0,
                currentPage: 1,
                perPage: 30,
                sortBy: "health",
                sortDesc: false,
                fields: [
                    {
                        key: "health",
                        label: "Health",
                        sortable: true,
                        tdClass: "health-column",
                    },
                    {
                        key: "source",
                        sortable: true
                    },
                    {
                        key: "destination",
                        sortable: true,
                    },
                    {
                        key: "destination.connectionUser",
                        label: "User",
                        sortable: true,
                    },
                    {
                        key: "pull",
                        sortable: true,
                        tdClass: "text-nowrap",
                    },
                    {
                        key: "push",
                        sortable: true,
                        tdClass: "text-nowrap",
                    },
                    {
                        key: "push_galaxy_clusters",
                        label: "Push Clusters",
                        sortable: true,
                    },
                    {
                        key: "pull_galaxy_clusters",
                        label: "Pull Clusters",
                        sortable: true,
                    },
                    {
                        key: "local_version",
                        label: "Local version",
                        sortable: true,
                        tdClass: "text-nowrap",
                    },
                    {
                        key: "remote_version",
                        label: "Remote version",
                        sortable: true,
                        tdClass: "text-nowrap",
                    },
                    {
                        key: "tested_at",
                        label: "Tested",
                        sortable: true,
                        tdClass: "text-nowrap",
                    },
                    {
                        key: "last_refresh",
                        sortable: true,
                        class: "align-middle refresh-column py-1"
                    },
                ]
            }
        }
    },
    computed: {
        ...mapState({
            allConnections: state => state.connections.all,
            selectedFleet: state => state.fleets.selected,
            remote_connections: state => state.servers.remote_connections,
        }),
        ...mapGetters({
            connectionCount: "connections/connectionCount"
        }),
        problemCount() {
            return this.allConnections.filter(isProblemLink).length
        },
        visibleConnections() {
            return this.problemsOnly ? this.allConnections.filter(isProblemLink) : this.allConnections
        },
        shownCount() {
            return this.table.filter ? this.table.filteredCount : this.visibleConnections.length
        },
        captionText() {
            const plural = (count, one, many) => `${count} ${count === 1 ? one : many}`
            if (this.shownCount === this.connectionCount) {
                return plural(this.connectionCount, "link", "links")
            }
            const shown = this.problemsOnly ? plural(this.shownCount, "problem link", "problem links") : plural(this.shownCount, "link", "links")
            return `Showing ${shown} out of ${this.connectionCount}`
        },
    },
    methods: {
        agoLabel,
        linkLevel,
        linkIsUnused,
        linkReasons,
        linkTestedAt,
        testedTitle(link) {
            return `Tested ${moment.unix(linkTestedAt(link)).format("LLL")}`
        },
        testStateOf(link) {
            const remoteID = link.destination.Server.id
            const state = this.linkTestState(link.source.id, remoteID)
            return { testing: state.testing || this.serverTesting(link.source.id), error: state.error }
        },
        // Both versions, and which side should be updated when the health reasons say so
        versionsOf(link) {
            const test = linkTest(link)
            const local = test.localVersion || null
            const remote = test.remoteVersion || null
            const reasons = linkVersionReasons(link)
            let behind = null
            if (reasons.length > 0) {
                if (reasons.some(reason => reason.code === "remote_outdated")) {
                    behind = "remote"
                }
                if (local && remote && compareVersions(local, remote) !== 0) {
                    behind = compareVersions(local, remote) < 0 ? "local" : "remote"
                }
            }
            return {
                local,
                remote,
                behind,
                behindLevel: reasons.some(reason => reason.level === "broken") ? "broken" : "degraded",
                title: reasons.map(reason => reason.message).join("\n"),
            }
        },
        rowClass(item, type) {
            return type === "row" && linkIsUnused(item) ? "row-unused" : ""
        },
        filterConnection(link, filter) {
            const needle = String(filter).trim().toLowerCase()
            if (needle === "") {
                return true
            }
            const remote = link.destination.Server || {}
            const test = linkTest(link)
            const haystack = [
                link.source.name, link.source.url, remote.name, remote.url,
                LINK_LEVEL_META[linkLevel(link)].label, linkIsUnused(link) ? "unused" : "",
                test.localVersion, test.remoteVersion,
                ...linkReasons(link).map(reason => reason.message),
            ]
            return haystack.some(value => value && String(value).toLowerCase().includes(needle))
        },
        // Columns without a plain value; null falls back to b-table's own comparison
        sortCompare(a, b, key) {
            switch (key) {
            case "health":
                return linkHealthRank(a) - linkHealthRank(b) || destinationName(a).localeCompare(destinationName(b))
            case "source":
                return (a.source.name || "").localeCompare(b.source.name || "")
            case "destination":
                return destinationName(a).localeCompare(destinationName(b))
            case "local_version":
                return compareVersions(linkTest(a).localVersion, linkTest(b).localVersion)
            case "remote_version":
                return compareVersions(linkTest(a).remoteVersion, linkTest(b).remoteVersion)
            case "tested_at":
                return (linkTestedAt(a) || 0) - (linkTestedAt(b) || 0)
            case "push_galaxy_clusters":
            case "pull_galaxy_clusters":
                return Number(Boolean(a.destination.Server[key])) - Number(Boolean(b.destination.Server[key]))
            default:
                return null
            }
        },
        onFiltered(filteredItems) {
            this.table.filteredCount = filteredItems.length
            this.table.currentPage = 1
        },
        onSorted() {
            this.table.currentPage = 1
        },
        forceHidden(row_id) {
            this.forcedHidden = row_id
        },
        clearForcedHidden() {
            this.forcedHidden = -1
        },
        genContextualMenu(connection) {
            const testing = this.testStateOf(connection).testing
            return [
                {
                    variant: "",
                    text: testing ? "Testing this link…" : "Test this link",
                    icon: "redo-alt",
                    eventName: "test-link",
                    disabled: testing,
                    callbackData: {connection: connection}
                },
                {
                    variant: "",
                    text: "View in Strategic View",
                    icon: "project-diagram",
                    eventName: "view-in-strategic-view",
                    callbackData: {connection: connection}
                },
                {
                    variant: "",
                    text: "View the server's sync links",
                    icon: "server",
                    eventName: "view-in-server",
                    callbackData: {connection: connection}
                }
            ]
        },
        refreshConnections() {
            this.refreshInProgress = true
            return this.$store.dispatch("connections/getConnections")
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not fetch connection index",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        toggleConnectionInfo(connection) {
            this.$store.commit("connections/toggleShowDetails", connection)
            if (connection._showDetails) {
                this.refreshInfo(connection)
            }
        },
        toggleRulesTreeMode() {
            this.rulesTreeMode = !this.rulesTreeMode
        },
        handleTestLink(data) {
            const connection = data.connection
            this.testLink(connection.source.id, connection.destination.Server.id)
        },
        handleRefreshInfo(data) {
            const connection = data.connection
            if (data.method === "no_cache") {
                // Fresh from MISP: re-test this link. The links reload when the test reports back
                this.testLink(connection.source.id, connection.destination.Server.id)
            }
            this.refreshInfo(connection)
        },
        refreshInfo(connection) {
            this.$store.dispatch("connections/getConnection", connection)
        },
        viewInServer(data) {
            const connection = data.connection
            if (connection && connection.source) {
                this.$router.push({ name: "servers.view", params: { server_id: connection.source.id }, query: { tab: "sync" } })
            }
        },
        viewInStrategicView(data) {
            const connection = data.connection
            if (connection && this.selectedFleet) {
                this.$router.push({ name: "strategicView", params: { fleet_id: this.selectedFleet.id }, query: { link: connection.vid } })
            }
        },
    },
    watch: {
        problemsOnly(enabled) {
            try {
                window.localStorage.setItem(PROBLEMS_ONLY_KEY, enabled ? "1" : "0")
            } catch (e) {
                // Not remembered, no harm
            }
            this.table.currentPage = 1
        },
        // Link tests and refreshes update the servers' connections: reload the links (once they settle)
        remote_connections: {
            handler() {
                clearTimeout(this.reloadTimer)
                this.reloadTimer = setTimeout(() => this.refreshConnections(), 500)
            },
            deep: true,
        },
    },
    mounted() {
        this.refreshConnections()
    },
    beforeDestroy() {
        clearTimeout(this.reloadTimer)
    },
}
</script>

<style scoped>
.connections-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5em 1em;
    margin-bottom: 0.5em;
}

.toolbar-end {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5em 0.75em;
}

.search-group {
    width: 18em;
    max-width: 100%;
}

.problems-switch {
    white-space: nowrap;
    font-size: 0.9em;
}

.problems-count {
    display: inline-block;
    min-width: 1.6em;
    margin-left: 0.2em;
    padding: 0 0.4em;
    border-radius: 0.8em;
    background: #e9ecef;
    color: #495057;
    font-size: 0.85em;
    font-weight: 600;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

.problems-count.has-problems {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.method-status {
    width: 14px;
}

/* Absolutely positioned bits of the cells (screen-reader labels, popover anchors) scroll with the table */
::v-deep .table-responsive {
    position: relative;
}

::v-deep .health-column {
    min-width: 11.5em;
    max-width: 22em;
}

.health-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.1em;
}

.health-reasons {
    margin: 0;
    padding: 0 0 0 1.7em;
    list-style: none;
    font-size: 0.85em;
    line-height: 1.35;
}

.health-reasons li {
    overflow-wrap: anywhere;
}

.reason-broken {
    color: var(--health-critical-ink);
}

.reason-degraded {
    color: var(--health-warning-ink);
}

.reason-unknown {
    color: #5a6270;
}

.test-error {
    padding-left: 2em;
    color: var(--health-critical-ink);
    font-size: 0.85em;
}

.version {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.9em;
    font-variant-numeric: tabular-nums;
}

.version.is-behind {
    font-weight: 600;
    cursor: help;
}

.behind-degraded {
    color: var(--health-warning-ink);
}

.behind-broken {
    color: var(--health-critical-ink);
}

.n-a {
    font-size: 0.85em;
}

.tested-at {
    font-size: 0.9em;
}

.tested-at.is-testing {
    color: var(--var-color-lapislazuli, #2c6bd1);
}

::v-deep .row-unused > td:not(.health-column) {
    color: #6c757d;
}

.table-empty {
    padding: 1em 0;
    color: #6c757d;
    text-align: center;
}

.table-empty.is-healthy {
    color: var(--health-ok-ink);
}

.table-empty.is-healthy .btn-link {
    margin-left: 0.5em;
}
</style>
