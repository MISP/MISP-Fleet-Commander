<template>
    <b-badge variant="x" class="d-flex align-items-center" style="border: 1px solid #bbb; background-color: #fff;">
        <span class="user-select-none d-flex align-items-center">
            <template v-if="isFleetWatchingEnabled">
                <template v-if="!show_for_selected_fleet">
                    <span class="fas fa-heartbeat mr-1" style="color: #d22f27; font-size: 26px; width: 28px;"></span>
                    Fleet watching system is
                    <b-badge
                        class="ml-1"
                        variant="success"
                        style="font-size: 100%;"
                    >enabled</b-badge>
                </template>
                <template v-else>
                    <template v-if="show_for_selected_fleet && isFleetWatchingEnabledForThisFleet">
                        <span class="fas fa-heartbeat mr-1" style="color: #d22f27; font-size: 26px; width: 28px;"></span>
                        Fleet watched
                        <timeSinceRefresh
                            class="ml-1"
                            :timestamp="watchedTimestamp"
                        ></timeSinceRefresh>
                    </template>
                    <template v-else>
                        <span class="fa-stack fa-1x mr-1" style="filter: grayscale(1); font-size: 13px; color: #d22f27;">
                            <i class="fas fa-heartbeat fa-stack-2x"></i>
                            <i class="fas fa-slash fa-stack-2x"></i>
                        </span>
                        Fleet not watched
                    </template>
                </template>
            </template>
            <template v-else>
                <span class="fa-stack fa-1x" :style="`filter: grayscale(1); font-size: ${show_for_selected_fleet ? '13px' : '10px'}; color: #d22f27;`">
                    <i class="fas fa-heartbeat fa-stack-2x"></i>
                    <i class="fas fa-slash fa-stack-2x"></i>
                </span>
                Fleet watching system is
                <b-badge
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
        },
        isFleetWatchingEnabledForThisFleet: function() {
            return this.selectedFleet.is_watched
        },
    }
}
</script>
