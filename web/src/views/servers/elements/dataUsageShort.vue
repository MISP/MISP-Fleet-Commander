<template>
    <span
        v-if="hasUsage"
        class="usage-container"
    >
        <div :title="`${usage.attribute_count} Attribute`">
            <i class="fas fa-cube"></i>
            <span>{{ genCount(usage.attribute_count) }}</span>
        </div>
        <div :title="`${usage.event_count} Event`">
            <i class="fas fa-envelope"></i>
            <span>{{ genCount(usage.event_count) }}</span>
        </div>
        <div :title="`${usage.attributes_per_event} per Events`">
            <i class="fas fa-chart-pie"></i>
            <span>{{ genCount(usage.attributes_per_event) }}</span>
        </div>
    </span>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "zeroMQStatus",
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
            const prefixes = ['', 'k', 'M', 'B', 'T']; // Add more as needed
            const magnitude = Math.floor(Math.log10(Math.abs(amount)) / 3);
            const abbreviated = (amount / Math.pow(1000, magnitude)).toFixed(0);
            return `${abbreviated}${prefixes[magnitude]}`;
        }
    }
}
</script>

<style scoped>
.usage-container {
    display: flex;
    font-family: monospace;
}

.usage-container > * {
    font-size: 0.75em;
}

.usage-container > *:not(:first-child) {
    margin-left: .25em;
}

.usage-container > div > span {
    margin-left: .25em;
    font-size: 1.1em;
}
</style>