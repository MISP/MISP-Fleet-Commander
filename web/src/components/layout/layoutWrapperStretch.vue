<template>
    <Layout name="LayoutStretch">
        <router-view></router-view>
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
