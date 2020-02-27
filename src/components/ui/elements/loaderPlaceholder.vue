<template>
    <span>
        <slot v-if="status"/>
        <cellLoading v-else></cellLoading>
    </span>
</template>

<script>
import cellLoading from "@/components/ui/elements/cellLoading.vue"

export default {
    name: "loaderPlaceholder",
    components: {
        cellLoading
    },
    props: {
        loading: {
            required: true
        }
    },
    computed: {
        status() {
            return this.loading
        }
    }
}
</script>

<style scoped>
</style>