<template>
    <b-badge variant="x" class="d-flex align-items-center" style="border: 1px solid #bbb; background-color: #fff;">
        <span class="fas fa-heartbeat" style="color: #d22f27; font-size: 24px; width: 28px;"></span>
        <span class="ml-1 user-select-none"> {{ show_for_selected_fleet && isFleetWatchingEnabled ? 'Fleet watched' : 'Fleet watching system is'}} <b-badge v-if="!show_for_selected_fleet || !isFleetWatchingEnabled" :variant="isFleetWatchingEnabled ? 'success' : 'danger'" style="font-size: 100%;">{{ isFleetWatchingEnabled ? 'enabled' : 'disabled' }}</b-badge></span>
        <template v-if="show_for_selected_fleet && isFleetWatchingEnabled">
            <timeSinceRefresh
                class="ml-1"
                :timestamp="watchedTimestamp"
            ></timeSinceRefresh>
        </template>
    </b-badge>
</template>

<script>
import { mapGetters } from "vuex"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: 'FleetWatchingStatusBadge',
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
            isFleetWatchingEnabled: "settings/isFleetWatchingEnabled",
            selectedFleet: "fleets/selectedFleet",
        }),
        watchedTimestamp: function() {
            return this.selectedFleet.watched_timestamp
        }
    }
}
</script>
