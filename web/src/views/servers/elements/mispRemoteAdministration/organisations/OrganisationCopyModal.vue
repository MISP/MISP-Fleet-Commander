<template>
    <b-modal
        id="modal-organisation-copy"
        size="lg"
        scrollable
        :title="org ? `Create ${org.name} on other servers` : 'Create on other servers'"
        @show="reset"
        @hidden="onHidden"
    >
        <div v-if="org" class="org-copy">
            <JobRunPanel
                v-if="job"
                :job="job"
                :servers="chosenServers"
                @navigate="$bvModal.hide('modal-organisation-copy')"
                @retried="followJob"
            ></JobRunPanel>

            <template v-else>
                <p class="copy-intro">
                    Created with the same UUID <code>{{ org.uuid }}</code>, name, type, sector, nationality, description and contacts.
                    Each server is checked again first: one that already has it is left as it is.
                </p>

                <div class="target-head">
                    <h6 class="section-title">Servers of {{ fleetName }}</h6>
                    <button v-if="selectable.length > 1" type="button" class="btn btn-link select-all" @click="toggleAll">
                        {{ allSelected ? "Select none" : "Select all" }}
                    </button>
                </div>
                <ul class="target-list">
                    <li v-for="target in targets" :key="target.id" :class="['target', { disabled: !target.selectable }]">
                        <b-form-checkbox
                            v-model="selected"
                            :value="target.id"
                            :disabled="!target.selectable"
                            class="target-check"
                        >
                            <span class="target-name">{{ target.name }}</span>
                        </b-form-checkbox>
                        <span :class="['target-state', `state-${target.state}`]">{{ target.note }}</span>
                    </li>
                </ul>

                <b-form-group label="Create it as" class="kind-group" :description="local ? 'Local: it can have users on those servers.' : 'External: the usual choice for an organisation whose users are on another server.'">
                    <div class="kind-choice" role="radiogroup" aria-label="Create it as">
                        <button type="button" role="radio" :aria-checked="!local ? 'true' : 'false'" :class="['kind-option', { active: !local }]" @click="local = false">
                            <i class="fas fa-globe" aria-hidden="true"></i> External
                        </button>
                        <button type="button" role="radio" :aria-checked="local ? 'true' : 'false'" :class="['kind-option', { active: local }]" @click="local = true">
                            <i class="fas fa-home" aria-hidden="true"></i> Local
                        </button>
                    </div>
                </b-form-group>
            </template>
        </div>

        <template #modal-footer="{ cancel }">
            <template v-if="job">
                <b-button variant="secondary" @click="cancel()">Close</b-button>
            </template>
            <template v-else>
                <b-button variant="secondary" @click="cancel()">Cancel</b-button>
                <b-button variant="primary" :disabled="starting || selected.length === 0" @click="start">
                    <b-spinner v-if="starting" small class="mr-1"></b-spinner>Create on {{ selected.length }} server{{ selected.length === 1 ? "" : "s" }}
                </b-button>
            </template>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/organisations"
import JobRunPanel from "@/components/jobs/JobRunPanel.vue"
import { isFinalJob } from "@/helpers/jobs"

const NOTES = {
    missing: "Missing",
    unknown: "Could not be listed: will be checked",
    same: "Already there",
    renamed: "Already there, under another name",
    other_uuid: "Has one of that name with another UUID: fix by hand",
}

export default {
    name: "OrganisationCopyModal",
    components: {
        JobRunPanel,
    },
    props: {
        server: {
            type: Object,
            required: true,
        },
        // The table row of the organisation: {org, standing, …}
        row: {
            type: Object,
            default: null,
        },
        comparison: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            selected: [],
            local: false,
            starting: false,
            jobId: null,
            chosenServers: [],
        }
    },
    computed: {
        org() {
            return this.row ? this.row.org : null
        },
        fleetName() {
            return (this.server.fleet && this.server.fleet.name) || "the fleet"
        },
        targets() {
            if (!this.row || !this.row.standing) {
                return []
            }
            return this.row.standing.rows
                .map(entry => ({
                    id: entry.id,
                    name: entry.name,
                    state: entry.state,
                    note: NOTES[entry.state],
                    selectable: entry.state === "missing" || entry.state === "unknown",
                }))
                .sort((a, b) => Number(b.selectable) - Number(a.selectable) || a.name.localeCompare(b.name))
        },
        selectable() {
            return this.targets.filter(target => target.selectable)
        },
        allSelected() {
            return this.selectable.length > 0 && this.selected.length === this.selectable.length
        },
        job() {
            return this.jobId === null ? null : this.$store.getters["jobs/job"](this.jobId)
        },
    },
    watch: {
        job(job, previous) {
            if (isFinalJob(job) && !isFinalJob(previous)) {
                this.$emit("done", job)
            }
        },
    },
    methods: {
        reset() {
            this.jobId = null
            this.local = false
            this.starting = false
            // Where it is missing; servers that could not be listed are left to the user
            this.selected = this.targets.filter(target => target.state === "missing").map(target => target.id)
        },
        onHidden() {
            this.jobId = null
        },
        toggleAll() {
            this.selected = this.allSelected ? [] : this.selectable.map(target => target.id)
        },
        start() {
            this.starting = true
            const ids = this.selected.slice()
            const servers = this.$store.state.servers.servers
            this.chosenServers = this.targets
                .filter(target => ids.includes(target.id))
                .map(target => servers[target.id] || { id: target.id, name: target.name })
            api.copy(this.server.id, { uuid: this.org.uuid, server_ids: ids, local: this.local })
                .then((data) => {
                    this.$store.commit("jobs/track", data.job_id)
                    this.$store.commit("jobs/setJob", data.job)
                    this.jobId = data.job_id
                    this.$store.dispatch("jobs/fetch", data.job_id).catch(() => {})
                })
                .catch((error) => {
                    this.$bvToast.toast(error.message, { title: "Could not start creating it", variant: "danger" })
                })
                .finally(() => { this.starting = false })
        },
        followJob(job) {
            this.jobId = job.id
        },
    },
}
</script>

<style scoped>
.org-copy {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.copy-intro {
    margin-bottom: 1rem;
    color: #3c4650;
}

.copy-intro code {
    color: #3c4650;
    overflow-wrap: anywhere;
}

.target-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
}

.section-title {
    margin: 0 0 0.35rem;
    font-size: 0.95em;
    font-weight: 700;
}

.select-all {
    padding: 0;
    font-size: 0.85rem;
}

.target-list {
    margin: 0 0 1rem;
    padding: 0;
    border: 1px solid var(--health-rule);
    border-radius: 0.25rem;
    list-style: none;
}

.target {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.2rem 1rem;
    padding: 0.4rem 0.75rem;
}

.target + .target {
    border-top: 1px solid var(--health-rule);
}

.target.disabled {
    background: #fafbfc;
}

.target-name {
    font-weight: 600;
}

.disabled .target-name {
    color: #6c757d;
    font-weight: 500;
}

.target-state {
    font-size: 0.82rem;
    color: #6c757d;
}

.state-missing {
    color: var(--var-color-lapislazuli);
    font-weight: 600;
}

.state-other_uuid {
    color: var(--health-warning-ink);
}

.kind-group {
    margin-bottom: 0;
}

.kind-group ::v-deep legend {
    font-weight: 600;
    color: #3c4650;
}

.kind-choice {
    display: inline-flex;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    overflow: hidden;
}

.kind-option {
    padding: 0.3rem 0.85rem;
    border: 0;
    background: #fff;
    color: #495057;
}

.kind-option + .kind-option {
    border-left: 1px solid #ced4da;
}

.kind-option.active {
    background: var(--var-color-lapislazuli);
    color: #fff;
}
</style>
