<template>
<div class="qm">
    <p v-if="servers.length === 0" class="qm-empty">No server answered.</p>
    <template v-else>
        <b-input-group v-if="kind === 'describe' && lines.length > 12" size="sm" class="qm-search">
            <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
            <b-form-input v-model="search" type="search" placeholder="Find a field" aria-label="Find a field"></b-form-input>
        </b-input-group>
        <div class="qm-scroll">
            <table class="qm-table">
                <caption class="sr-only">{{ kind === 'describe' ? 'Fields of the table on each server' : 'Tables each server answers' }}</caption>
                <thead>
                    <tr>
                        <th scope="col">{{ kind === 'describe' ? 'Field' : 'Table' }}</th>
                        <template v-if="kind === 'describe'">
                            <th scope="col">Type</th>
                            <th scope="col">Operators</th>
                            <th scope="col">Level</th>
                        </template>
                        <th v-for="server in servers" :key="server.id" scope="col" class="qm-server" :title="server.name">
                            {{ server.name }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="line in shownLines" :key="line.name" :class="{ 'qm-partial': line.partial }">
                        <th scope="row" class="qm-name"><code>{{ line.name }}</code></th>
                        <template v-if="kind === 'describe'">
                            <td class="qm-type">{{ line.type }}</td>
                            <td class="qm-ops"><code v-for="op in line.operators" :key="op">{{ op }}</code></td>
                            <td class="qm-level">{{ line.level }}</td>
                        </template>
                        <td v-for="server in servers" :key="server.id" class="qm-cell">
                            <i
                                v-if="line.on.has(server.id)"
                                class="fas fa-check qm-yes"
                                :title="`${server.name} has ${line.name}`"
                            ></i>
                            <span v-else class="qm-no" :title="`${server.name} lacks ${line.name}`">—</span>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <p v-if="kind === 'describe' && limits" class="qm-note">
            <i class="fas fa-circle-info mr-1" aria-hidden="true"></i>{{ limits }}
        </p>
        <p v-if="partialCount > 0" class="qm-note">
            {{ partialCount }} {{ kind === 'describe' ? 'field' : 'table' }}{{ partialCount === 1 ? ' is' : 's are' }} not on every server.
        </p>
    </template>
</div>
</template>

<script>
const LIMIT_NAMES = { max_depth: "depth", max_nodes: "conditions", max_list: "IN list", max_value_length: "value length" }

function limitsText(limits) {
    return Object.entries(limits || {}).map(([name, value]) => `${LIMIT_NAMES[name] || name} ${value}`).join(" · ")
}

// DESCRIBE as fields × servers, SHOW TABLES as tables × servers: what each server has, and what some lack
export default {
    name: "QueryMatrix",
    props: {
        // describe or show_tables
        kind: { type: String, required: true },
        results: { type: Array, default: () => [] },
        // The table names in mispql's order, for SHOW TABLES
        tableOrder: { type: Array, default: () => [] },
    },
    data() {
        return { search: "" }
    },
    computed: {
        answered() {
            const wanted = this.kind === "describe" ? "describe" : "tables"
            return this.results.filter(result => result.response && result.response.outcome === wanted)
        },
        servers() {
            return this.answered.map(result => ({ id: result.server_id, name: result.server_name }))
        },
        lines() {
            const lines = {}
            const order = []
            this.answered.forEach((result) => {
                if (this.kind === "describe") {
                    const fields = (result.response.describe || {}).fields || {}
                    Object.entries(fields).forEach(([name, info]) => {
                        if (!lines[name]) {
                            lines[name] = { name, types: new Set(), operators: new Set(), levels: new Set(), on: new Set() }
                            order.push(name)
                        }
                        lines[name].types.add(info.type)
                        ;(info.operators || []).forEach(op => lines[name].operators.add(op))
                        ;[].concat(info.level || []).forEach(level => lines[name].levels.add(level))
                        lines[name].on.add(result.server_id)
                    })
                } else {
                    (result.response.tables || []).forEach((name) => {
                        if (!lines[name]) {
                            lines[name] = { name, on: new Set() }
                            order.push(name)
                        }
                        lines[name].on.add(result.server_id)
                    })
                }
            })
            if (this.kind !== "describe") {
                const rank = name => (this.tableOrder.indexOf(name) === -1 ? 1000 : this.tableOrder.indexOf(name))
                order.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
            }
            const total = this.servers.length
            return order.map((name) => {
                const line = lines[name]
                return Object.assign({}, line, {
                    partial: line.on.size < total,
                    type: line.types ? Array.from(line.types).join(" / ") : "",
                    operators: line.operators ? Array.from(line.operators) : [],
                    level: line.levels ? Array.from(line.levels).join(", ") : "",
                })
            })
        },
        shownLines() {
            const needle = this.search.trim().toLowerCase()
            return needle ? this.lines.filter(line => line.name.toLowerCase().includes(needle)) : this.lines
        },
        partialCount() {
            return this.lines.filter(line => line.partial).length
        },
        limits() {
            const texts = this.answered.map(result => limitsText((result.response.describe || {}).limits))
            const distinct = Array.from(new Set(texts.filter(Boolean)))
            if (distinct.length === 0) {
                return ""
            }
            if (distinct.length === 1) {
                return `Limits: ${distinct[0]}`
            }
            return `Limits differ: ${this.answered.map((result, index) => `${result.server_name}: ${texts[index] || 'none'}`).join("; ")}`
        },
    },
}
</script>

<style scoped>
.qm-search {
    max-width: 18rem;
    margin-bottom: 0.6rem;
}

.qm-empty {
    margin: 0;
    color: #5a6270;
    font-size: 0.88rem;
}

.qm-scroll {
    max-height: 32rem;
    overflow: auto;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
}

.qm-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
}

.qm-table th,
.qm-table td {
    padding: 0.4rem 0.7rem;
    border-bottom: 1px solid #eef0f3;
    vertical-align: middle;
}

.qm-table thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f6f7f9;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #5a6270;
    white-space: nowrap;
}

.qm-table tbody tr:last-child th,
.qm-table tbody tr:last-child td {
    border-bottom: 0;
}

.qm-server {
    max-width: 9rem;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: center;
    text-transform: none !important;
    letter-spacing: 0 !important;
}

.qm-name code {
    color: var(--var-color-yankeesblue);
    font-size: 0.84rem;
}

.qm-type,
.qm-level {
    color: #5a6270;
    white-space: nowrap;
}

.qm-ops code {
    display: inline-block;
    margin: 0 0.2rem 0.15rem 0;
    padding: 0 0.3rem;
    border-radius: 3px;
    background: #f1f3f5;
    color: #b4235a;
    font-size: 0.75rem;
    white-space: nowrap;
}

.qm-cell {
    text-align: center;
}

.qm-yes {
    color: var(--health-ok);
}

.qm-no {
    color: #b3b9c1;
}

.qm-partial {
    background: #fffbf2;
}

.qm-note {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
    color: #5a6270;
}
</style>
