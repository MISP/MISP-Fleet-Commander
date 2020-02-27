<template>
    <b-card no-body>
        <template v-if="server._loading">
            <div class="text-center text-danger my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong class="ml-2">Loading...</strong>
            </div>
        </template>
        <template v-else>
            <template v-if="details.error">
                <div class="mb-2 text-right">
                    <span class="mr-1 text-muted">
                        <i class="far fa-clock mr-1"></i>
                        <small class="align-middle">{{ details.data.query_result.timestamp | moment("from") }}</small>
                    </span>
                    <b-button 
                        size="sm" variant="primary"
                        @click="refreshDiagnostic()"
                    ><b-icon icon="arrow-clockwise"></b-icon></b-button>
                </div>
                <b-alert show variant="danger">
                    Error while accessing diagnostic:
                    <strong>{{ details.data }}</strong>
                </b-alert>
            </template>
            <template v-else>
                <b-card no-body>
                    <b-tabs card>
                        <b-tab title="Diagnostic" class="p-1" active no-body>
                            <b-card no-body>
                                <b-tabs pills card vertical>
                                    <b-tab
                                        v-for="(value, setting) in getDiagnostic"
                                        v-bind:key="setting"
                                        :title="setting"
                                    >
                                        <b-card-text><pre>{{ value }}</pre></b-card-text>
                                    </b-tab>
                                </b-tabs>
                            </b-card>
                        </b-tab>
                        <b-tab title="Server settings" class="p-1" no-body>
                                <pre>{{ getConfig }}</pre>
                        </b-tab>
                        <b-tab title="Usage" no-body>
                            <b-card no-body>
                                Usage
                            </b-card>
                        </b-tab>
                        <b-tab title="User" class="p-1" no-body>
                            <b-card no-body>
                                <pre>{{ details.data.query_result.serverUser }}</pre>
                            </b-card>
                        </b-tab>
                        <b-tab title="Connected MISP Servers" class="p-1" no-body>
                            <b-card no-body>
                                Synchronisation status
                            </b-card>
                        </b-tab>
                        <b-tab title="Content" class="p-1" no-body disabled>
                            <b-card no-body>
                                Content
                            </b-card>
                        </b-tab>

                        <template v-slot:tabs-end>
                            <b-nav-item href="#" class="ml-auto rightmost-action">
                                <timeSinceRefresh
                                    :timestamp="details.data.timestamp"
                                    type="ddd DD/MM/YYYY hh:mm"
                                ></timeSinceRefresh>
                                <b-button 
                                    size="sm" variant="primary"
                                    @click="refreshDiagnosticFull()"
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
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "RowDetails",
    components: {
        timeSinceRefresh,
    },
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
        getDiagnostic() {
            // eslint-disable-next-line no-unused-vars
            let {finalSettings, ...diagnostic} = this.details.data.query_result.serverSettings
            return diagnostic
        },
        getConfig() {
            return this.details.data.query_result.serverSettings.finalSettings
        }
    },
    methods: {
        refreshDiagnosticFull() {
            this.$emit("actionRefresh", "no_cache")
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

pre {
    white-space: pre-wrap;
    max-height: 800px;
}
</style>