<template>
<div class="qp">
    <div class="qp-tools">
        <b-input-group v-if="serverCount > 8" size="sm" class="qp-search">
            <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
            <b-form-input v-model="search" type="search" placeholder="Find a server" aria-label="Find a server"></b-form-input>
        </b-input-group>
        <div class="qp-tool-buttons">
            <b-button size="sm" variant="link" class="qp-link" :disabled="supportedIds.length === 0" @click="selectSupported">
                Only those that can run queries
            </b-button>
            <b-button size="sm" variant="link" class="qp-link" :disabled="value.length === 0" @click="$emit('input', [])">
                Clear
            </b-button>
            <b-button size="sm" variant="outline-secondary" :disabled="checking || serverCount === 0" @click="$emit('recheck')">
                <i :class="['fas', 'fa-rotate-right', 'mr-1', { 'fa-spin': checking }]" aria-hidden="true"></i>Check again
            </b-button>
        </div>
    </div>

    <p v-if="fleets.length === 0" class="qp-empty">You have no fleets yet: add servers to a fleet to query them.</p>

    <section v-for="fleet in shownFleets" :key="fleet.id" class="qp-fleet" :aria-labelledby="`qp-fleet-${fleet.id}`">
        <header class="qp-fleet-header">
            <b-form-checkbox
                :checked="fleetState(fleet) === 'all'"
                :indeterminate="fleetState(fleet) === 'some'"
                :disabled="fleet.servers.length === 0"
                @change="toggleFleet(fleet, $event)"
            >
                <span :id="`qp-fleet-${fleet.id}`" class="qp-fleet-name">{{ fleet.name }}</span>
            </b-form-checkbox>
            <span class="qp-fleet-count">{{ selectedIn(fleet) }} / {{ fleet.servers.length }}</span>
        </header>
        <p v-if="fleet.loading" class="qp-fleet-note"><b-spinner small class="mr-1"></b-spinner>Loading its servers…</p>
        <p v-else-if="fleet.error" class="qp-fleet-note text-danger">Could not load its servers: {{ fleet.error }}</p>
        <p v-else-if="fleet.servers.length === 0" class="qp-fleet-note">No servers in this fleet.</p>
        <ul v-else class="qp-servers">
            <li v-for="server in fleet.servers" :key="server.id">
                <label :class="['qp-server', { selected: isSelected(server.id) }]">
                    <input
                        type="checkbox"
                        class="qp-check"
                        :checked="isSelected(server.id)"
                        @change="toggle(server.id, $event.target.checked)"
                    >
                    <span class="qp-server-name" :title="server.url">{{ server.name }}</span>
                    <span
                        :class="['qp-cap', `job-tone-${capability(server.id).tone}`]"
                        :title="capabilityTitle(server.id)"
                    >
                        <i :class="['fas', capability(server.id).icon]" aria-hidden="true"></i>
                        {{ capability(server.id).label }}
                    </span>
                </label>
            </li>
        </ul>
    </section>
    <p v-if="search && shownFleets.length === 0" class="qp-empty">No server matches “{{ search }}”.</p>
</div>
</template>

<script>
import { capabilityMeta } from "@/helpers/mispql"

// Which servers a statement runs on: the user's fleets and their servers, each with whether it can run complex
// queries. Servers that can't may be picked: the run skips them and says so
export default {
    name: "QueryServerPicker",
    props: {
        // [{id, name, servers: [{id, name, url}], loading, error}]
        fleets: { type: Array, default: () => [] },
        // server id -> capability ({state, detail, status}); absent while being checked
        capabilities: { type: Object, default: () => ({}) },
        // The selected server ids
        value: { type: Array, default: () => [] },
        checking: { type: Boolean, default: false },
    },
    data() {
        return { search: "" }
    },
    computed: {
        selected() {
            return new Set(this.value)
        },
        serverCount() {
            return this.fleets.reduce((total, fleet) => total + fleet.servers.length, 0)
        },
        supportedIds() {
            return this.fleets.flatMap(fleet => fleet.servers)
                .filter(server => (this.capabilities[server.id] || {}).state === "supported")
                .map(server => server.id)
        },
        shownFleets() {
            const needle = this.search.trim().toLowerCase()
            if (!needle) {
                return this.fleets
            }
            return this.fleets.map((fleet) => {
                if (fleet.name.toLowerCase().includes(needle)) {
                    return fleet
                }
                const servers = fleet.servers.filter(server => server.name.toLowerCase().includes(needle)
                    || String(server.url || "").toLowerCase().includes(needle))
                return servers.length ? Object.assign({}, fleet, { servers }) : null
            }).filter(Boolean)
        },
    },
    methods: {
        isSelected(id) {
            return this.selected.has(id)
        },
        selectedIn(fleet) {
            return fleet.servers.filter(server => this.selected.has(server.id)).length
        },
        fleetState(fleet) {
            const count = this.selectedIn(fleet)
            if (count === 0) {
                return "none"
            }
            return count === fleet.servers.length ? "all" : "some"
        },
        toggle(id, on) {
            const next = this.value.filter(other => other !== id)
            if (on) {
                next.push(id)
            }
            this.$emit("input", next)
        },
        toggleFleet(fleet, on) {
            const ids = new Set(fleet.servers.map(server => server.id))
            const next = this.value.filter(id => !ids.has(id))
            this.$emit("input", on ? next.concat(fleet.servers.map(server => server.id)) : next)
        },
        selectSupported() {
            this.$emit("input", this.supportedIds.slice())
        },
        capability(id) {
            const found = this.capabilities[id]
            return capabilityMeta(found ? found.state : null)
        },
        capabilityTitle(id) {
            const found = this.capabilities[id]
            if (!found) {
                return "Asking the server whether it runs complex queries"
            }
            const meta = capabilityMeta(found.state)
            const detail = found.detail ? `: ${found.detail}` : ""
            return `${meta.label} (${meta.short})${detail}`
        },
    },
}
</script>

<style scoped>
.qp-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 1rem;
    margin-bottom: 0.75rem;
}

.qp-search {
    max-width: 18rem;
}

.qp-tool-buttons {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-left: auto;
}

.qp-link {
    font-size: 0.82rem;
    padding-left: 0.35rem;
    padding-right: 0.35rem;
}

.qp-empty {
    margin: 0;
    color: #5a6270;
    font-size: 0.88rem;
}

.qp-fleet + .qp-fleet {
    margin-top: 0.9rem;
}

.qp-fleet-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
}

.qp-fleet-name {
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    font-size: 0.9rem;
}

.qp-fleet-count {
    font-size: 0.78rem;
    color: #8a919c;
    font-variant-numeric: tabular-nums;
}

.qp-fleet-note {
    margin: 0 0 0 1.5rem;
    font-size: 0.85rem;
    color: #5a6270;
}

.qp-servers {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
    gap: 0.35rem;
    margin: 0;
    padding: 0;
    list-style: none;
}

.qp-server {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    padding: 0.4rem 0.55rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    min-width: 0;
    transition: border-color 0.12s ease, background-color 0.12s ease;
}

.qp-server:hover {
    border-color: #b9c2cd;
}

.qp-server.selected {
    border-color: rgba(41, 120, 160, 0.55);
    background: #f3f8fb;
}

.qp-check {
    flex: none;
    margin: 0;
}

.qp-server-name {
    flex: 1 1 auto;
    min-width: 0;
    font-size: 0.88rem;
    color: var(--var-color-yankeesblue);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.qp-cap {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--job-ink);
    background: var(--job-tint);
    white-space: nowrap;
}
</style>
