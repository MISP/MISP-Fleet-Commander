<template>
    <b-card>
        <template v-if="details.data.loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="details.error">
                <b-alert show variant="danger">
                    Error while accessing diagnostic:
                    <strong>{{ details.data }}</strong>
                </b-alert>
            </template>
            <template v-else>
                <b-card no-body>
                    <b-tabs card>
                        <b-tab title="Server settings" active>
                            <b-card no-body>
                                <b-tabs pills card vertical>
                                    <b-tab
                                        v-for="(value, setting) in details.data"
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

                        <template v-slot:tabs-end>
                            <b-nav-item href="#" class="ml-auto rightmost-action">
                                <span class="mr-1 text-muted">
                                    <i class="far fa-clock mr-1"></i>
                                    <small class="align-middle">{{ details.data.timestamp | moment("from") }}</small>
                                </span>
                                <b-button 
                                    size="sm" variant="primary"
                                    @click="refreshDiagnostic()"
                                ><b-icon icon="arrow-clockwise"></b-icon></b-button>
                            </b-nav-item>
                        </template>
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
        },
        server: {
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
        refreshDiagnostic() {
            this.$emit("actionRefresh", "done")
        }
    }
}
</script>

<style scoped>

ul.nav-tabs > li.nav-item.rightmost-action > a {
    padding-bottom: 0;
    margin-top: -10px;
    margin-right: -15px;
}

ul.nav-tabs > li.nav-item.rightmost-action > a:hover {
    border: 1px solid #ffffff00;
}
ul.nav-tabs > li.nav-item.rightmost-action > a:focus {
    border: 1px solid #ffffff00;
}
</style>