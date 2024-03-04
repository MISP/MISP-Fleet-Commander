<template>
    <b-modal
        id="modal-user-administration"
        size="lg"
        :title="`User administration for server ${server.name}`"
        :hide-footer="true"
    >
        <div class="mb-3">
            <b-button size="sm" variant="warning" class="mr-1">
                <i class="fas fa-lock"></i> Reset password
            </b-button>
            <b-button size="sm" variant="warning" class="mr-1">
                <i class="fas fa-key"></i> Reset authkey
            </b-button>
            <b-button size="sm" variant="primary" class="mr-1">
                <i class="fas fa-lock"></i> Set password
            </b-button>
            <b-button size="sm" variant="primary" class="mr-1" v-b-modal="'modal-administration-user-disable'">
                <i :class="`fas fa-toggle-${user.disabled ? 'on' : 'off'}`"></i> {{ user.User.disabled ? 'Enable' : 'Disable' }} User
            </b-button>
            <b-button size="sm" variant="primary" class="mr-1" :href="`${server.url}/admin/users/view/${user.User.id}`" target="_blank">
               <i class="fas fa-external-link-alt"></i> View
            </b-button>
            <b-button size="sm" variant="primary" class="mr-1" :href="`${server.url}/admin/users/edit/${user.User.id}`" target="_blank">
               <i class="fas fa-external-link-alt"></i> Edit
            </b-button>
        </div>

        <b-table-simple
            striped small
            class="mb-0"
            :bordered="false"
            :borderless="true"
            :outlined="false"
        >
            <b-tbody>
                <b-tr>
                    <b-th>Email</b-th>
                    <b-td>{{ user.User.email }}</b-td>
                </b-tr>
                <b-tr>
                    <b-th>Org. name</b-th>
                    <b-td>{{ user.Organisation.name }}</b-td>
                </b-tr>
                <b-tr>
                     <b-th>Role</b-th>
                     <b-td>
                         <userPerms
                            :perms="user.Role"
                            :row_id="3"
                            context="userview"
                        ></userPerms>
                     </b-td>
                </b-tr>
                <b-tr>
                     <b-th>Created</b-th>
                     <b-td>
                         <timeSinceRefresh
                            :timestamp=" user.User.date_created"
                            type="ddd DD/MM/YYYY HH:mm"
                            :noicon="true"
                            :noformat="true"
                            :small="false"
                        ></timeSinceRefresh>
                     </b-td>
                </b-tr>
                <b-tr>
                    <b-th>Last modified</b-th>
                    <b-td>
                        <timeSinceRefresh
                            :timestamp=" user.User.date_modified"
                            :noicon="true"
                            :noformat="true"
                            :small="false"
                        ></timeSinceRefresh>
                    </b-td>
                </b-tr>
                <b-tr>
                    <b-th>Last login</b-th>
                    <b-td>
                        <timeSinceRefresh
                            :timestamp=" user.User.last_login"
                            :small="false"
                        ></timeSinceRefresh>
                    </b-td>
                </b-tr>
                <b-tr>
                    <b-th>State</b-th>
                    <b-td>
                    <b-badge pill :variant="user.User.disabled ? 'danger' : 'success' ">
                        {{ user.User.disabled ? 'Disabled' : 'Enabled' }}
                    </b-badge>
                    </b-td>
                </b-tr>
            </b-tbody>
        </b-table-simple>

        <userDisable :user="user" :server="server" :isDisabled="user.User.disabled "></userDisable>
    </b-modal>
</template>

<script>
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"
import userDisable from "@/views/servers/elements/mispRemoteAdministration/userAdministrationActions/userDisable.vue"

export default {
    name: "UserAdministrationModal",
    components: {
        timeSinceRefresh,
        userPerms,
        userDisable,
    },
    props: {
        user: {
            required: true,
            type: Object
        },
        server: {
            required: true,
            type: Object
        },
    },
    data: function() {
        return {
            postInProgress: false,
            table: {
                fields: [
                    { key: "property", thStyle: { display: "none" } },
                    { key: "value", thStyle: { display: "none" } }
                ],
            }
        }
    },
    computed: {
    },
    methods: {
        doStuff() {
            console.log("doing stuff")
        }
    }
}
</script>