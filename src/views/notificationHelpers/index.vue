<template>
    <div class="">
        <div class="">
            <h4>Notification Helpers</h4>
        </div>
<!-- 
        <b-list-group>
            <b-list-group-item
                v-for="(helper, index) in getHelpers"
                v-bind:key="index"
                href="#" class="p-2 flex-column align-items-start"
            >
                <div class="d-flex w-100 justify-content-between">
                    <h5 class="mb-1">{{ helper.name }}</h5>
                    <b-badge :variant="helper.enabled ? 'success' : 'danger'">
                        {{ helper.enabled ? 'enabled' : 'disabled'}}
                    </b-badge>
                </div>
                <p class="mb-1">{{ helper.description }}</p>
            </b-list-group-item>
        </b-list-group> -->

        <b-card no-body>
            <b-table-simple class="mb-0">
                <b-thead>
                    <b-tr>
                        <b-th>Name</b-th>
                        <b-th>Description</b-th>
                        <b-th>Features</b-th>
                        <b-th>Enabled</b-th>
                    </b-tr>
                </b-thead>
                <b-tbody>
                    <b-tr v-if="getHelpers.length == 0">
                        <b-td colspan="4" class="text-center">There are no notification helpers available.</b-td>
                    </b-tr>
                    <b-tr v-for="(helper, index) in getHelpers" :key="index">
                        <b-td class="text-nowrap"><h6>{{ helper.name }}</h6></b-td>
                        <b-td>{{ helper.description }}</b-td>
                        <b-td class="text-nowrap">
                            <b-badge
                            v-for="(feature, index) in availableFeatures"
                            :key="index"
                            :variant="helper.features.includes(feature) ? 'success' : 'danger'"
                            :class="getRoundedClass(index)"
                            >
                                {{ feature }}
                            </b-badge>
                        </b-td>
                        <b-td>
                            <i :class="['fa', helper.enabled ? 'fa-check' : 'fa-times', helper.enabled ? 'text-success' : 'text-danger']"></i>
                        </b-td>
                    </b-tr>
                </b-tbody>
            </b-table-simple>
        </b-card>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "NotificationHelpers",
    components: {
    },
    data: function () {
        return {
            availableFeatures: ["accept", "process", "delete"],
            getHelpers: [
                {
                    name: "Up To Date",
                    description: "Check that the server is up-to-date",
                    enabled: true,
                    features: ["accept", "delete"]
                },
                {
                    name: "User Registration",
                    description: "List open user registration requests",
                    enabled: false,
                    features: ["process", "delete"]
                }
            ]
        }
    },
    computed: {
        ...mapState({
            // getHelpers: state => state.notificationHelpers.all
        }),
        helpersEmpty() {
            return this.getHelpers == 0
        }
    },
    methods: {
        // refreshNotifications() {
        //     this.refreshInProgress = true
        //     return new Promise((resolve, reject) => {
        //         this.$store.dispatch("notifications/getNotifications", 9)
        //             .then(() => {
        //                 resolve()
        //             })
        //             .catch(error => {
        //                 this.$bvToast.toast(error, {
        //                     title: "Could not fetch server group index",
        //                     variant: "danger",
        //                 })
        //                 reject()
        //             })
        //             .finally(() => {
        //                 this.refreshInProgress = false
        //             })
        //     })
        // },
        getRoundedClass(index) {
            if (this.availableFeatures.length == 1) {
                return ""
            } else if (index == 0) {
                return "rounded-left flat-right"
            } else if (index == this.availableFeatures.length-1) {
                return "rounded-right flat-left"
            } else {
                return "rounded-0"
            }
        },
    },
    mounted() {
        // this.refreshNotifications()
    }
}
</script>

<style scoped>
thead tr th {
    border-top: 0;
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
