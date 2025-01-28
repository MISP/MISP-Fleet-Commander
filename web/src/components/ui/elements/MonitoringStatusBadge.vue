<template>
    <b-badge variant="x" class="mb-2" style="border: 1px solid #bbb; background-color: #fff;">
        <span style="color: #d22f27;" title="This fleet is marked to be monitored">
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"><path fill="currentColor" d="M11 18h2v3h-2zm5 3v2H8v-2zm4-3H4a3.003 3.003 0 0 1-3-3V4a3.003 3.003 0 0 1 3-3h16a3.003 3.003 0 0 1 3 3v11a3.003 3.003 0 0 1-3 3M4 3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1Z"/><path fill="currentColor" d="m16 15l-1.914-6.38L13 13l-1.309-3h-.331L10 14L8.843 9.933L8.309 11H5v-1h2.691L9 7l1.068 3.713L10.64 9h1.669l.487.973L14 4l2 8l.64-2H19v1h-1.64z"/></svg>
        </span>
        <span class="ml-1 user-select-none">Monitoring is <b-badge :variant="isMonitoringEnabled ? 'success' : 'danger'" style="font-size: 100%;">{{ isMonitoringEnabled ? 'enabled' : 'disabled' }}</b-badge></span>
    </b-badge>
</template>

<script>
import { mapGetters } from "vuex"

export default {
    name: 'MonitoringStatusBadge',
    props: {
    },
    computed: {
        ...mapGetters({
            isMonitoringEnabled: "settings/isMonitoringEnabled",
        }),
    }
}
</script>
