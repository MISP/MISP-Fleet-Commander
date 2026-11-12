<template>
    <div :class="['job-results', { 'job-results-scroll': maxHeight }]" :style="maxHeight ? { maxHeight } : {}">
        <table class="job-results-table">
            <colgroup>
                <col class="col-server">
                <col class="col-status">
                <col class="col-http hide-narrow">
                <col class="hide-narrow">
                <col class="col-time hide-narrow">
                <col class="col-view">
            </colgroup>
            <thead>
                <tr>
                    <th scope="col">Server</th>
                    <th scope="col">Status</th>
                    <th scope="col" class="hide-narrow" title="HTTP status of the last request made to the server">HTTP</th>
                    <th scope="col" class="hide-narrow">Result</th>
                    <th scope="col" class="text-right hide-narrow">Time</th>
                    <th scope="col"><span class="sr-only">Response</span></th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="row in rows" :key="row.key" :class="{ 'row-error': row.status === 'error' }">
                    <td class="cell-server">
                        <router-link
                            v-if="row.server_id"
                            :to="{ name: 'servers.view', params: { server_id: row.server_id } }"
                            class="server-name"
                            @click.native="$emit('navigate')"
                        >{{ row.server_name }}</router-link>
                        <span v-else class="server-name server-gone" title="This server was deleted">{{ row.server_name }}</span>
                        <span class="server-url" :title="row.server_url">{{ row.server_url }}</span>
                        <span v-if="row.summary" class="summary summary-narrow">{{ row.summary }}</span>
                    </td>
                    <td>
                        <span v-if="row.status === null" class="not-run">Not run</span>
                        <span v-else-if="row.status === 'pending' && running" class="in-progress" title="Waiting for its turn or for the server to answer">
                            <b-spinner small class="mr-1" label="In progress"></b-spinner>Pending
                        </span>
                        <JobStatusBadge v-else :status="row.status" of="result" small></JobStatusBadge>
                    </td>
                    <td class="cell-http hide-narrow">
                        <span v-if="row.http_status" :class="httpClass(row.http_status)">{{ row.http_status }}</span>
                    </td>
                    <td class="cell-summary hide-narrow">
                        <span v-if="row.summary" class="summary" :title="row.summary">{{ row.summary }}</span>
                    </td>
                    <td class="cell-time hide-narrow">{{ durationOf(row) }}</td>
                    <td class="cell-view">
                        <b-button
                            v-if="hasResponse(row)"
                            size="sm"
                            variant="link"
                            class="view-button"
                            :aria-label="`View the response of ${row.server_name}`"
                            @click="openResponse(row)"
                        >View</b-button>
                    </td>
                </tr>
            </tbody>
        </table>

        <b-modal
            :id="modalId"
            scrollable
            size="lg"
            ok-only
            ok-title="Close"
            ok-variant="secondary"
            :title="selected ? `Response of ${selected.server_name}` : 'Response'"
            @hidden="selected = null"
        >
            <template v-if="selected">
                <div class="response-head">
                    <JobStatusBadge :status="selected.status" of="result"></JobStatusBadge>
                    <span v-if="selected.http_status" :class="['response-http', httpClass(selected.http_status)]">HTTP {{ selected.http_status }}</span>
                    <span class="response-summary">{{ selected.summary }}</span>
                    <b-button
                        v-if="!selected.response_truncated"
                        variant="link"
                        size="sm"
                        class="ml-auto p-0"
                        :title="treeMode ? 'Show as raw JSON' : 'Show as a tree'"
                        @click="treeMode = !treeMode"
                    >
                        <i :class="['fas', treeMode ? 'fa-code' : 'fa-stream']" aria-hidden="true"></i>
                    </b-button>
                </div>
                <b-alert v-if="selected.response_truncated" show variant="warning" class="small py-2">
                    The response was larger than 64 KB: only its beginning was kept.
                </b-alert>
                <pre v-if="selected.response_truncated" class="response-raw">{{ selected.response }}</pre>
                <jsonViewer
                    v-else-if="treeMode"
                    :item="responseBody(selected)"
                    rootKeyName="Response"
                    :open="true"
                ></jsonViewer>
                <pre v-else class="response-raw">{{ JSON.stringify(responseBody(selected), null, 2) }}</pre>
                <p class="response-note">Credentials in stored responses are replaced by <code>***</code>.</p>
            </template>
        </b-modal>
    </div>
</template>

<script>
import JobStatusBadge from "@/components/jobs/JobStatusBadge.vue"
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import { formatDuration, resultDuration } from "@/helpers/jobs"

let uid = 0

export default {
    name: "JobResultsTable",
    components: {
        JobStatusBadge,
        jsonViewer,
    },
    props: {
        // The job whose results to show, or null before it is started
        job: {
            type: Object,
            default: null,
        },
        // Shown as "Not run" rows while there is no job: [{id, name, url}]
        servers: {
            type: Array,
            default: () => [],
        },
        maxHeight: {
            type: String,
            default: null,
        },
    },
    data() {
        uid += 1
        return {
            modalId: `job-response-${uid}`,
            selected: null,
            treeMode: true,
        }
    },
    computed: {
        // Queued jobs wait for a worker: their servers are not being worked on yet
        running() {
            return this.job !== null && this.job.status === "running"
        },
        rows() {
            if (this.job !== null && Array.isArray(this.job.results)) {
                return this.job.results.map(result => Object.assign({ key: `r${result.id}` }, result))
            }
            return this.servers.filter(server => server).map(server => ({
                key: `s${server.id}`, server_id: server.id, server_name: server.name, server_url: server.url,
                status: null, http_status: null, summary: "", response: null,
            }))
        },
    },
    methods: {
        durationOf(row) {
            return formatDuration(resultDuration(row))
        },
        hasResponse(row) {
            return row.response !== null && row.response !== undefined
        },
        httpClass(status) {
            if (status >= 200 && status < 300) {
                return "http-ok"
            }
            return status >= 500 ? "http-error" : "http-warning"
        },
        // Raw queries and plugin answers both carry what MISP sent in `data`; plugin errors sit beside it
        responseBody(row) {
            const response = row.response
            if (response && typeof response === "object" && !Array.isArray(response) && "data" in response) {
                const body = { data: response.data }
                if (response.error) {
                    body.error = response.error
                }
                if (response.headers) {
                    body.headers = response.headers
                }
                if (response.request_response) {
                    body.request = response.request_response
                }
                return body
            }
            return response
        },
        openResponse(row) {
            this.selected = row
            this.$bvModal.show(this.modalId)
        },
    },
}
</script>

<style scoped>
.job-results {
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
}

.job-results-scroll {
    overflow: auto;
}

.job-results-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.875rem;
}

.col-server { width: 30%; }
.col-status { width: 8.5rem; }
.col-http { width: 4rem; }
.col-time { width: 5.5rem; }
.col-view { width: 4rem; }

.job-results-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f6f7f9;
    color: #5a6270;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 0.45rem 0.75rem;
    border-bottom: 1px solid var(--health-rule);
    text-align: left;
}

.job-results-table td {
    padding: 0.45rem 0.75rem;
    border-bottom: 1px solid #f0f2f5;
    vertical-align: middle;
    height: 3.1rem;
}

.job-results-table tbody tr:last-child td {
    border-bottom: none;
}

.row-error td {
    background: #fffafa;
}

.cell-server {
    overflow: hidden;
}

.server-name,
.server-url {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.server-name {
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.server-gone {
    color: #6c757d;
    text-decoration: line-through;
}

.server-url {
    font-size: 0.78rem;
    color: #6c757d;
}

.not-run {
    color: #8a929c;
    font-size: 0.8rem;
}

.in-progress {
    display: inline-flex;
    align-items: center;
    color: var(--var-color-lapislazuli);
    font-size: 0.8rem;
    font-weight: 600;
}

.cell-http {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
}

.http-ok { color: var(--health-ok-ink); }
.http-warning { color: var(--health-warning-ink); }
.http-error { color: var(--health-critical-ink); }

.cell-summary {
    overflow: hidden;
}

.summary {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: #3d4450;
    line-height: 1.3;
    word-break: break-word;
}

.cell-time {
    text-align: right;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.cell-view {
    text-align: right;
}

.view-button {
    padding: 0;
    font-size: 0.85rem;
}

.response-head {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
}

.response-http {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.response-summary {
    color: #3d4450;
}

.response-raw {
    max-height: 60vh;
    overflow: auto;
    background: #f6f7f9;
    border-radius: 4px;
    padding: 0.75rem;
    font-size: 0.8rem;
    white-space: pre-wrap;
    word-break: break-word;
}

.response-note {
    margin: 0.75rem 0 0;
    font-size: 0.78rem;
    color: #6c757d;
}

.summary-narrow {
    display: none;
}

@media (max-width: 640px) {
    .hide-narrow {
        display: none;
    }
    .summary-narrow {
        display: -webkit-box;
        margin-top: 0.2rem;
        font-size: 0.8rem;
    }
    .col-server { width: auto; }
    .col-status { width: 6.5rem; }
    .col-view { width: 3rem; }
    .job-results-table td {
        height: auto;
    }
}
</style>
