<template>
    <component
        v-bind:is="requestedComponent ? requestedComponent : defaultComponent"
        :status="status"
        :data="data"
        :errors="errors"
    ></component>
</template>

<script>
import generic from "@/components/ui/pluginElements/generic.vue";
import boolean from "@/components/ui/pluginElements/boolean.vue";
import textVariant from "@/components/ui/pluginElements/textVariant.vue";

export default {
    name: "pluginIndexColumn",
    components: {
        generic,
        boolean,
        textVariant,
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
        plugin_response: {
            required: true
        }
    },
    data: function() {
        return {
            defaultComponent: 'generic',
        }
    },
    computed: {
        data() {
            return this.plugin_response.data !== undefined ? this.plugin_response.data : {}
        },
        requestedComponent() {
            return this.plugin_response.component || null
        },
        status() {
            return this.plugin_response.status
        },
        errors() {
            return this.plugin_response.errors || null
        },
    },
    methods: {
    }
}
</script>

<style scoped>

</style>