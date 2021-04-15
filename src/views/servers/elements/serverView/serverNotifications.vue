<template>
    <div>
        <b-table-simple class="mb-0" responsive
        sticky-header
        >
            <b-thead head-variant="light">
                <b-tr>
                    <b-th>Date</b-th>
                    <b-th>Severity</b-th>
                    <b-th>Title</b-th>
                    <b-th>Action</b-th>
                </b-tr>
            </b-thead>
            <b-tbody>
                <b-tr v-if="notifications.length == 0">
                    <b-td colspan="4" class="text-center">There are no notifications for this server</b-td>
                </b-tr>
                <b-tr v-for="(notification, index) in notifications" :key="index">
                    <b-td>{{ notification.date }}</b-td>
                    <b-td>{{ notification.status }}</b-td>
                    <b-td>{{ notification.title }}</b-td>
                    <b-td>
                        <b-button class="ml-1" size="sm" variant="light" title="Accept">
                            <i class="fas fa-check"></i>
                        </b-button>
                        <b-button class="ml-1" size="sm" variant="light">
                            <i class="fas fa-cogs"></i>
                        </b-button>
                        <b-button class="ml-1" size="sm" variant="outline-danger" title="Delete notification">
                            <i class="fas fa-trash"></i>
                        </b-button>
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"

export default {
    name: "ServerNotifications",
    components: {
    },
    props: {
        server: {
            required: true,
            type: Object
        }
    },
    computed: {
    },
    data: function () {
        return {
            notifications: [
                // {
                //     "id": "1",
                //     "uuid": "2b2b2c71-7ba3-4d99-9d8b-0646aa56e00e",
                //     "title": "User registration for rateuser@admin.test.",
                //     "type": "registration",
                //     "ip": "10.0.2.2",
                //     "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
                //     "user_agent_sha256": "b31d6571dc54050285bc94819f48de44e81c9b1db2de8b6d4ce1c2c039b0691a",
                //     "comment": "Hello!",
                //     "deleted": false,
                //     "timestamp": "1615453743",
                //     "store_as_file": false,
                //     "data": {
                //         "email": "rateuser@admin.test",
                //         "org_name": "cases",
                //         "org_uuid": "9e7e987e-b45a-4860-9ab4-b53034fe3a20",
                //         "message": "Hello!",
                //         "custom_perms": "1",
                //         "perm_sync": "1",
                //         "perm_publish": "1",
                //         "perm_admin": "1"
                //     }
                // },
                // {
                //     "id": "1",
                //     "uuid": "2b2b2c71-7ba3-4d99-9d8b-0646aa56e00e",
                //     "title": "User registration for rateuser@admin.test.",
                //     "type": "registration",
                //     "ip": "10.0.2.2",
                //     "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
                //     "user_agent_sha256": "b31d6571dc54050285bc94819f48de44e81c9b1db2de8b6d4ce1c2c039b0691a",
                //     "comment": "Hello!",
                //     "deleted": false,
                //     "timestamp": "1615453743",
                //     "store_as_file": false,
                //     "data": {
                //         "email": "rateuser@admin.test",
                //         "org_name": "cases",
                //         "org_uuid": "9e7e987e-b45a-4860-9ab4-b53034fe3a20",
                //         "message": "Hello!",
                //         "custom_perms": "1",
                //         "perm_sync": "1",
                //         "perm_publish": "1",
                //         "perm_admin": "1"
                //     }
                // },
            ]
        }
    }
}
</script>

<style scoped>
thead tr th {
    background-color: teal;
    border-top: 0;
}
</style>
