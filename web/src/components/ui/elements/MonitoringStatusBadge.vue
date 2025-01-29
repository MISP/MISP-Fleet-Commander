<template>
    <b-badge variant="x" class="d-flex align-items-center" style="border: 1px solid #bbb; background-color: #fff;">
        <span style="color: #d22f27; width: 28px;" title="This fleet is marked to be monitored">
            <img src="@/assets/monitored.svg" alt="Fleet monitored icon" width="26" height="26">
        </span>
        <span class="ml-1 user-select-none"> {{ show_for_selected_fleet && isMonitoringEnabled ? 'Monitored' : 'Monitoring system is'}} <b-badge v-if="!show_for_selected_fleet || !isMonitoringEnabled" :variant="isMonitoringEnabled ? 'success' : 'danger'" style="font-size: 100%;">{{ isMonitoringEnabled ? 'enabled' : 'disabled' }}</b-badge></span>
        <template v-if="show_for_selected_fleet && isMonitoringEnabled">
            <timeSinceRefresh
                class="ml-1"
                :timestamp="monitoredTimestamp"
            ></timeSinceRefresh>
        </template>
    </b-badge>
</template>

<script>
import { mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: 'MonitoringStatusBadge',
    components: {
        timeSinceRefresh
    },
    props: {
        show_for_selected_fleet: {
            required: false,
            type: Boolean,
            default: false,
        }
    },
    computed: {
        ...mapGetters({
            isMonitoringEnabled: "settings/isMonitoringEnabled",
            selectedFleet: "fleets/selectedFleet",
        }),
        monitoredTimestamp: function() {
            return this.selectedFleet.monitored_timestamp
        }
    }
}
</script>
