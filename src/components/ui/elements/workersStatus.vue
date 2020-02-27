<template>
    <div v-if="workerCount > 0">
        <div :id="`badge-workers-${server_id}`" class="badge-list">
            <b-badge v-b-tooltip.hover.html="getTitle('cache', workerCache)" class="rounded-left flat-right" :variant="workerCache.variant">{{ workerCache.jobCount }}</b-badge>
            <b-badge v-b-tooltip.hover.html="getTitle('default', workerDefault)" class="rounded-0 border-right" :variant="workerDefault.variant">{{ workerDefault.jobCount }}</b-badge>
            <b-badge v-b-tooltip.hover.html="getTitle('prio', workerPrio)" class="rounded-0" :variant="workerPrio.variant">{{ workerPrio.jobCount }}</b-badge>
            <b-badge v-b-tooltip.hover.html="getTitle('update', workerUpdate)" class="rounded-0" :variant="workerUpdate.variant">{{ workerUpdate.jobCount }}</b-badge>
            <b-badge v-b-tooltip.hover.html="getTitle('mail', workerMail)" class="rounded-right flat-left" :variant="workerMail.variant">{{ workerMail.jobCount }}</b-badge>
        </div>
    </div>
</template>

<script>
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
        workerCount() {
            return Object.keys(this.workers).length
        },
        workerCache() {
            return {
                jobCount: this.workers.cache.jobCount,
                variant: this.getVariantFromAlive(this.workers.cache),
                ...this.getAliveNumbers(this.workers.cache)
            }
        },
        workerDefault() {
            return {
                jobCount: this.workers.default.jobCount,
                variant: this.getVariantFromAlive(this.workers.default),
                ...this.getAliveNumbers(this.workers.default)
            }
        },
        workerPrio() {
            return {
                jobCount: this.workers.prio.jobCount,
                variant: this.getVariantFromAlive(this.workers.prio),
                ...this.getAliveNumbers(this.workers.prio)
            }
        },
        workerUpdate() {
            return {
                jobCount: this.workers.update.jobCount,
                variant: this.getVariantFromAlive(this.workers.update),
                ...this.getAliveNumbers(this.workers.update)
            }
        },
        workerMail() {
            return {
                jobCount: this.workers.email.jobCount,
                variant: this.getVariantFromAlive(this.workers.email),
                ...this.getAliveNumbers(this.workers.email)
            }
        }
    },
    data: function() {
        return {}
    },
    methods: {
        getVariantFromAlive(workerType) {
            const deadCount = this.getAliveNumbers(workerType).dead
            return deadCount == 0 ? 
                "success" :
                (deadCount == workerType.workers.length ? "danger" : "warning")
        },
        getAliveNumbers(workerType) {
            let deadCount = 0
            for (const worker of workerType.workers){
                if (!worker.ok) {
                    deadCount++
                }
            }
            return {dead: deadCount, alive: workerType.workers.length-deadCount, total: workerType.workers.length}
        },
        getTitle(workerName, workerType) {
            return {
                title: `Worker <strong>${workerName}</strong>:<div class="text-left">${workerType.jobCount} in queue</br>${workerType.alive}/${workerType.total} alive</div>`
            }
        }
    }
}
</script>

<style scoped>
    .badge-list {
        width: fit-content;
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