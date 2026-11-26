<template>
    <b-modal
        :id="modalId"
        title="Follow a saved query on this tab"
        size="lg"
        scrollable
        :busy="saving"
        @show="onShow"
    >
        <b-alert v-if="message" show variant="danger" class="aw-alert">{{ message }}</b-alert>

        <div v-if="loading && !candidates" class="aw-loading" role="status">
            <b-spinner small class="mr-2"></b-spinner>Looking for your saved queries…
        </div>

        <div v-else-if="candidates && candidates.length === 0" class="aw-empty">
            <i class="fas fa-search" aria-hidden="true"></i>
            <div>
                <p class="aw-empty-title">None of your saved queries counts anything on this fleet's servers.</p>
                <p class="aw-empty-text">
                    A widget follows a saved SELECT or COUNT that runs on at least one of them. Write the statement on
                    the Query page with this fleet chosen, then save it: it shows up here.
                </p>
                <router-link :to="{ name: 'query', query: { fleet: String(fleetId) } }" class="btn btn-sm btn-primary">
                    <i class="fas fa-terminal mr-1" aria-hidden="true"></i>Query this fleet
                </router-link>
            </div>
        </div>

        <form v-else-if="candidates" class="aw-form" @submit.prevent="submit">
            <fieldset class="aw-fieldset">
                <legend class="aw-legend">Saved query</legend>
                <div class="aw-list" role="radiogroup" aria-label="Saved query">
                    <label
                        v-for="candidate in candidates"
                        :key="candidate.id"
                        :class="['aw-option', { 'is-chosen': chosen === candidate.id, 'is-disabled': candidate.added }]"
                    >
                        <input
                            v-model="chosen"
                            type="radio"
                            name="aw-saved"
                            class="aw-radio"
                            :value="candidate.id"
                            :disabled="candidate.added"
                        />
                        <span class="aw-option-body">
                            <span class="aw-option-name">{{ candidate.name }}</span>
                            <span class="aw-option-facts">{{ facts(candidate) }}</span>
                            <span class="aw-option-where">
                                <i class="fas fa-server" aria-hidden="true"></i>{{ where(candidate) }}
                            </span>
                        </span>
                        <span v-if="candidate.added" class="aw-added">Already on this tab</span>
                    </label>
                </div>
            </fieldset>

            <fieldset class="aw-fieldset">
                <legend class="aw-legend">Show it as</legend>
                <div class="aw-displays" role="radiogroup" aria-label="Show it as">
                    <label
                        v-for="option in DISPLAYS"
                        :key="option.key"
                        :class="['aw-display', { 'is-chosen': display === option.key }]"
                    >
                        <input v-model="display" type="radio" name="aw-display" class="aw-radio" :value="option.key" />
                        <i :class="['fas', option.icon, 'aw-display-icon']" aria-hidden="true"></i>
                        <span class="aw-option-body">
                            <span class="aw-option-name">{{ option.label }}</span>
                            <span class="aw-option-facts">{{ option.text }}</span>
                        </span>
                    </label>
                </div>
                <p class="aw-hint">You can switch it later from the widget's menu.</p>
            </fieldset>
        </form>

        <template #modal-footer="{ cancel }">
            <b-button variant="outline-secondary" :disabled="saving" @click="cancel()">Cancel</b-button>
            <b-button
                v-if="candidates && candidates.length > 0"
                variant="primary"
                :disabled="saving || !chosen"
                @click="submit"
            >
                <b-spinner v-if="saving" small class="mr-1"></b-spinner>Add to the tab
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/usageWidgets"
import { candidateWhere, DISPLAYS, widgetFacts } from "@/helpers/usageWidgets"

// Choose a saved query to follow on a fleet's Usage tab, and how to show it
export default {
    name: "AddQueryWidgetModal",
    props: {
        modalId: { type: String, required: true },
        fleetId: { type: Number, required: true },
        // The server the tab is limited to: the added widget comes back drawn for it
        serverId: { type: Number, default: null },
    },
    data() {
        return {
            DISPLAYS,
            candidates: null,
            fleetServers: 0,
            loading: false,
            saving: false,
            message: "",
            chosen: null,
            display: "total",
        }
    },
    methods: {
        onShow() {
            this.message = ""
            this.chosen = null
            this.display = "total"
            this.loading = true
            api.candidates(this.fleetId).then((answer) => {
                this.candidates = answer.saved || []
                this.fleetServers = answer.fleet_servers || 0
                const free = this.candidates.filter((candidate) => !candidate.added)
                // One to choose from: chosen already
                this.chosen = free.length === 1 ? free[0].id : null
            }).catch((error) => {
                this.message = `Could not list your saved queries: ${error}`
            }).finally(() => {
                this.loading = false
            })
        },
        facts(candidate) {
            return widgetFacts(candidate)
        },
        where(candidate) {
            return candidateWhere(candidate, this.fleetServers)
        },
        submit() {
            if (!this.chosen || this.saving) {
                return
            }
            this.saving = true
            this.message = ""
            api.add(this.fleetId, this.chosen, this.display, this.serverId).then((answer) => {
                if (!answer.ok) {
                    this.message = answer.message
                    return
                }
                this.$emit("added", answer)
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
.aw-alert {
    font-size: 0.875rem;
}

.aw-loading {
    color: #6c757d;
    font-size: 0.875rem;
}

.aw-empty {
    display: flex;
    gap: 0.9rem;
    padding: 0.4rem 0.2rem;
}

.aw-empty > i {
    margin-top: 0.2rem;
    color: #9aa6b5;
    font-size: 1.3rem;
}

.aw-empty-title {
    margin: 0 0 0.3rem;
    font-weight: 600;
}

.aw-empty-text {
    margin: 0 0 0.75rem;
    color: #52514e;
    font-size: 0.875rem;
    line-height: 1.5;
}

.aw-fieldset {
    margin: 0;
    padding: 0;
    border: 0;
    min-width: 0;
}

.aw-fieldset + .aw-fieldset {
    margin-top: 1.1rem;
}

.aw-legend {
    margin-bottom: 0.45rem;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.aw-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.aw-option,
.aw-display {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    margin: 0;
    padding: 0.55rem 0.75rem;
    border: 1px solid #dfe3e9;
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    transition: border-color 0.12s ease, background-color 0.12s ease;
}

.aw-option:hover,
.aw-display:hover {
    border-color: #b9c3d0;
}

.aw-option.is-chosen,
.aw-display.is-chosen {
    border-color: var(--primary, #007bff);
    background: #f3f8ff;
    box-shadow: inset 0 0 0 1px var(--primary, #007bff);
}

.aw-option:focus-within,
.aw-display:focus-within {
    outline: 2px solid rgba(0, 123, 255, 0.35);
    outline-offset: 1px;
}

.aw-option.is-disabled {
    cursor: default;
    background: #f8f9fb;
    color: #8a929c;
}

.aw-option.is-disabled:hover {
    border-color: #dfe3e9;
}

.aw-radio {
    flex: none;
    margin-top: 0.25rem;
}

.aw-option-body {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
    flex: 1;
}

.aw-option-name {
    font-weight: 600;
    color: #212d40;
    overflow-wrap: anywhere;
}

.is-disabled .aw-option-name {
    color: #6c757d;
}

.aw-option-facts,
.aw-option-where {
    color: #6c757d;
    font-size: 0.8rem;
}

.aw-option-where i {
    margin-right: 0.3rem;
    color: #9aa1a7;
}

.aw-added {
    flex: none;
    align-self: center;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    background: #eceff3;
    color: #5a6270;
    font-size: 0.72rem;
    font-weight: 700;
    white-space: nowrap;
}

.aw-displays {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
    gap: 0.5rem;
}

.aw-display-icon {
    flex: none;
    margin-top: 0.2rem;
    color: #5a6270;
    font-size: 1rem;
}

.is-chosen .aw-display-icon {
    color: var(--primary, #007bff);
}

.aw-hint {
    margin: 0.4rem 0 0;
    color: #6c757d;
    font-size: 0.78rem;
}
</style>
