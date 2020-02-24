<template>
    <b-card>
        <template v-if="details.loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="details.error">
                <b-alert show variant="danger">
                    Error while accessing diagnostic:
                    <strong>{{ details.message }}</strong>
                </b-alert>
            </template>
            <template v-else>
                <b-card no-body>
                    <b-tabs card>
                        <b-tab title="Server settings" active>
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
                        </b-tab>
                        <b-tab title="Usage">
                            <b-card no-body>
                                Usage
                            </b-card>
                        </b-tab>
                        <b-tab title="User">
                            <b-card no-body>
                                User
                            </b-card>
                        </b-tab>
                        <b-tab title="Connected MISP Servers">
                            <b-card no-body>
                                Synchronisation status
                            </b-card>
                        </b-tab>
                        <b-tab title="Content" disabled>
                            <b-card no-body>
                                Content
                            </b-card>
                        </b-tab>
                    </b-tabs>
                </b-card>
            </template>
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