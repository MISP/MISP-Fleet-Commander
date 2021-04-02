<template>
    <span>
        <slot v-if="status"/>
        <cellLoading v-else :height="height" :width="width" :maxWidth="maxWidth" :style="style"></cellLoading>
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
        },
        height: {
            type: String,
            default: "0.5rem"
        },
        width: {
            type: String,
            default: ""
        },
        maxWidth: {
            type: String,
            default: ""
        },
        placeholderWidth: {
            type: String,
            default: ""
        },
    },
    computed: {
        status() {
            return this.loading
        },
        style() {
            return {
                width: this.placeholderWidth
            }
        }
    }
}
</script>

<style scoped>
</style>