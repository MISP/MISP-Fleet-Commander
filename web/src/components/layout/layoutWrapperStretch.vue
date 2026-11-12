<template>
    <Layout name="LayoutStretch">
        <!-- Another fleet is another network: the Strategic View is built again rather than patched -->
        <router-view :key="$route.params.fleet_id"></router-view>
    </Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"

export default {
    name: "layoutWrapperStretch",
    components: {
        Layout
    }
}
</script>
