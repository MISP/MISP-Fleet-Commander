<template>
    <div class="d-flex flex-column">
        <div class="d-flex align-items-baseline">
            <span class="flex-grow-1 mr-2">Status</span>
            <b-badge :variant="connection.status.color">{{ connection.status.message }}</b-badge>
        </div>
        <div v-if="connection.localVersion !== ''" class="d-flex align-items-baseline">
            <span class="flex-grow-1 mr-2">Local version</span>
            <span>{{ connection.localVersion }}</span>
        </div>
        <div v-if="connection.remoteVersion !== ''" class="d-flex align-items-baseline">
            <span class="flex-grow-1 mr-2">Remote version</span>
            <span>{{ connection.remoteVersion }}</span>
        </div>
        <div v-if="connection.compatibility.message !== ''" class="d-flex align-items-baseline">
            <span class="flex-grow-1 mr-2">Compatibility</span>
            <b-badge :variant="connection.compatibility.color">{{ connection.compatibility.message }}</b-badge>
        </div>
        <div v-if="connection.post.variant !== ''" class="d-flex align-items-baseline">
            <span class="flex-grow-1 mr-2">POST test</span>
            <b-badge :variant="connection.post.color">
                {{ connection.post.result }}
                <i :class="['fas', connection.post.success ? 'fa-check' : 'fa-times']"></i>
            </b-badge>
        </div>
        <template v-if="user.email != ''">
            <hr class="w-100">
            <div>
                <div v-if="user.email != ''" class="d-flex align-items-baseline">
                    <span class="flex-grow-1 mr-2">User</span>
                    <span>{{ user.email }}</span>
                </div>
                <div v-if="user.role_name != ''" class="d-flex align-items-baseline">
                    <span class="flex-grow-1 mr-2">Role</span>
                    <b-badge :variant="user.role_color">{{ user.role_name }}</b-badge>
                </div>
                <div class="d-flex align-items-baseline">
                    <span class="flex-grow-1 mr-2">Sync status</span>
                    <b-badge :variant="user.sync_flag == 1 ? 'success' : 'danger'">
                        <i :class="['fas', user.sync_flag == 1 ? 'fa-check' : 'fa-times']"></i>
                    </b-badge>
                </div>
            </div>
        </template>
    </div>
</template>

<script>
export default {
    name: "connectionState",
    props: {
        connection: {
            type: Object,
            required: true
        },
        user: {
            type: Object,
            required: true
        },
    },
    data: function() {
        return {}
    },
    computed: {
    }
}
</script>

<style scoped>

</style>