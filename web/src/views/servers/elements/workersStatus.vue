<template>
    <div v-if="serverHasSettings">
        <div v-if="workerCount > 0 && backgroundJobEnabled">
            <div :id="`badge-workers-${server_id}`" class="badge-list d-flex flex-nowrap">
                <b-badge v-b-tooltip.hover.html="getTitle('cache', workerCache)" class="rounded-left flat-right" :variant="workerCache.variant">{{ workerCache.jobCount }}</b-badge>
                <b-badge v-b-tooltip.hover.html="getTitle('default', workerDefault)" class="rounded-0 border-right" :variant="workerDefault.variant">{{ workerDefault.jobCount }}</b-badge>
                <b-badge v-b-tooltip.hover.html="getTitle('prio', workerPrio)" class="rounded-0" :variant="workerPrio.variant">{{ workerPrio.jobCount }}</b-badge>
                <b-badge v-b-tooltip.hover.html="getTitle('update', workerUpdate)" class="rounded-0" :variant="workerUpdate.variant">{{ workerUpdate.jobCount }}</b-badge>
                <b-badge v-b-tooltip.hover.html="getTitle('mail', workerMail)" class="rounded-right flat-left" :variant="workerMail.variant">{{ workerMail.jobCount }}</b-badge>
            </div>
        </div>
        <b-badge
            v-else-if="backgroundJobEnabled && workerCount == 0"
            variant="danger"
            rounded
        >
            Background job enabled but no worker running
        </b-badge>
        <b-badge
            v-else
            variant="danger"
            rounded
        >
            Background job disabled
        </b-badge>
    </div>
</template>

<script>
import { mapState } from "vuex"

export default {
    name: "workersStatus",
    props: {
        workers: {
        },
        server_id: {
            type: Number,
            required: true
        }
    },
    computed: {
        ...mapState({
            final_settings: state => state.servers.final_settings,
        }),
        backgroundJobEnabled() {
            return this.final_settings[this.server_id]['MISP.background_jobs']
        },
        serverHasSettings() {
            return this.final_settings[this.server_id] !== undefined && Object.keys(this.final_settings[this.server_id]).length > 0
        },
        workerCount() {
            return Object.keys(this.workers).length
        },
        workerCache() {
            return {
                jobCount: this.workers?.cache?.jobCount,
                variant: this.getVariantFromAlive(this.workers?.cache),
                ...this.getAliveNumbers(this.workers?.cache)
            }
        },
        workerDefault() {
            return {
                jobCount: this.workers?.default?.jobCount,
                variant: this.getVariantFromAliveAndJobCount(this.workers?.default),
                ...this.getAliveNumbers(this.workers?.default)
            }
        },
        workerPrio() {
            return {
                jobCount: this.workers.prio?.jobCount,
                variant: this.getVariantFromAliveAndJobCount(this.workers?.prio),
                ...this.getAliveNumbers(this.workers?.prio)
            }
        },
        workerUpdate() {
            return {
                jobCount: this.workers?.update?.jobCount,
                variant: this.getVariantFromAlive(this.workers?.update),
                ...this.getAliveNumbers(this.workers?.update)
            }
        },
        workerMail() {
            return {
                jobCount: this.workers?.email?.jobCount,
                variant: this.getVariantFromAlive(this.workers?.email),
                ...this.getAliveNumbers(this.workers?.email)
            }
        }
    },
    data: function() {
        return {}
    },
    methods: {
        getVariantFromAliveAndJobCount(workerType) {
            const aliveNumber = this.getAliveNumbers(workerType)
            if (aliveNumber.total == 0) {
                return "danger"
            }
            const deadCount = aliveNumber.dead
            return deadCount == 0 ? 
                (workerType.jobCount <= 10 ? "" : (workerType <= 100 ? "warning" : "danger")) :
                (deadCount == workerType.workers.length ? "danger" : "warning")
        },
        getVariantFromAlive(workerType) {
            const aliveNumber = this.getAliveNumbers(workerType)
            if (aliveNumber.total == 0) {
                return "danger"
            }
            const deadCount = aliveNumber.dead
            return deadCount == 0 ? 
                "" :
                (deadCount == workerType.workers.length ? "danger" : "warning")
        },
        getAliveNumbers(workerType) {
            let deadCount = 0
            if (workerType.workers === undefined) {
                workerType.workers = {}
            }
            Object.values(workerType.workers).forEach(worker => {
                if (!worker.ok) {
                    deadCount++
                }
            });
            return {dead: deadCount, alive: Object.values(workerType.workers).length-deadCount, total: Object.values(workerType.workers).length}
        },
        getTitle(workerName, workerType) {
            let title = ''
            if (workerType.total == 0) {
                title = `Worker <strong>${workerName}</strong>:<div class="text-left">${workerType.jobCount} in queue</br>No worker running</div>`
            } else [
                title = `Worker <strong>${workerName}</strong>:<div class="text-left">${workerType.jobCount} in queue</br>${workerType.alive}/${workerType.total} alive</div>`
            ]
            return {
                title: title
            }
        }
    }
}
</script>

<style scoped>
    .badge-list {
        width: fit-content;
    }

    .badge-list > .badge {
        cursor: default;
    }

    .badge-list > .badge:not(:last-child) {
        border-right: 1px solid #dee2e6
    }

    .flat-right {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }

    .flat-left {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0
    }
</style>
