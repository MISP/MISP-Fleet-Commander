<template>
    <b-modal
        id="modal-organisation-baseline"
        :title="org ? `Add ${org.name} to the baseline` : 'Add to the baseline'"
        @show="reset"
    >
        <div v-if="org" class="org-baseline">
            <p class="baseline-intro">
                Every server of <strong>{{ fleetName }}</strong> is then checked for this organisation, by its UUID.
                A server without it, or with other values, shows as drifting, and can be fixed from the fleet's Baseline tab.
            </p>

            <fieldset class="check-fields">
                <legend>What to check</legend>
                <b-form-checkbox :checked="true" disabled class="check-row">
                    Present, named <strong>{{ org.name }}</strong>
                </b-form-checkbox>
                <b-form-checkbox v-for="field in fields" :key="field.key" v-model="checks[field.key]" :disabled="!field.value" class="check-row">
                    {{ field.label }}
                    <span v-if="field.value" class="check-value">{{ field.value }}</span>
                    <span v-else class="check-empty">(empty here)</span>
                </b-form-checkbox>
                <b-form-checkbox v-model="checks.checkLocal" class="check-row">
                    {{ org.local ? "Local" : "External" }} everywhere
                    <span class="check-hint">Usually local on one server and external on the others: leave unticked unless every server should agree.</span>
                </b-form-checkbox>
            </fieldset>

            <b-alert :show="conflict" variant="warning" class="baseline-alert">
                This organisation is already a rule of the baseline. Replace that rule with this one?
            </b-alert>
            <b-alert :show="error !== null" variant="danger" class="baseline-alert">{{ error }}</b-alert>
        </div>

        <template #modal-footer="{ cancel }">
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
            <b-button :variant="conflict ? 'warning' : 'primary'" :disabled="saving" @click="save">
                <b-spinner v-if="saving" small class="mr-1"></b-spinner>{{ conflict ? "Replace the rule" : "Add the rule" }}
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import baselinesApi from "@/api/baselines"
import { baselineRule } from "@/helpers/organisations"

export default {
    name: "OrganisationBaselineModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        org: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            checks: { checkType: true, checkNationality: true, checkSector: true, checkLocal: false },
            conflict: false,
            saving: false,
            error: null,
        }
    },
    computed: {
        fleet() {
            return this.server.fleet || null
        },
        fleetName() {
            return (this.fleet && this.fleet.name) || "the fleet"
        },
        fields() {
            return [
                { key: "checkType", label: "Type", value: this.org.type },
                { key: "checkSector", label: "Sector", value: this.org.sector },
                { key: "checkNationality", label: "Nationality", value: this.org.nationality },
            ]
        },
    },
    methods: {
        reset() {
            this.checks = { checkType: true, checkNationality: true, checkSector: true, checkLocal: false }
            this.conflict = false
            this.saving = false
            this.error = null
        },
        save() {
            if (!this.fleet) {
                return
            }
            this.saving = true
            this.error = null
            const rule = baselineRule(this.org, this.checks)
            baselinesApi.addRules(this.fleet.id, [rule], this.conflict ? "replace" : "error")
                .then(() => {
                    this.$bvToast.toast(`${this.org.name} is now checked on every server of ${this.fleetName}. Open the Baseline tab to see where it drifts.`, {
                        title: this.conflict ? "Baseline rule replaced" : "Added to the baseline",
                        variant: "success",
                        solid: true,
                        to: { name: "fleet.view", params: { fleet_id: this.fleet.id }, query: { tab: "baseline" } },
                    })
                    this.$bvModal.hide("modal-organisation-baseline")
                })
                .catch((error) => {
                    if (error.status === 409 && !this.conflict) {
                        this.conflict = true
                        return
                    }
                    const detail = error.errors && error.errors.length > 0 ? error.errors.map(item => item.message || item).join("; ") : ""
                    this.error = detail ? `${error.message}: ${detail}` : error.message
                })
                .finally(() => { this.saving = false })
        },
    },
}
</script>

<style scoped>
.org-baseline {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.baseline-intro {
    color: #3c4650;
}

.check-fields {
    margin: 0 0 0.75rem;
    padding: 0;
    border: 0;
}

.check-fields legend {
    margin-bottom: 0.35rem;
    font-size: 0.95em;
    font-weight: 700;
}

.check-row + .check-row {
    margin-top: 0.3rem;
}

.check-value {
    margin-left: 0.3em;
    padding: 0 0.4em;
    border-radius: 0.2rem;
    background: #f1f3f5;
    color: #3c4650;
}

.check-empty {
    color: #9aa1a7;
}

.check-hint {
    display: block;
    color: #6c757d;
    font-size: 0.82rem;
}

.baseline-alert {
    margin-bottom: 0;
    padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
}
</style>
