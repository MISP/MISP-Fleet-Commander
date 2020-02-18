<template>
    <Layout name="LayoutDefault">
        <router-view></router-view>
    </Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"

export default {
    name: "LayoutWrapper",
    components: {
        Layout
    }
}
</script>
