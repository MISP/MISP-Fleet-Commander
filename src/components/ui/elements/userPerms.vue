<template>
    <span>
        <template v-if="permCount > 0 && !summaryEmpty">
            <b-badge
                :id="`badge-perms-${context}-${row_id}`"
                :variant="summary.state"
            >{{ summary.text }}</b-badge>

            <b-popover
                custom-class="mw-25"
                :target="`badge-perms-${context}-${row_id}`"
                :variant="summary.state"
                triggers="hover" placement="auto">
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
        context: {
            type: String,
            required: true
        },
        row_id: {
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
            }
            return remote_user
        },
        permCount() {
            return this.perms === "" ? 0 : Object.keys(this.perms).length
        },
        summaryEmpty() {
            return Object.keys(this.summary).length == 0
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