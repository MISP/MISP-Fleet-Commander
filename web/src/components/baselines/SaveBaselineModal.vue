<template>
    <b-modal
        id="modal-baseline-save"
        title="Save as a saved baseline"
        cancel-variant="outline-secondary"
        @show="onShow"
        @shown="focusName"
    >
        <p class="save-intro">
            Keeps a copy of the {{ ruleCount }} of {{ fleetName }}, to import into other fleets.
            Later changes to this fleet do not change the copy.
        </p>

        <div v-if="saved.length > 0" class="save-target" role="radiogroup" aria-label="Save as">
            <b-form-radio v-model="target" value="new" name="save-target">A new saved baseline</b-form-radio>
            <b-form-radio v-model="target" value="update" name="save-target">In place of an existing one</b-form-radio>
        </div>

        <template v-if="target === 'new'">
            <b-form-group label="Name" label-for="save-name" :state="nameState" :invalid-feedback="nameError">
                <b-form-input
                    id="save-name"
                    ref="name"
                    v-model="name"
                    :state="nameState"
                    maxlength="120"
                    autocomplete="off"
                    @input="nameError = null"
                    @keydown.enter.prevent="submit"
                ></b-form-input>
            </b-form-group>
            <b-form-group label="Description" label-for="save-description" :description="`${description.length} / 500`" class="mb-0">
                <b-form-textarea
                    id="save-description"
                    v-model="description"
                    rows="2"
                    max-rows="5"
                    maxlength="500"
                    placeholder="What it is for (optional)"
                ></b-form-textarea>
            </b-form-group>
        </template>
        <template v-else>
            <b-form-group label="Saved baseline" label-for="save-existing">
                <b-form-select id="save-existing" v-model="existingId" :options="savedOptions"></b-form-select>
            </b-form-group>
            <p v-if="existing" class="save-replace">
                <i class="fas fa-triangle-exclamation mr-1" aria-hidden="true"></i>
                Its {{ ruleCountOf(existing.rule_count) }} are replaced by the {{ ruleCount }} of {{ fleetName }}. Its name and description stay.
            </p>
        </template>

        <ul v-if="notes.length > 0" class="save-notes">
            <li v-for="note in notes" :key="note"><i class="fas fa-circle-info mr-1" aria-hidden="true"></i>{{ note }}</li>
        </ul>

        <b-alert :show="!!error" variant="danger" class="mt-3 mb-0">{{ error }}</b-alert>

        <template #modal-footer="{ cancel }">
            <b-button variant="outline-secondary" @click="cancel()">Cancel</b-button>
            <b-button variant="primary" :disabled="!canSave" @click="submit">
                <b-spinner v-if="saving" small class="mr-1"></b-spinner>
                <i v-else class="fas fa-bookmark mr-1" aria-hidden="true"></i>{{ target === 'new' ? 'Save' : 'Replace its rules' }}
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/baselines"
import { ruleCountText } from "./baselineFormat"

// Keeps a copy of a fleet's baseline in the user's saved baselines
export default {
    name: "SaveBaselineModal",
    props: {
        fleetId: { type: Number, required: true },
        fleetName: { type: String, default: "this fleet" },
        rules: { type: Array, default: () => [] },
    },
    data() {
        return {
            saved: [],
            target: "new",
            name: "",
            description: "",
            existingId: null,
            nameError: null,
            error: null,
            saving: false,
        }
    },
    computed: {
        ruleCount() {
            return ruleCountText(this.rules.length)
        },
        savedOptions() {
            return this.saved.map(item => ({ value: item.id, text: `${item.name} (${ruleCountText(item.rule_count)})` }))
        },
        existing() {
            return this.saved.find(item => item.id === this.existingId) || null
        },
        nameState() {
            return this.nameError ? false : null
        },
        canSave() {
            if (this.saving) {
                return false
            }
            return this.target === "new" ? this.name.trim() !== "" : this.existingId !== null
        },
        notes() {
            const notes = []
            const forced = this.rules.filter(rule => rule.forced).length
            if (forced > 0) {
                notes.push(`${forced === 1 ? "One forced server-specific setting is" : `${forced} forced server-specific settings are`} kept: they will apply to every fleet it is imported into.`)
            }
            if (this.rules.some(rule => rule.type === "custom_galaxy")) {
                notes.push("Custom galaxies keep the server they are copied from.")
            }
            return notes
        },
    },
    methods: {
        ruleCountOf(count) {
            return ruleCountText(count)
        },
        onShow() {
            this.target = "new"
            this.name = this.fleetName
            this.description = ""
            this.existingId = null
            this.nameError = null
            this.error = null
            this.saving = false
            api.library()
                .then((library) => {
                    this.saved = library.saved
                    this.existingId = this.saved.length > 0 ? this.saved[0].id : null
                })
                .catch(() => {
                    this.saved = []
                })
        },
        focusName() {
            if (this.$refs.name) {
                this.$refs.name.select()
            }
        },
        submit() {
            if (!this.canSave) {
                return
            }
            this.saving = true
            this.error = null
            const request = this.target === "new"
                ? api.createSaved({ name: this.name, description: this.description, from_fleet_id: this.fleetId })
                : api.updateSaved(this.existingId, { from_fleet_id: this.fleetId })
            request
                .then((saved) => {
                    this.$emit("saved", saved)
                    this.$bvModal.hide("modal-baseline-save")
                })
                .catch((error) => {
                    if (error.field === "name") {
                        this.nameError = error.message
                    } else {
                        this.error = error.message
                    }
                })
                .finally(() => {
                    this.saving = false
                })
        },
    },
}
</script>

<style scoped>
.save-intro {
    color: #4a5260;
    font-size: 0.9rem;
}

.save-target {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem 1.25rem;
    margin-bottom: 1rem;
}

.save-replace {
    margin: 0;
    font-size: 0.875rem;
    color: var(--health-warning-ink);
}

.save-notes {
    list-style: none;
    margin: 1rem 0 0;
    padding: 0.5rem 0.75rem;
    background: var(--health-focus-bg);
    border-radius: 6px;
    font-size: 0.85rem;
    color: #3b4250;
}

.save-notes li + li {
    margin-top: 0.25rem;
}

.save-notes i {
    color: var(--var-color-lapislazuli);
}
</style>
