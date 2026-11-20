<template>
    <b-modal
        :id="modalId"
        :title="title"
        size="lg"
        :busy="saving"
        @show="onShow"
        @shown="focusName"
    >
        <b-alert v-if="message" show variant="danger" class="sq-alert">{{ message }}</b-alert>
        <b-form class="sq-form" novalidate @submit.prevent="submit()">
            <b-form-group
                label="Name"
                label-for="sq-name"
                :invalid-feedback="errors.name"
                :state="errors.name ? false : null"
            >
                <b-form-input
                    id="sq-name"
                    ref="name"
                    v-model="form.name"
                    maxlength="120"
                    autocomplete="off"
                    placeholder="e.g. No tlp:red events"
                    :state="errors.name ? false : null"
                    @input="errors.name = null"
                ></b-form-input>
            </b-form-group>
            <b-form-group
                label="Description"
                label-for="sq-description"
                description="Optional. Shown with the issues it raises, so say why it matters."
                :invalid-feedback="errors.description"
                :state="errors.description ? false : null"
            >
                <b-form-textarea
                    id="sq-description"
                    v-model="form.description"
                    rows="2"
                    max-rows="4"
                    maxlength="500"
                ></b-form-textarea>
            </b-form-group>

            <div class="sq-what">
                <div class="sq-what-item">
                    <span class="sq-label">Statement</span>
                    <pre class="sq-statement">{{ statementShown }}</pre>
                    <p v-if="statementChanged" class="sq-statement-change">
                        <i class="fas fa-rotate-left" aria-hidden="true"></i>
                        A new statement asks another question: its servers' last answers and its history start again.
                    </p>
                    <ul v-if="statementErrors.length" class="sq-statement-errors">
                        <li v-for="(error, index) in statementErrors" :key="index">
                            <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>
                            {{ error.message }}<span v-if="error.line"> (line {{ error.line }}, column {{ error.column }})</span>
                        </li>
                    </ul>
                </div>
                <div class="sq-what-item">
                    <span class="sq-label" id="sq-target-label">Runs on</span>
                    <template v-if="selected">
                        <div v-if="fleetsWhole.length" class="sq-target" role="group" aria-labelledby="sq-target-label">
                            <b-form-checkbox v-for="entry in fleetsWhole" :key="entry.id" v-model="form.follow" :value="entry.id">
                                Follow fleet <strong>{{ entry.name }}</strong>
                                <span class="sq-hint">servers added to it later run it too ({{ entry.servers.length }} now)</span>
                            </b-form-checkbox>
                        </div>
                        <p v-if="others.length" :class="['sq-target-text', { 'is-extra': fleetsWhole.length > 0 }]">
                            {{ othersLead }} <span class="sq-hint">{{ serverNames }}</span>
                        </p>
                    </template>
                    <p v-else class="sq-target-text">
                        {{ savedTarget }}
                        <span class="sq-hint">Open it in Query to change its statement or servers.</span>
                    </p>
                    <p v-if="errors.target" class="sq-field-error">{{ errors.target }}</p>
                </div>
            </div>

            <template v-if="checkable">
                <div class="sq-row">
                    <b-form-group
                        label="Schedule"
                        label-for="sq-schedule"
                        class="sq-schedule"
                        :invalid-feedback="errors.schedule_minutes"
                        :state="errors.schedule_minutes ? false : null"
                    >
                        <b-form-select id="sq-schedule" v-model="form.schedule" :options="scheduleOptions"></b-form-select>
                    </b-form-group>
                    <b-form-group
                        :label="kind === 'count' ? 'Each server\'s count should be' : 'Each server should find'"
                        :label-for="kind === 'count' ? 'sq-comparator' : null"
                        class="sq-expect"
                        :invalid-feedback="errors.expectation"
                        :state="errors.expectation ? false : null"
                    >
                        <div v-if="kind === 'count'" class="sq-expect-count">
                            <b-form-select id="sq-comparator" v-model="form.comparator" :options="comparatorOptions"></b-form-select>
                            <b-form-input
                                v-if="form.comparator"
                                v-model.number="form.value"
                                type="number"
                                min="0"
                                step="1"
                                aria-label="Expected count"
                                class="sq-expect-value"
                            ></b-form-input>
                        </div>
                        <b-form-radio-group
                            v-else
                            v-model="form.rows"
                            :options="rowOptions"
                            buttons
                            button-variant="outline-secondary"
                            class="sq-rows"
                        ></b-form-radio-group>
                    </b-form-group>
                </div>
                <b-form-group v-if="expectation" label="When a server's answer is not as expected" class="mb-2">
                    <div class="sq-severity" role="radiogroup" aria-label="Severity">
                        <button
                            v-for="option in severityOptions"
                            :key="option.value"
                            type="button"
                            role="radio"
                            :aria-checked="form.severity === option.value ? 'true' : 'false'"
                            :class="['sq-severity-option', `sev-${option.value}`, { active: form.severity === option.value }]"
                            @click="form.severity = option.value"
                        >
                            <i :class="option.icon" aria-hidden="true"></i> {{ option.text }}
                        </button>
                    </div>
                </b-form-group>
            </template>

            <p class="sq-consequence">
                <i class="fas fa-circle-info" aria-hidden="true"></i>
                <span>{{ consequence }}</span>
            </p>
            <p v-if="checkable && form.schedule && options && options.scheduled_runs === false" class="sq-off">
                <i class="fas fa-pause" aria-hidden="true"></i>
                Scheduled runs are turned off in the settings (Queries): it will only run by hand until they are on.
            </p>
        </b-form>

        <template #modal-footer="{ cancel }">
            <b-button variant="outline-secondary" :disabled="saving" @click="cancel()">Cancel</b-button>
            <b-button
                v-if="mode === 'update' && selected"
                variant="outline-primary"
                :disabled="saving || !canSubmit"
                title="Keep the saved query as it was, and save this as another one"
                @click="submit('create')"
            >Save as new</b-button>
            <b-button variant="primary" :disabled="saving || !canSubmit" @click="submit()">
                <b-spinner v-if="saving" small class="mr-1"></b-spinner>{{ mode === 'update' ? 'Save changes' : 'Save' }}
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import { SEVERITY_META } from "@/views/attention/healthLabels"
import api from "@/api/queries"
import {
    CHECKED_KINDS, consequenceText, expectationForm, formExpectation, otherServers, savedBody, targetText, wholeFleets,
} from "@/helpers/savedQueries"

const SEVERITIES = ["info", "warning", "critical"]
const NAMES_SHOWN = 4

function emptyForm() {
    return { name: "", description: "", follow: [], schedule: null, comparator: "", value: 0, rows: "none", severity: "warning" }
}

// Saves a statement with its servers, schedule and expectation: a new saved query, or changes to one. Without
// `statement` and `selected`, only the details (name, schedule, expectation…) are changed
export default {
    name: "SaveQueryModal",
    props: {
        modalId: { type: String, default: "modal-save-query" },
        // "create" or "update"
        mode: { type: String, default: "create" },
        // The saved query changed, or the one a new one starts from
        saved: { type: Object, default: null },
        // What to save; null keeps the saved query's
        statement: { type: String, default: null },
        kind: { type: String, default: null },
        selected: { type: Array, default: null },
        fleets: { type: Array, default: () => [] },
        // The language's `saved`: schedules, comparators, severities
        options: { type: Object, default: null },
    },
    data() {
        return {
            form: emptyForm(),
            errors: {},
            statementErrors: [],
            message: "",
            saving: false,
        }
    },
    computed: {
        title() {
            if (this.mode === "update" && this.saved) {
                return this.selected ? `Save changes to “${this.saved.name}”` : `Edit “${this.saved.name}”`
            }
            return "Save this query"
        },
        statementShown() {
            return this.statement !== null ? this.statement : (this.saved && this.saved.statement) || ""
        },
        // Saving changes with another statement drops what was kept for the old one
        statementChanged() {
            return this.mode === "update" && Boolean(this.saved) && this.statement !== null && this.statement !== this.saved.statement
        },
        checkable() {
            return CHECKED_KINDS.includes(this.kind)
        },
        // The fleets whose servers are all selected: each may be followed
        fleetsWhole() {
            return this.selected ? wholeFleets(this.selected, this.fleets) : []
        },
        // The selected servers no followed fleet holds: listed on their own
        others() {
            return this.selected ? otherServers(this.selected, this.form.follow, this.fleetsWhole) : []
        },
        othersLead() {
            const count = this.others.length
            const servers = `${count} server${count === 1 ? "" : "s"}`
            if (this.fleetsWhole.length === 0) {
                return servers
            }
            return this.form.follow.length > 0 ? `Plus ${servers}` : `These ${servers} only`
        },
        serverNames() {
            const byId = {}
            this.fleets.forEach(fleet => fleet.servers.forEach((server) => { byId[server.id] = server.name }))
            const names = this.others.map(id => byId[id] || `#${id}`)
            const shown = names.slice(0, NAMES_SHOWN).join(", ")
            return names.length > NAMES_SHOWN ? `${shown} and ${names.length - NAMES_SHOWN} more` : shown
        },
        savedTarget() {
            return this.saved ? targetText(this.saved) : ""
        },
        scheduleOptions() {
            const schedules = (this.options && this.options.schedules) || []
            return [{ value: null, text: "By hand only" }].concat(schedules.map(entry => ({ value: entry.minutes, text: entry.label })))
        },
        comparatorOptions() {
            const comparators = (this.options && this.options.comparators) || []
            return [{ value: "", text: "Anything: no expectation" }]
                .concat(comparators.map(entry => ({ value: entry.name, text: `${entry.symbol}  ${entry.words}` })))
        },
        rowOptions() {
            const rows = (this.options && this.options.row_expectations) || []
            const labels = { "eq:0": ["no_rows", "No rows"], "gt:0": ["some_rows", "Some rows"] }
            return [{ value: "none", text: "Anything" }].concat(rows.map((entry) => {
                const [value, text] = labels[`${entry.comparator}:${entry.value}`] || [entry.label, entry.label]
                return { value, text }
            }))
        },
        severityOptions() {
            return SEVERITIES.map(value => ({ value, text: SEVERITY_META[value].label, icon: SEVERITY_META[value].icon }))
        },
        expectation() {
            return formExpectation(this.kind, this.form)
        },
        expectationValid() {
            if (this.kind !== "count" || !this.form.comparator) {
                return true
            }
            const value = this.form.value
            return Number.isInteger(value) && value >= 0
        },
        consequence() {
            return consequenceText({
                kind: this.kind,
                schedule: this.form.schedule,
                expectation: this.expectation,
                severity: this.form.severity,
                schedules: this.options && this.options.schedules,
                options: this.options,
            })
        },
        canSubmit() {
            return this.form.name.trim() !== "" && this.expectationValid && Boolean(this.statementShown.trim())
                && (!this.selected || this.selected.length > 0)
        },
    },
    methods: {
        onShow() {
            const saved = this.saved
            const form = emptyForm()
            if (saved) {
                Object.assign(form, {
                    name: this.mode === "update" ? saved.name : `${saved.name} (copy)`,
                    description: saved.description || "",
                    schedule: saved.schedule_minutes,
                    severity: saved.severity || "warning",
                }, saved.kind === this.kind ? expectationForm(this.kind, saved.expectation) : {})
            }
            // Every whole fleet is followed in a new saved query; one being changed follows those it followed
            const whole = this.fleetsWhole.map(fleet => fleet.id)
            form.follow = saved ? whole.filter(id => (saved.fleet_ids || []).includes(id)) : whole
            if (!this.checkable) {
                form.schedule = null
            }
            this.form = form
            this.errors = {}
            this.statementErrors = []
            this.message = ""
        },
        focusName() {
            const input = this.$refs.name && this.$refs.name.$el
            if (input) {
                input.focus()
                if (this.mode !== "update") {
                    input.select()
                }
            }
        },
        submit(mode = this.mode) {
            if (!this.canSubmit || this.saving) {
                return
            }
            this.saving = true
            this.errors = {}
            this.statementErrors = []
            this.message = ""
            const body = savedBody(this.form, { kind: this.kind, statement: this.statement, selected: this.selected, fleets: this.fleetsWhole })
            const request = mode === "update" ? api.savedUpdate(this.saved.id, body) : api.savedCreate(body)
            request.then((answer) => {
                if (!answer.ok) {
                    this.statementErrors = answer.errors || []
                    if (answer.field && answer.field !== "statement" && answer.field in { name: 1, description: 1, target: 1, schedule_minutes: 1, expectation: 1 }) {
                        this.$set(this.errors, answer.field, answer.message)
                    } else if (!this.statementErrors.length) {
                        this.message = answer.message || "Could not save it"
                    }
                    return
                }
                const saved = Object.assign({}, answer)
                delete saved.ok
                this.$emit("saved", saved, mode)
                this.$bvModal.hide(this.modalId)
            }).catch((error) => {
                this.message = String(error)
            }).finally(() => {
                this.saving = false
            })
        },
    },
}
</script>

<style scoped>
.sq-alert {
    font-size: 0.88rem;
}

.sq-what {
    display: grid;
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    gap: 0.75rem 1.25rem;
    margin-bottom: 1rem;
    padding: 0.75rem 0.85rem;
    border-radius: 6px;
    background: #f8f9fb;
    border: 1px solid #eef0f3;
}

.sq-what-item {
    min-width: 0;
}

.sq-label {
    display: block;
    margin-bottom: 0.3rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.sq-statement {
    margin: 0;
    max-height: 7rem;
    overflow: auto;
    font-size: 0.8rem;
    color: #3c4452;
    white-space: pre-wrap;
    word-break: break-word;
}

.sq-statement-change {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0.4rem 0 0;
    font-size: 0.82rem;
    color: var(--health-warning-ink);
}

.sq-statement-errors {
    margin: 0.4rem 0 0;
    padding: 0;
    list-style: none;
    font-size: 0.82rem;
    color: var(--health-critical-ink);
}

.sq-target {
    font-size: 0.88rem;
}

.sq-target >>> .custom-control {
    margin-bottom: 0.3rem;
}

.sq-target-text.is-extra {
    margin-top: 0.15rem;
    padding-left: 1.5rem;
}

.sq-target-text {
    margin: 0;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.sq-hint {
    display: block;
    font-weight: 400;
    font-size: 0.78rem;
    color: #6b7380;
}

.sq-field-error {
    margin: 0.3rem 0 0;
    font-size: 0.8rem;
    color: var(--health-critical-ink);
}

.sq-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1.25rem;
}

.sq-schedule {
    flex: 1 1 12rem;
}

.sq-expect {
    flex: 2 1 18rem;
}

.sq-expect-count {
    display: flex;
    gap: 0.5rem;
}

.sq-expect-count select {
    flex: 1 1 auto;
}

.sq-expect-value {
    flex: 0 0 8rem;
}

.sq-rows {
    display: flex;
    width: 100%;
}

.sq-rows >>> .btn {
    flex: 1 1 0;
    font-size: 0.86rem;
}

.sq-severity {
    display: inline-flex;
    padding: 2px;
    border-radius: 6px;
    background: #eef0f3;
}

.sq-severity-option {
    border: none;
    background: none;
    padding: 0.25rem 0.8rem;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #4a5260;
}

.sq-severity-option i {
    margin-right: 0.2rem;
}

.sq-severity-option.active {
    background: #fff;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.12);
}

.sq-severity-option.sev-critical.active,
.sq-severity-option.sev-critical:hover i {
    color: var(--health-critical-ink);
}

.sq-severity-option.sev-warning.active,
.sq-severity-option.sev-warning:hover i {
    color: var(--health-warning-ink);
}

.sq-severity-option.sev-info.active,
.sq-severity-option.sev-info:hover i {
    color: var(--health-info-ink);
}

.sq-severity-option:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.sq-consequence {
    display: flex;
    gap: 0.5rem;
    margin: 0.5rem 0 0;
    padding: 0.55rem 0.75rem;
    border-radius: 6px;
    background: var(--health-focus-bg);
    font-size: 0.86rem;
    color: #3c4452;
}

.sq-consequence i {
    margin-top: 0.2rem;
    color: var(--var-color-lapislazuli);
}

.sq-off {
    margin: 0.5rem 0 0;
    font-size: 0.82rem;
    color: var(--health-warning-ink);
}

@media (max-width: 575.98px) {
    .sq-what {
        grid-template-columns: minmax(0, 1fr);
    }
}
</style>
