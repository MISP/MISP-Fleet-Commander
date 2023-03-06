<template>
    <component
        v-if="!errors"
        v-bind:is="requestedComponent ? requestedComponent : defaultComponent"
        :status="status"
        :data="data"
        :errors="errors"
    ></component>
    <span v-else>
        <i
            :id="`plugin-popover-${plugin_name}-${server_id}`"
            class="fa fa-exclamation-triangle text-danger"
        ></i>
        <b-popover
            href="#" tabindex="0"
            triggers="hover"
            boundary="viewport"
            :target="`plugin-popover-${plugin_name}-${server_id}`"
            variant="danger"
            title="Error while fetching plugin data"
        >
            {{ printableErrors }}
        </b-popover>
    </span>
</template>

<script>
import generic from "@/components/ui/pluginElements/generic.vue";
import boolean from "@/components/ui/pluginElements/boolean.vue";
import textVariant from "@/components/ui/pluginElements/textVariant.vue";

export default {
    name: "pluginValueRenderer",
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
        plugin_name: {
            type: String,
            required: true
        },
        plugin_response: {
            required: true
        },
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
        printableErrors() {
            return this.errors.length == 1 ? this.errors[0] : JSON.stringify(this.errors)
        },
    },
    methods: {
    }
}
</script>

<style scoped>

</style>