<template>
    <span>
        <template v-if="permCount > 0">
            <b-badge
                :id="`badge-perms-${server_id}`"
                :variant="summary.state"
            >{{ summary.text }}</b-badge>

            <b-popover
                custom-class="mw-25"
                :target="`badge-perms-${server_id}`"
                :variant="summary.state"
                triggers="hover" placement="righttop">
                <pre>{{ perms }}</pre>
            </b-popover>
        </template>
        <template>
        </template>
    </span>
</template>

<script>
export default {
    props: {
        perms: {},
        server_id: {
            type: Number,
            required: true
        }
    },
    computed: {
        summary() {
            let remote_user = {}
            if (this.perms.perm_site_admin) {
                remote_user.state = "success"
                remote_user.text = "site_admin"
            } else if (this.perms.perm_admin) {
                remote_user.state = "danger"
                remote_user.text = "admin"
            } else if (this.perms.perm_sync) {
                remote_user.state = "danger"
                remote_user.text = "sync"
            } else if (this.perms.perm_add) {
                remote_user.state = "danger"
                remote_user.text = "user"
            } else {
                remote_user.state = "dark"
                remote_user.text = "read only"
            }
            return remote_user
        },
        permCount() {
            return this.perms === "" ? 0 : Object.keys(this.perms).length
        }
    },
    data: function() {
        return {}
    },
    methods: {
    }
}
</script>

<style scoped>

</style>