<template>
    <div class="d-flex flex-column align-items-center">
        <div
            v-if="hasUsage"
            class="usage-container text-nowrap badge-list"
        >
            <b-badge
                :title="`${usage.event_count.toLocaleString()} Events`"
                class="rounded-left flat-right"
            >
                <i class="fas fa-envelope mr-1"></i>
                <span>{{ genCount(usage.event_count) }}</span>
            </b-badge>
            <b-badge
                :title="`${usage.attributes_per_event.toLocaleString()} Attributes per Events`"
                class="rounded-right flat-left"
            >
                <i class="fas fa-chart-pie mr-1"></i>
                <span>{{ genCount(usage.attributes_per_event) }}</span>
            </b-badge>
        </div>
        <div
            v-if="hasUsage"
            class="usage-container text-nowrap badge-list mt-1"
        >
            <b-badge
                :title="`${usage.attribute_count.toLocaleString()} Attributes`"
                class="rounded-left flat-right"
            >
                <i class="fas fa-cube mr-1"></i>
                <span>{{ genCount(usage.attribute_count) }}</span>
            </b-badge>
            <b-badge
                :title="`${usage.object_count.toLocaleString()} Objects`"
                class="rounded-right flat-left"
            >
                <i class="fas fa-cubes mr-1"></i>
                <span>{{ genCount(usage.object_count) }}</span>
            </b-badge>
        </div>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "dataUsageShort",
    props: {
        server_id: {
            required: true,
            type: Number,
        },
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            server_usage: state => state.servers.server_usage,
        }),
        usage() {
            return this.server_usage[this.server_id]?.stats
        },
        hasUsage() {
            return this.usage !== undefined
        },
    },
    methods: {
        genCount(amount) {
            if (amount == 0) {
                return '0'
            }
            const prefixes = ['', 'k', 'M', 'B', 'T']; // Add more as needed
            const magnitude = Math.floor(Math.log10(Math.abs(amount)) / 3);
            const abbreviated = (amount / Math.pow(1000, magnitude)).toFixed(0);
            return `${abbreviated}${prefixes[magnitude]}`;
        },
    }
}
</script>

<style scoped>
    .usage-container {
        display: flex;
        align-items: center;
        font-family: monospace;
        flex-wrap: nowrap;
    }

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
