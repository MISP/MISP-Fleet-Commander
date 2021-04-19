<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <div class="container">
            <div class="mt-1 mb-4">
                <h3>[Application name]</h3>
                <h5 class="text-muted">Manage your MISP community easily</h5>
            </div>
            <div class="row">
                <div class="col">
                    <ServerGroup class="mt-3"></ServerGroup>
                </div>
                <div class="col">
                    <NotificationHelpers class="mt-3"></NotificationHelpers>
                </div>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import ServerGroup from "@/views/serverGroups/index.vue"
import NotificationHelpers from "@/views/notificationHelpers/index.vue"

export default {
    name: "TheHome",
    components: {
        Layout,
        ServerGroup,
        NotificationHelpers
    },
    data: function () {
        return {
        }
    }
}
</script>

<style scoped>
</style>
