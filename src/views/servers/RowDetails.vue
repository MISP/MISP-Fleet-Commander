<template>
    <b-card>
        <template v-if="!details.error">
            <b-card no-body>
                <b-tabs pills card vertical>
                <b-tab
                    v-for="(value, setting) in details.message"
                    v-bind:key="setting"
                    :title="setting"
                >
                    <b-card-text><pre>{{ value }}</pre></b-card-text>
                </b-tab>
                </b-tabs>
            </b-card>
        </template>
        <template v-else>
            <b-alert show variant="danger">
                Error while accessing diagnostic:
                <strong>{{ details.message }}</strong>
            </b-alert>
        </template>
    </b-card>
</template>

<script>
export default {
    name: "RowDetails",
    props: {
        details: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
        }
    },
    computed: {

    },
    methods: {
        
    }
}
</script>

<style scoped>

</style>