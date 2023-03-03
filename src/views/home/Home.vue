<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <div class="container">
            <div class="mt-1 mb-4">
                <img src="@/assets/logo.png" class="logo mb-3" alt="MISP Fleet Commander logo">
                <h5 class="text-muted fw-light">Manage your MISP communities easily</h5>
            </div>
            <div class="row">
                <div class="col">
                    <ServerGroup class="mt-3"></ServerGroup>
                </div>
                <div class="col">
                    <PluginIndex class="mt-3"></PluginIndex>
                </div>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import ServerGroup from "@/views/serverGroups/index.vue"
import PluginIndex from "@/views/plugins/PluginIndex.vue"

export default {
    name: "TheHome",
    components: {
        Layout,
        ServerGroup,
        PluginIndex
    },
    data: function () {
        return {
        }
    }
}
</script>

<style scoped>
    .logo {
        height: auto;
        max-width: 400px;
    }
</style>
