<template>
    <b-modal
        id="modal-sharing-group-baseline"
        :title="group ? `Add ${group.name} to the baseline` : 'Add to the baseline'"
        @show="reset"
    >
        <div v-if="group" class="sg-baseline">
            <p class="baseline-intro">
                Every server of <strong>{{ fleetName }}</strong> is then checked for this sharing group, by its UUID.
                A server without it, or with other values, shows as drifting, and can be fixed from the fleet's Baseline tab.
            </p>
            <fieldset class="check-fields">
                <legend>What to check</legend>
                <b-form-checkbox :checked="true" disabled class="check-row">
                    Present, named <strong>{{ group.name }}</strong>
                    <span class="check-hint">Created {{ group.roaming ? "roaming" : "not roaming" }} where a fix creates it.</span>
                </b-form-checkbox>
                <b-form-checkbox v-model="checks.checkMembers" :disabled="group.members.length === 0" class="check-row">
                    At least these {{ group.members.length }} member{{ group.members.length === 1 ? "" : "s" }}
                    <span class="check-hint">Other members a server adds are fine; missing ones drift and can be added.</span>
                </b-form-checkbox>
                <b-form-checkbox v-model="checks.checkActive" class="check-row">
                    {{ group.active ? "Active" : "Inactive" }} everywhere
                </b-form-checkbox>
                <b-form-checkbox v-for="field in fields" :key="field.key" v-model="checks[field.key]" :disabled="!field.value" class="check-row">
                    {{ field.label }}
                    <span v-if="field.value" class="check-value">{{ field.value }}</span>
                    <span v-else class="check-empty">(empty here)</span>
                </b-form-checkbox>
            </fieldset>
            <b-alert :show="conflict" variant="warning" class="baseline-alert">
                This sharing group is already a rule of the baseline. Replace that rule with this one?
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
import { baselineRule } from "@/helpers/sharingGroups"

function defaultChecks() {
    return { checkMembers: true, checkActive: true, checkReleasability: true, checkDescription: true }
}

export default {
    name: "SharingGroupBaselineModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        group: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            checks: defaultChecks(),
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
                { key: "checkReleasability", label: "Releasable to", value: this.group.releasability },
                { key: "checkDescription", label: "Description", value: this.group.description },
            ]
        },
    },
    methods: {
        reset() {
            this.checks = defaultChecks()
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
            const rule = baselineRule(this.group, this.checks)
            baselinesApi.addRules(this.fleet.id, [rule], this.conflict ? "replace" : "error")
                .then(() => {
                    this.$bvToast.toast(`${this.group.name} is now checked on every server of ${this.fleetName}. Open the Baseline tab to see where it drifts.`, {
                        title: this.conflict ? "Baseline rule replaced" : "Added to the baseline",
                        variant: "success",
                        solid: true,
                        to: { name: "fleet.view", params: { fleet_id: this.fleet.id }, query: { tab: "baseline" } },
                    })
                    this.$bvModal.hide("modal-sharing-group-baseline")
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
.sg-baseline {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.baseline-intro {
    color: #3c4650;
}

.check-fields {
    margin: 0;
}

.check-fields legend {
    margin-bottom: 0.35rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: #3c4650;
}

.check-row + .check-row {
    margin-top: 0.3rem;
}

.check-value {
    margin-left: 0.35em;
    color: #5a6270;
    overflow-wrap: anywhere;
}

.check-empty {
    margin-left: 0.35em;
    color: #9aa1a7;
}

.check-hint {
    display: block;
    color: #6c757d;
    font-size: 0.8rem;
}

.baseline-alert {
    margin: 0.75rem 0 0;
}
</style>
