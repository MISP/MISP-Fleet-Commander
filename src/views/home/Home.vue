<template>
<Layout name="LayoutDefault">
    <h3>
        <iconForScope scope="home"></iconForScope>
        Home
    </h3>
</Layout>
</template>

<script>
import Layout from "@/components/layout/Layout.vue"
import iconForScope from "@/components/ui/elements/iconForScope.vue"

export default {
    name: "TheHome",
    components: {
        Layout,
        iconForScope
    },
    data: function () {
        return {
        }
    }
}
</script>

<style scoped>
</style>
