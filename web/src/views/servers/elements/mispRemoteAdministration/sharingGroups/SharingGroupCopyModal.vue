<template>
    <b-modal
        id="modal-sharing-group-copy"
        size="lg"
        scrollable
        :title="group ? `${group.name} on other servers` : 'On other servers'"
        @show="reset"
        @hidden="onHidden"
    >
        <div v-if="group" class="sg-copy">
            <JobRunPanel
                v-if="job"
                :job="job"
                :servers="chosenServers"
                @navigate="$bvModal.hide('modal-sharing-group-copy')"
                @retried="followJob"
            ></JobRunPanel>

            <template v-else>
                <ul class="copy-intro">
                    <li>
                        <strong>Where it is missing</strong>, it is created with the same UUID <code>{{ group.uuid }}</code>,
                        name, description, releasability, active and roaming flags, and its {{ group.members.length }}
                        member{{ group.members.length === 1 ? "" : "s" }} (organisations unknown there are created as external).
                    </li>
                    <li><strong>Where it already is</strong>, the members it lacks are added. Nothing is removed or renamed.</li>
                    <li v-if="remoteServers > 0">
                        Its {{ remoteServers }} server{{ remoteServers === 1 ? "" : "s" }} {{ remoteServers === 1 ? "is" : "are" }} not copied:
                        server lists name this server's own sync connections.
                    </li>
                </ul>
                <p class="copy-check">Each server is checked again when the job reaches it.</p>

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
                        <span :class="['target-state', `state-${target.tone}`]">{{ target.note }}</span>
                    </li>
                </ul>
            </template>
        </div>

        <template #modal-footer="{ cancel }">
            <template v-if="job">
                <b-button variant="secondary" @click="cancel()">Close</b-button>
            </template>
            <template v-else>
                <b-button variant="secondary" @click="cancel()">Cancel</b-button>
                <b-button variant="primary" :disabled="starting || selected.length === 0" @click="start">
                    <b-spinner v-if="starting" small class="mr-1"></b-spinner>Apply on {{ selected.length }} server{{ selected.length === 1 ? "" : "s" }}
                </b-button>
            </template>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/sharingGroups"
import JobRunPanel from "@/components/jobs/JobRunPanel.vue"
import { isFinalJob } from "@/helpers/jobs"
import { LOCAL_INSTANCE } from "@/helpers/sharingGroups"

function targetOf(entry) {
    if (entry.state === "missing") {
        return { note: "Missing: will be created", tone: "action", selectable: true, preselected: true }
    }
    if (entry.state === "differs" && entry.lacking > 0) {
        const count = entry.lacking
        return { note: `Lacks ${count} member${count === 1 ? "" : "s"}: ${count === 1 ? "it" : "they"} will be added`, tone: "action", selectable: true, preselected: true }
    }
    if (entry.state === "differs") {
        return { note: "Has every member (other differences left as they are)", tone: "muted", selectable: false }
    }
    if (entry.state === "unknown") {
        return { note: "Could not be listed: will be checked", tone: "muted", selectable: true, preselected: false }
    }
    if (entry.state === "other_uuid") {
        return { note: "Has one of that name with another UUID: fix by hand", tone: "warning", selectable: false }
    }
    return { note: "Already complete", tone: "muted", selectable: false }
}

export default {
    name: "SharingGroupCopyModal",
    components: {
        JobRunPanel,
    },
    props: {
        server: {
            type: Object,
            required: true,
        },
        // The table row of the group: {group, standing, …}
        row: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            selected: [],
            starting: false,
            jobId: null,
            chosenServers: [],
        }
    },
    computed: {
        group() {
            return this.row ? this.row.group : null
        },
        fleetName() {
            return (this.server.fleet && this.server.fleet.name) || "the fleet"
        },
        remoteServers() {
            return this.group ? this.group.servers.filter(item => item.server_id !== LOCAL_INSTANCE).length : 0
        },
        targets() {
            if (!this.row || !this.row.standing) {
                return []
            }
            return this.row.standing.rows
                .map(entry => ({ id: entry.id, name: entry.name, ...targetOf(entry) }))
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
            this.starting = false
            // Where something is to do; servers that could not be listed are left to the user
            this.selected = this.targets.filter(target => target.preselected).map(target => target.id)
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
            api.copy(this.server.id, { uuid: this.group.uuid, server_ids: ids })
                .then((data) => {
                    this.$store.commit("jobs/track", data.job_id)
                    this.$store.commit("jobs/setJob", data.job)
                    this.jobId = data.job_id
                    this.$store.dispatch("jobs/fetch", data.job_id).catch(() => {})
                })
                .catch((error) => {
                    this.$bvToast.toast(error.message, { title: "Could not start the job", variant: "danger" })
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
.sg-copy {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.copy-intro {
    margin: 0 0 0.4rem;
    padding-left: 1.1rem;
    color: #3c4650;
}

.copy-intro li + li {
    margin-top: 0.2rem;
}

.copy-intro code {
    color: #3c4650;
    overflow-wrap: anywhere;
}

.copy-check {
    margin-bottom: 1rem;
    color: #6c757d;
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
    margin: 0;
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

.state-action {
    color: var(--var-color-lapislazuli);
    font-weight: 600;
}

.state-warning {
    color: var(--health-warning-ink);
}
</style>
