<template>
    <b-badge variant="x" class="d-flex align-items-center" style="border: 1px solid #bbb; background-color: #fff;">
        <span class="user-select-none d-flex align-items-center">
            <template v-if="isMonitoringEnabled">
                <template v-if="!show_for_selected_fleet">
                    <img src="@/assets/monitored.svg" alt="Fleet monitored icon" width="26" height="26" class="mr-1">
                    Fleet monitoring system is
                    <b-badge
                        class="ml-1"
                        variant="success"
                        style="font-size: 100%;"
                    >enabled</b-badge>
                </template>
                <template v-else>
                    <template v-if="show_for_selected_fleet && isFleetMonitoringEnabledForThisFleet">
                        <img src="@/assets/monitored.svg" alt="Fleet monitored icon" width="26" height="26" class="mr-1">
                        Fleet monitored
                        <timeSinceRefresh
                            class="ml-1"
                            :timestamp="monitoredTimestamp"
                        ></timeSinceRefresh>
                    </template>
                    <template v-else>
                        <img src="@/assets/monitored-slash.svg" alt="Fleet not monitored icon" width="26" height="26" style="filter: grayscale(1); color: #d22f27;" class="mr-1">
                        Fleet not monitored
                    </template>
                </template>
            </template>
            <template v-else>
                <img src="@/assets/monitored-slash.svg" alt="Fleet not monitored icon" width="26" height="26" style="filter: grayscale(1); color: #d22f27;">
                Fleet monitoring system is
                <b-badge
                    class="ml-1"
                    variant="danger"
                    style="font-size: 100%;"
                >disabled</b-badge>
            </template>
        </span>
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
        },
        isFleetMonitoringEnabledForThisFleet: function() {
            return this.selectedFleet.is_monitored
        },
    }
}
</script>
