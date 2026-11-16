<template>
    <div class="baseline">
        <b-alert :show="!!error" variant="danger">
            <strong>Could not load the baseline.</strong> {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="fetch()">Try again</b-button>
        </b-alert>

        <div v-if="!loaded && !error" class="baseline-loading" role="status">
            <b-spinner small class="mr-2"></b-spinner>Loading the baseline…
        </div>

        <!-- No rule yet -->
        <section v-else-if="loaded && rules.length === 0" class="baseline-empty" aria-labelledby="baseline-empty-title">
            <div class="baseline-empty-icon" aria-hidden="true"><i class="fas fa-ruler-combined"></i></div>
            <h2 id="baseline-empty-title" class="baseline-empty-title">No baseline for this fleet yet</h2>
            <p class="baseline-empty-text">
                A baseline lists the settings, taxonomies, galaxies, object templates, organisations, sharing groups and custom galaxies every server of the fleet should have.
                Servers that drift from it show here, in Needs attention and in the fleet table.
            </p>
            <div class="baseline-empty-actions">
                <b-button variant="primary" :disabled="servers.length === 0" @click="openReference">
                    <i class="fas fa-server mr-1" aria-hidden="true"></i>Start from a reference server
                </b-button>
                <b-button variant="outline-primary" @click="openAdd">
                    <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add a rule
                </b-button>
                <b-button v-if="otherFleets.length > 0" variant="outline-secondary" @click="openCopy">
                    <i class="fas fa-copy mr-1" aria-hidden="true"></i>Copy from another fleet
                </b-button>
            </div>
            <p v-if="servers.length === 0" class="baseline-empty-hint">Add servers to the fleet to pick rules from one of them.</p>
        </section>

        <template v-else-if="loaded">
            <div class="baseline-head">
                <div class="baseline-status" aria-live="polite">
                    <span :class="['baseline-verdict', verdict.tone]">
                        <i :class="verdict.icon" aria-hidden="true"></i> {{ verdict.text }}
                    </span>
                    <span class="baseline-counts">
                        {{ rules.length }} rule{{ rules.length === 1 ? '' : 's' }} · {{ servers.length }} server{{ servers.length === 1 ? '' : 's' }}
                        <template v-if="totals.unknown > 0"> · <span :title="unknownTitle">{{ totals.unknown }} unknown</span></template>
                    </span>
                </div>
                <div class="baseline-actions">
                    <b-button
                        v-if="fixableDrift > 0"
                        size="sm"
                        variant="outline-primary"
                        @click="openFix({})"
                    >
                        <i class="fas fa-wrench mr-1" aria-hidden="true"></i>Fix all drift
                    </b-button>
                    <b-button
                        v-if="hasContentRules"
                        size="sm"
                        variant="outline-secondary"
                        :disabled="checking"
                        title="List the taxonomies, galaxies, object templates, organisations and sharing groups of every server again"
                        @click="checkContent"
                    >
                        <i :class="['fas fa-rotate mr-1', { 'fa-spin': checking }]" aria-hidden="true"></i>Check content
                    </b-button>
                    <b-dropdown size="sm" variant="primary" split right @click="openAdd">
                        <template #button-content>
                            <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add rule
                        </template>
                        <b-dropdown-item-button :disabled="servers.length === 0" @click="openReference">
                            <i class="fas fa-server fa-fw mr-1" aria-hidden="true"></i>From a reference server…
                        </b-dropdown-item-button>
                        <b-dropdown-item-button :disabled="otherFleets.length === 0" @click="openCopy">
                            <i class="fas fa-copy fa-fw mr-1" aria-hidden="true"></i>Copy from another fleet…
                        </b-dropdown-item-button>
                        <b-dropdown-divider></b-dropdown-divider>
                        <b-dropdown-item-button variant="danger" @click="clearAll">
                            <i class="fas fa-trash-can fa-fw mr-1" aria-hidden="true"></i>Remove all rules
                        </b-dropdown-item-button>
                    </b-dropdown>
                </div>
            </div>

            <div class="baseline-filters">
                <div class="baseline-filter" role="group" aria-label="Show">
                    <button
                        v-for="option in filterOptions"
                        :key="option.value"
                        type="button"
                        :class="['baseline-filter-option', { active: filter === option.value }]"
                        :aria-pressed="filter === option.value ? 'true' : 'false'"
                        @click="filter = option.value"
                    >
                        {{ option.label }}<span class="baseline-filter-count">{{ option.count }}</span>
                    </button>
                </div>
                <b-input-group size="sm" class="baseline-search">
                    <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
                    <b-form-input v-model="search" type="search" placeholder="Search rules" aria-label="Search rules"></b-form-input>
                </b-input-group>
                <span class="baseline-legend" aria-hidden="true">
                    <span><i class="fas fa-check legend-match"></i> In line</span>
                    <span><i class="fas fa-xmark legend-drift"></i> Drift</span>
                    <span><i class="fas fa-question legend-unknown"></i> Unknown</span>
                    <span><i class="fas fa-clock-rotate-left legend-unknown"></i> Unreachable</span>
                </span>
            </div>

            <DriftMatrix
                v-if="shownRules.length > 0"
                :rules="shownRules"
                :servers="servers"
                :highlight-rule-id="highlightRuleId"
                :refreshing="refreshing"
                @edit="openEdit"
                @delete="deleteRule"
                @fix="openFix"
            ></DriftMatrix>
            <div v-else class="baseline-none">
                <template v-if="filter === 'drift' && search.trim() === ''">
                    <i class="fas fa-circle-check mr-1 text-success" aria-hidden="true"></i>Every server is in line with the baseline.
                </template>
                <template v-else>No rule matches.</template>
                <b-button variant="link" size="sm" @click="filter = 'all'; search = ''">Show all rules</b-button>
            </div>
        </template>

        <RuleModal
            :fleet-id="fleetId"
            :types="types"
            :servers="servers"
            :rules="rules"
            :rule="editingRule"
            @saved="onSaved"
        ></RuleModal>
        <ReferenceImportModal
            :fleet-id="fleetId"
            :servers="servers"
            :rules="rules"
            @saved="onSaved"
        ></ReferenceImportModal>
        <RemediationModal :fleet-id="fleetId" :scope="fixScope"></RemediationModal>

        <b-modal
            id="modal-baseline-copy"
            title="Copy a baseline from another fleet"
            ok-title="Copy"
            cancel-variant="outline-secondary"
            :ok-disabled="copy.fleetId === null || copy.saving"
            @show="copy.error = null"
            @ok="submitCopy"
        >
            <b-form-group label="Fleet" label-for="copy-fleet">
                <b-form-select id="copy-fleet" v-model="copy.fleetId" :options="otherFleets"></b-form-select>
            </b-form-group>
            <b-form-group v-if="rules.length > 0" label="This fleet's rules" class="mb-0">
                <b-form-radio-group v-model="copy.mode" stacked name="copy-mode" :options="copyModes"></b-form-radio-group>
            </b-form-group>
            <b-alert :show="!!copy.error" variant="danger" class="mt-3 mb-0">{{ copy.error }}</b-alert>
        </b-modal>
    </div>
</template>

<script>
import { mapGetters } from "vuex"
import api from "@/api/baselines"
import DriftMatrix from "./DriftMatrix.vue"
import ReferenceImportModal from "./ReferenceImportModal.vue"
import RemediationModal from "./RemediationModal.vue"
import RuleModal from "./RuleModal.vue"
import { LISTED_TYPES, expectedText, ruleTitle } from "./baselineFormat"

// Health updates of a fleet's servers come in bursts (refresh of every server): one reload for the burst
const RELOAD_DELAY_MS = 800
let typesPromise = null

export default {
    name: "BaselineTab",
    components: { DriftMatrix, ReferenceImportModal, RemediationModal, RuleModal },
    props: {
        fleetId: { type: Number, required: true },
    },
    data() {
        return {
            matrix: null,
            types: null,
            loaded: false,
            refreshing: false,
            error: null,
            filter: "all",
            search: "",
            editingRule: null,
            fixScope: {},
            highlightRuleId: null,
            checking: false,
            reloadTimer: null,
            unsubscribe: null,
            copy: { fleetId: null, mode: "merge", saving: false, error: null },
            copyModes: [
                { value: "merge", text: "Keep them, and add the other fleet's rules (same rules are overwritten)" },
                { value: "replace", text: "Replace them with the other fleet's rules" },
            ],
        }
    },
    computed: {
        ...mapGetters({
            fleetList: "fleets/fleetList",
        }),
        rules() {
            return this.matrix ? this.matrix.rules : []
        },
        servers() {
            return this.matrix ? this.matrix.servers : []
        },
        totals() {
            return this.matrix ? this.matrix.totals : { match: 0, drift: 0, unknown: 0 }
        },
        serverIds() {
            return new Set(this.servers.map(server => server.id))
        },
        otherFleets() {
            return this.fleetList
                .filter(fleet => fleet.id !== this.fleetId)
                .map(fleet => ({ value: fleet.id, text: fleet.name }))
        },
        // Drifting values of rules that can be fixed from here (a version is upgraded by hand)
        fixableDrift() {
            return this.driftingRules.filter(rule => rule.remediable).length
        },
        hasContentRules() {
            return this.rules.some(rule => LISTED_TYPES.includes(rule.type))
        },
        statesByRule() {
            const states = {}
            this.rules.forEach((rule) => {
                const key = String(rule.id)
                states[rule.id] = this.servers.map(server => (server.results[key] || { state: "unknown" }).state)
            })
            return states
        },
        driftingRules() {
            return this.rules.filter(rule => this.statesByRule[rule.id].includes("drift"))
        },
        unknownRules() {
            return this.rules.filter(rule => this.statesByRule[rule.id].includes("unknown"))
        },
        filterOptions() {
            return [
                { value: "all", label: "All rules", count: this.rules.length },
                { value: "drift", label: "Drifting", count: this.driftingRules.length },
                { value: "unknown", label: "Unknown", count: this.unknownRules.length },
            ]
        },
        shownRules() {
            const base = this.filter === "drift" ? this.driftingRules : this.filter === "unknown" ? this.unknownRules : this.rules
            const search = this.search.trim().toLowerCase()
            if (search === "") {
                return base
            }
            return base.filter(rule => `${ruleTitle(rule)} ${rule.key} ${expectedText(rule)} ${rule.note}`.toLowerCase().includes(search))
        },
        verdict() {
            const drifting = this.servers.filter(server => server.drift > 0).length
            if (this.servers.length === 0) {
                return { tone: "is-muted", icon: "fas fa-circle-info", text: "No server to check" }
            }
            if (drifting > 0) {
                return {
                    tone: "is-drift",
                    icon: "fas fa-triangle-exclamation",
                    text: `${drifting} of ${this.servers.length} server${this.servers.length === 1 ? "" : "s"} drift${drifting === 1 ? "s" : ""} from the baseline`,
                }
            }
            if (this.totals.unknown > 0) {
                return { tone: "is-muted", icon: "fas fa-circle-question", text: "No drift found, some values are unknown" }
            }
            return { tone: "is-ok", icon: "fas fa-circle-check", text: "Every server is in line" }
        },
        unknownTitle() {
            return "Values this fleet cannot check now: unreachable servers, content not listed yet, settings MISP hides"
        },
        routeRuleId() {
            const id = parseInt(this.$route.query.rule, 10)
            return Number.isNaN(id) ? null : id
        },
    },
    watch: {
        fleetId() {
            this.matrix = null
            this.loaded = false
            this.filter = "all"
            this.search = ""
            this.fetch()
        },
        routeRuleId(id) {
            if (id === null) {
                this.highlightRuleId = null
            }
            this.revealRule()
        },
    },
    created() {
        if (typesPromise === null) {
            typesPromise = api.types().catch((error) => {
                typesPromise = null
                throw error
            })
        }
        typesPromise.then((types) => { this.types = types }).catch(() => {})
        this.fetch()
        // A server's health is published again whenever its drift may have changed (refresh, check, rule edit)
        this.unsubscribe = this.$store.subscribe((mutation) => {
            if (mutation.type === "health/setServerIssues" && mutation.payload && this.serverIds.has(mutation.payload.server_id)) {
                this.scheduleReload()
            }
        })
    },
    beforeDestroy() {
        clearTimeout(this.reloadTimer)
        if (this.unsubscribe) {
            this.unsubscribe()
        }
    },
    methods: {
        fetch() {
            const fleet_id = this.fleetId
            this.refreshing = this.loaded
            return api.drift(fleet_id)
                .then((matrix) => {
                    if (fleet_id !== this.fleetId) {
                        return
                    }
                    this.matrix = matrix
                    this.error = null
                    const firstLoad = !this.loaded
                    this.loaded = true
                    if (firstLoad) {
                        this.revealRule()
                    }
                })
                .catch((error) => {
                    if (fleet_id === this.fleetId) {
                        this.error = error.message
                    }
                })
                .finally(() => {
                    this.refreshing = false
                })
        },
        scheduleReload() {
            clearTimeout(this.reloadTimer)
            this.reloadTimer = setTimeout(() => this.fetch(), RELOAD_DELAY_MS)
        },
        // `?rule=` (from an issue's action): show that rule, whatever the filters
        revealRule() {
            const id = this.routeRuleId
            if (id === null || !this.loaded) {
                return
            }
            if (!this.rules.some(rule => rule.id === id)) {
                this.$bvToast.toast("This rule is no longer in the baseline.", { title: "Rule not found", variant: "warning" })
                return
            }
            if (!this.shownRules.some(rule => rule.id === id)) {
                this.filter = "all"
                this.search = ""
            }
            this.highlightRuleId = id
            this.$nextTick(() => {
                const row = document.getElementById(`baseline-rule-${id}`)
                if (row) {
                    row.scrollIntoView({ block: "center", behavior: "smooth" })
                }
            })
        },
        openAdd() {
            this.editingRule = null
            this.$nextTick(() => this.$bvModal.show("modal-baseline-rule"))
        },
        openEdit(rule) {
            this.editingRule = rule
            this.$nextTick(() => this.$bvModal.show("modal-baseline-rule"))
        },
        openFix(scope) {
            this.fixScope = scope
            this.$nextTick(() => this.$bvModal.show("modal-baseline-fix"))
        },
        openReference() {
            this.$bvModal.show("modal-baseline-reference")
        },
        openCopy() {
            if (this.copy.fleetId === null && this.otherFleets.length > 0) {
                this.copy.fleetId = this.otherFleets[0].value
            }
            this.$bvModal.show("modal-baseline-copy")
        },
        onSaved() {
            this.fetch()
        },
        deleteRule(rule) {
            this.$bvModal.msgBoxConfirm(`Servers will no longer be checked for ${ruleTitle(rule)} (${expectedText(rule)}).`, {
                title: "Remove this rule?",
                okTitle: "Remove",
                okVariant: "danger",
                cancelVariant: "outline-secondary",
                centered: true,
            }).then((confirmed) => {
                if (!confirmed) {
                    return
                }
                api.deleteRule(rule.id)
                    .then(() => this.fetch())
                    .catch((error) => {
                        this.$bvToast.toast(error.message, { title: "Could not remove the rule", variant: "danger" })
                    })
            })
        },
        clearAll() {
            this.$bvModal.msgBoxConfirm(`All ${this.rules.length} rules of this fleet's baseline will be removed, and their drift issues cleared.`, {
                title: "Remove the whole baseline?",
                okTitle: "Remove all rules",
                okVariant: "danger",
                cancelVariant: "outline-secondary",
                centered: true,
            }).then((confirmed) => {
                if (!confirmed) {
                    return
                }
                api.clear(this.fleetId)
                    .then(() => this.fetch())
                    .catch((error) => {
                        this.$bvToast.toast(error.message, { title: "Could not remove the baseline", variant: "danger" })
                    })
            })
        },
        submitCopy(event) {
            event.preventDefault()
            this.copy.saving = true
            this.copy.error = null
            const mode = this.rules.length === 0 ? "replace" : this.copy.mode
            api.copy(this.fleetId, this.copy.fleetId, mode)
                .then(() => {
                    this.$bvModal.hide("modal-baseline-copy")
                    this.fetch()
                })
                .catch((error) => {
                    this.copy.error = error.errors.length > 0
                        ? `${error.message}: ${error.errors.slice(0, 3).map(item => item.message).join("; ")}`
                        : error.message
                })
                .finally(() => {
                    this.copy.saving = false
                })
        },
        checkContent() {
            this.checking = true
            api.check(this.fleetId)
                .then((result) => {
                    const count = result.server_ids.length
                    this.$bvToast.toast(
                        count > 0 ? `Listing the content of ${count} server${count === 1 ? "" : "s"}. The matrix updates as each one answers.` : result.message,
                        { title: "Checking content", variant: "info" },
                    )
                })
                .catch((error) => {
                    this.$bvToast.toast(error.message, { title: "Could not check the content", variant: "danger" })
                })
                .finally(() => {
                    this.checking = false
                })
        },
    },
}
</script>

<style scoped>
.baseline {
    max-width: 1400px;
}

.baseline-loading {
    padding: 2rem 0;
    color: #5a6270;
}

.baseline-empty {
    max-width: 46rem;
    margin: 2rem auto;
    padding: 2rem 2rem 1.75rem;
    text-align: center;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
}

.baseline-empty-icon {
    width: 3rem;
    height: 3rem;
    margin: 0 auto 0.75rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--health-focus-bg);
    color: var(--var-color-lapislazuli);
    font-size: 1.25rem;
}

.baseline-empty-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
    margin-bottom: 0.5rem;
}

.baseline-empty-text {
    color: #4a5260;
    margin-bottom: 1.25rem;
}

.baseline-empty-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
}

.baseline-empty-hint {
    margin: 0.75rem 0 0;
    font-size: 0.85rem;
    color: #5a6270;
}

.baseline-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem 1rem;
    margin-bottom: 0.75rem;
}

.baseline-status {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.85rem;
}

.baseline-verdict {
    font-weight: 600;
    font-size: 1rem;
}

.baseline-verdict.is-drift {
    color: var(--health-critical-ink);
}

.baseline-verdict.is-ok {
    color: var(--health-ok-ink);
}

.baseline-verdict.is-muted {
    color: #4a5260;
}

.baseline-counts {
    font-size: 0.85rem;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

.baseline-actions {
    display: flex;
    gap: 0.5rem;
}

.baseline-filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin-bottom: 0.6rem;
}

.baseline-filter {
    display: inline-flex;
    padding: 2px;
    border-radius: 6px;
    background: #eef0f3;
}

.baseline-filter-option {
    border: none;
    background: none;
    padding: 0.2rem 0.7rem;
    border-radius: 4px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #4a5260;
    line-height: 1.5;
}

.baseline-filter-option:hover {
    color: var(--var-color-yankeesblue);
}

.baseline-filter-option.active {
    background: #fff;
    color: var(--var-color-yankeesblue);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.12);
}

.baseline-filter-option:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.baseline-filter-count {
    margin-left: 0.35rem;
    font-weight: 500;
    color: #6c737d;
    font-variant-numeric: tabular-nums;
}

.baseline-search {
    flex: 0 1 18rem;
}

.baseline-legend {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.85rem;
    margin-left: auto;
    font-size: 0.78rem;
    color: #5a6270;
}

.legend-match {
    color: var(--health-ok);
}

.legend-drift {
    color: var(--health-critical-ink);
}

.legend-unknown {
    color: #a0a6ae;
}

.baseline-none {
    padding: 2rem 1rem;
    text-align: center;
    color: #4a5260;
    background: #fff;
    border: 1px dashed var(--health-rule);
    border-radius: 6px;
}
</style>
