<template>
<Layout name="LayoutDefault">
    <div class="page-container">
        <h3><iconForScope scope="home"></iconForScope> Home</h3>

        <div class="container">
            <div class="row">
                <div class="col">
                    <ServerGroup class="mt-3"></ServerGroup>
                </div>
                <div class="col">
                </div>
            </div>
        </div>
    </div>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"
import ServerGroup from "@/views/serverGroups/index.vue"

export default {
    name: "TheHome",
    components: {
        Layout,
        iconForScope,
        ServerGroup
    },
    data: function () {
        return {
        }
    }
}
</script>

<style scoped>
</style>
