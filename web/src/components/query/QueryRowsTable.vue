<template>
<div class="qr">
    <div class="qr-toolbar">
        <div class="qr-summary" aria-live="polite">
            <template v-if="page">
                <strong>{{ formatNumber(page.total) }}</strong> row{{ page.total === 1 ? '' : 's' }}
                <template v-if="serverName"> from <strong>{{ serverName }}</strong>
                    <b-button size="sm" variant="link" class="qr-inline" @click="$emit('update:serverId', null)">show every server</b-button>
                </template>
                <template v-else-if="serverCount > 1"> from {{ serverCount }} servers</template>
            </template>
            <template v-else-if="loading">Loading the rows…</template>
        </div>
        <div class="qr-actions">
            <b-dropdown
                size="sm"
                variant="outline-secondary"
                right
                :disabled="!page || allColumns.length === 0"
                class="qr-columns"
                boundary="window"
            >
                <template #button-content>
                    <i class="fas fa-table-columns mr-1" aria-hidden="true"></i>Columns
                    <span class="qr-count">{{ shownColumns.length }}/{{ allColumns.length }}</span>
                </template>
                <b-dropdown-form form-class="qr-columns-form">
                    <div class="qr-columns-quick">
                        <b-button size="sm" variant="link" :disabled="!page || !page.default_columns" @click="useDefaultColumns">Default</b-button>
                        <b-button size="sm" variant="link" @click="shownColumns = allColumns.slice()">All</b-button>
                    </div>
                    <b-form-checkbox-group v-model="shownColumns" stacked class="qr-columns-list">
                        <b-form-checkbox v-for="column in allColumns" :key="column" :value="column">
                            <code>{{ column }}</code>
                        </b-form-checkbox>
                    </b-form-checkbox-group>
                </b-dropdown-form>
            </b-dropdown>
            <b-dropdown size="sm" variant="outline-primary" right :disabled="!page || page.total === 0 || exporting">
                <template #button-content>
                    <b-spinner v-if="exporting" small class="mr-1"></b-spinner>
                    <i v-else class="fas fa-download mr-1" aria-hidden="true"></i>Export
                </template>
                <b-dropdown-item-button @click="exportRows('csv')">
                    <i class="fas fa-file-csv fa-fw mr-1" aria-hidden="true"></i>CSV
                </b-dropdown-item-button>
                <b-dropdown-item-button @click="exportRows('json')">
                    <i class="fas fa-file-code fa-fw mr-1" aria-hidden="true"></i>JSON
                </b-dropdown-item-button>
                <b-dropdown-text class="qr-export-note">
                    {{ formatNumber(page ? page.total : 0) }} rows, the {{ shownColumns.length }} shown columns and the server
                </b-dropdown-text>
            </b-dropdown>
        </div>
    </div>

    <b-alert :show="!!error" variant="danger" class="qr-alert">
        Could not load the rows: {{ error }}
        <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
    </b-alert>
    <b-alert :show="expiredNames.length > 0" variant="warning" class="qr-alert">
        <i class="fas fa-clock mr-1" aria-hidden="true"></i>
        Rows of {{ expiredNames.join(', ') }} are no longer kept. Run the query again to see them.
    </b-alert>

    <div v-if="page && page.total === 0 && !loading" class="qr-empty">
        <i class="fas fa-magnifying-glass" aria-hidden="true"></i>
        <p>No rows matched{{ serverName ? ` on ${serverName}` : '' }}.</p>
    </div>

    <div v-else-if="page" :class="['qr-scroll', { 'qr-loading': loading }]">
        <table class="qr-table">
            <caption class="sr-only">Rows of every server, merged</caption>
            <thead>
                <tr>
                    <th scope="col" class="qr-sticky">Server</th>
                    <th v-for="column in shownColumns" :key="column" scope="col">{{ column }}</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(row, index) in page.rows" :key="index">
                    <th scope="row" class="qr-sticky qr-server">{{ row._server_name }}</th>
                    <td v-for="column in shownColumns" :key="column">
                        <span v-if="isEmpty(row[column])" class="qr-empty-cell" aria-label="empty">—</span>
                        <span v-else-if="Array.isArray(row[column])" class="qr-list">
                            <span v-for="(item, i) in row[column].slice(0, 4)" :key="i" class="qr-chip" :title="text(item)">{{ text(item) }}</span>
                            <span v-if="row[column].length > 4" class="qr-more" :title="text(row[column])">+{{ row[column].length - 4 }}</span>
                        </span>
                        <span v-else-if="typeof row[column] === 'boolean'" :class="['qr-bool', { on: row[column] }]">{{ row[column] ? 'true' : 'false' }}</span>
                        <span v-else class="qr-text" :title="text(row[column]).length > 60 ? text(row[column]) : null">{{ text(row[column]) }}</span>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <div v-if="page && page.total > perPage" class="qr-pager">
        <b-pagination
            v-model="pageNumber"
            :total-rows="page.total"
            :per-page="perPage"
            size="sm"
            class="mb-0"
            aria-label="Pages of rows"
        ></b-pagination>
        <span class="qr-range">{{ formatNumber(firstRow) }}–{{ formatNumber(lastRow) }} of {{ formatNumber(page.total) }}</span>
    </div>
</div>
</template>

<script>
import api from "@/api/queries"
import { cellText, exportFileName, toCSV, toJSON } from "@/helpers/mispql"

const NUMBER = new Intl.NumberFormat()
const EXPORT_PAGE = 1000

function download(name, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }))
    const link = document.createElement("a")
    link.href = url
    link.download = name
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// A run's rows, every server's merged (or one server's), a page at a time, with the columns to show and the export
export default {
    name: "QueryRowsTable",
    props: {
        jobId: { type: String, required: true },
        results: { type: Array, default: () => [] },
        // Only this server's rows, when set (.sync)
        serverId: { type: Number, default: null },
        table: { type: String, default: null },
    },
    data() {
        return {
            page: null,
            pageNumber: 1,
            perPage: 100,
            loading: false,
            error: null,
            shownColumns: [],
            columnsChosen: false,
            exporting: false,
            request: 0,
        }
    },
    computed: {
        allColumns() {
            return this.page ? this.page.columns : []
        },
        serverName() {
            const found = this.results.find(result => result.server_id === this.serverId)
            return found ? found.server_name : null
        },
        serverCount() {
            return this.results.filter(result => result.response && result.response.outcome === "rows").length
        },
        expiredNames() {
            const expired = new Set((this.page && this.page.expired_servers) || [])
            return this.results.filter(result => expired.has(result.server_id)).map(result => result.server_name)
        },
        firstRow() {
            return (this.pageNumber - 1) * this.perPage + 1
        },
        lastRow() {
            return Math.min(this.page ? this.page.total : 0, this.pageNumber * this.perPage)
        },
        exportColumns() {
            return [{ key: "_server_name", label: "server" }].concat(this.shownColumns.map(column => ({ key: column, label: column })))
        },
    },
    watch: {
        jobId() {
            this.columnsChosen = false
            this.reset()
        },
        serverId() {
            this.reset()
        },
        pageNumber() {
            this.load()
        },
    },
    mounted() {
        this.load()
    },
    methods: {
        formatNumber(value) {
            return NUMBER.format(value)
        },
        text(value) {
            return cellText(value)
        },
        isEmpty(value) {
            return value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0)
        },
        reset() {
            if (this.pageNumber !== 1) {
                this.pageNumber = 1  // the watcher loads
            } else {
                this.load()
            }
        },
        load() {
            this.request += 1
            const request = this.request
            this.loading = true
            this.error = null
            api.rows(this.jobId, {
                offset: (this.pageNumber - 1) * this.perPage,
                limit: this.perPage,
                server_id: this.serverId === null ? undefined : this.serverId,
            }).then((page) => {
                if (request !== this.request) {
                    return
                }
                this.page = page
                if (!this.columnsChosen) {
                    this.columnsChosen = true
                    this.shownColumns = page.default_columns ? page.default_columns.slice() : page.columns.slice()
                }
            }).catch((error) => {
                if (request === this.request) {
                    this.error = error
                }
            }).finally(() => {
                if (request === this.request) {
                    this.loading = false
                }
            })
        },
        useDefaultColumns() {
            if (this.page && this.page.default_columns) {
                this.shownColumns = this.page.default_columns.slice()
            }
        },
        // Every row (with the server filter), fetched a large page at a time, then written in the browser
        async exportRows(format) {
            this.exporting = true
            try {
                const rows = []
                let offset = 0
                for (;;) {
                    // eslint-disable-next-line no-await-in-loop
                    const page = await api.rows(this.jobId, {
                        offset,
                        limit: EXPORT_PAGE,
                        server_id: this.serverId === null ? undefined : this.serverId,
                    })
                    rows.push(...page.rows)
                    offset += EXPORT_PAGE
                    if (offset >= page.total || page.rows.length === 0) {
                        break
                    }
                }
                if (format === "csv") {
                    download(exportFileName(this.table, "csv"), `﻿${toCSV(this.exportColumns, rows)}`, "text/csv;charset=utf-8")
                } else {
                    download(exportFileName(this.table, "json"), toJSON(this.exportColumns, rows), "application/json")
                }
            } catch (error) {
                this.$bvToast.toast(String(error), { title: "Could not export the rows", variant: "danger", solid: true })
            } finally {
                this.exporting = false
            }
        },
    },
}
</script>

<style scoped>
.qr-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    margin-bottom: 0.6rem;
}

.qr-summary {
    font-size: 0.88rem;
    color: #3c4452;
}

.qr-inline {
    padding: 0 0 0 0.25rem;
    font-size: inherit;
    vertical-align: baseline;
}

.qr-actions {
    display: flex;
    gap: 0.4rem;
    margin-left: auto;
}

.qr-count {
    margin-left: 0.25rem;
    font-size: 0.72rem;
    color: inherit;
    opacity: 0.72;
    font-variant-numeric: tabular-nums;
}

.qr-columns >>> .qr-columns-form {
    width: 18rem;
    padding: 0.4rem 0.75rem 0.6rem;
}

.qr-columns-quick {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 0.25rem;
    border-bottom: 1px solid #eef0f3;
}

.qr-columns-quick .btn {
    padding-left: 0;
    font-size: 0.8rem;
}

.qr-columns-list {
    max-height: 18rem;
    overflow-y: auto;
    padding-top: 0.3rem;
}

.qr-columns-list code {
    color: var(--var-color-yankeesblue);
    font-size: 0.8rem;
}

.qr-export-note {
    font-size: 0.75rem;
    color: #6b7380;
    white-space: normal;
    min-width: 14rem;
}

.qr-alert {
    font-size: 0.86rem;
    padding: 0.5rem 0.75rem;
}

.qr-empty {
    padding: 2rem 1rem;
    text-align: center;
    color: #5a6270;
    border: 1px dashed var(--health-rule);
    border-radius: 6px;
    background: #fff;
}

.qr-empty i {
    font-size: 1.4rem;
    color: #b3b9c1;
}

.qr-empty p {
    margin: 0.5rem 0 0;
}

.qr-scroll {
    max-height: 70vh;
    overflow: auto;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
    transition: opacity 0.15s ease;
}

.qr-loading {
    opacity: 0.55;
}

.qr-table {
    min-width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.84rem;
}

.qr-table th,
.qr-table td {
    padding: 0.38rem 0.7rem;
    border-bottom: 1px solid #eef0f3;
    vertical-align: top;
    text-align: left;
}

.qr-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #f6f7f9;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: #3c4452;
    white-space: nowrap;
}

.qr-table tbody tr:hover td,
.qr-table tbody tr:hover th {
    background: #f7fafc;
}

.qr-sticky {
    position: sticky;
    left: 0;
    z-index: 1;
    background: #fff;
    border-right: 1px solid #eef0f3;
}

.qr-table thead .qr-sticky {
    z-index: 3;
    background: #f6f7f9;
    font-family: inherit;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #5a6270;
}

.qr-server {
    font-weight: 600;
    color: var(--var-color-lapislazuli);
    white-space: nowrap;
}

.qr-text {
    display: inline-block;
    max-width: 28rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: top;
    color: var(--var-color-yankeesblue);
    font-variant-numeric: tabular-nums;
}

.qr-empty-cell {
    color: #c2c7ce;
}

/* On one line, so that every row has the same height; the full list is on hover */
.qr-list {
    display: inline-flex;
    flex-wrap: nowrap;
    align-items: center;
    gap: 0.2rem;
}

.qr-chip {
    max-width: 11rem;
    padding: 0.02rem 0.4rem;
    border-radius: 3px;
    background: #eef1f5;
    color: #2f3a4b;
    font-size: 0.75rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.qr-more {
    font-size: 0.75rem;
    color: #6b7380;
    white-space: nowrap;
}

.qr-bool {
    font-size: 0.78rem;
    color: #8a919c;
}

.qr-bool.on {
    color: var(--health-ok-ink);
    font-weight: 600;
}

.qr-pager {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 0.6rem;
}

.qr-range {
    font-size: 0.8rem;
    color: #6b7380;
    font-variant-numeric: tabular-nums;
}
</style>
