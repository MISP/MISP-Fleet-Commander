<template>
    <div class="nodeServer">
        <div class="node-container d-inline-block">
            <b-card no-body>
                <template v-slot:header>
                    <div class="top-header d-flex flex-wrap">
                        <div class="d-flex flex-wrap align-items-center mr-1">
                            <span class="server-name mr-1">
                                <i class="fa fa-server"></i>
                                <span class="text-monospace">
                                    {{ getServer.name }}
                                </span>
                            </span>
                            <span class="server-url">
                                <a href="#" class="text-muted font-weight-light text-wrap">
                                    {{ getServer.url }}
                                    <sup class="fa fa-external-link-alt text-muted"></sup>
                                </a>
                            </span>
                        </div>
                        <div class="ml-auto">
                            <span :class="['badge', getServerStatus.error ? 'badge-danger' : 'badge-success']">{{ getServerStatus.data }}</span>
                        </div>
                    </div>
                </template>
                <b-tabs card nav-class="card-header-tabs" @input="tabChanged" v-model="tabIndex">
                    <b-tab title="Info" active>
                        <ServerNodeInfo :server="getServer"></ServerNodeInfo>
                    </b-tab>
                    <b-tab title="Usage">
                        <ServerNodeUsage :usage="getServerUsage" :server="getServer"></ServerNodeUsage>
                    </b-tab>
                    <b-tab title="Synchronization">
                        <ServerNodeSync :sync="{}"></ServerNodeSync>
                    </b-tab>
                    <b-tab title="Pinned content">
                        <ServerNodePinnedContent :server="getServer"></ServerNodePinnedContent>
                    </b-tab>
                    <template v-slot:tabs-end>
                        <a class="nav-link disabled ml-auto border-0" href="#" style="pointer-events: auto;">
                            <timeSinceRefresh :timestamp="lastRefreshTimestamp" :clockNoMargin="true"></timeSinceRefresh>
                            <button type="button btn-sm" class="btn btn-link sync-btn p-0">
                                <i class="fas fa-sync"></i>
                            </button>
                        </a>
                    </template>
                </b-tabs>
            </b-card>
        </div>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
/* eslint-disable vue/no-unused-components */
import * as d3 from "d3"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import ServerNodeInfo from "@/views/strategicView/elements/nodeElements/ServerNodeInfo.vue"
import ServerNodeUsage from "@/views/strategicView/elements/nodeElements/ServerNodeUsage.vue"
import ServerNodeSync from "@/views/strategicView/elements/nodeElements/ServerNodeSync.vue"
import ServerNodePinnedContent from "@/views/strategicView/elements/nodeElements/ServerNodePinnedContent.vue"

export default {
    name: "ServerNode",
    components: {
        timeSinceRefresh,
        ServerNodeInfo,
        ServerNodeUsage,
        ServerNodeSync,
        ServerNodePinnedContent,
        iconButton,
        loaderPlaceholder
    },
    data: function () {
        return {
            tabIndex: 0,
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            server_usage: state => state.servers.server_usage,
            remote_connections: state => state.servers.remote_connections,
            last_refresh: state => state.servers.last_refresh,
        }),
        getServer: function() {
            return this.servers[this.server_id] || null
        },
        getServerStatus: function() {
            return this.server_status[this.server_id] || {}
        },
        getServerUsage: function() {
            return this.server_usage[this.server_id] || {}
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id]
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        lastRefreshTimestamp: function() {
            return this.last_refresh[this.server_id] || null
        },
    },
    methods: {
        tabChanged() {
            this.$nextTick(() => {
                this.resizeParentForeignObject()
            })
        },
        resizeParentForeignObject() { // sync SVG's ForeignObject dimensions with those of this child node
            const tranformScale = d3.zoomTransform(this.d3SVGNode).k
            const tranformScaleInverse = 1 / tranformScale
            const divBoundingRect = this.$el.getBoundingClientRect()
            const parentSVG = this.$el.closest("foreignObject.nodeFO")
            parentSVG.setAttribute("width", `${divBoundingRect.width * tranformScaleInverse}px`)
            parentSVG.setAttribute("height", `${divBoundingRect.height * tranformScaleInverse}px`)
        },
        setTabIndex(index) {
            this.tabIndex = index
        }
    },
    props: {
        server_id: {
            type: Number,
            required: true
        },
        d3Node: {
            type: Object,
            required: true
        },
        d3SVGNode: {
            type: SVGSVGElement,
            required: true
        }
    },
    created() {
        const nodeFunctions = {
            setTabIndex: this.setTabIndex,
        }
        this.$emit('nodeFunctions', nodeFunctions);
    },
    mounted() {
        this.tabChanged()
    }
}
</script>

<style>
foreignObject.nodeFO {
    overflow: visible;
}
</style>

<style scoped>
.nodeServer {
    width: min-content;
}

.nodeServer > .node-container > div.card > div.card-body {
    flex-grow: 1;
}

.node-container > .card {
    font-size: 75%;
    box-shadow: rgba(0, 0, 0, 0.16) 0px 3px 6px, rgba(0, 0, 0, 0.23) 0px 3px 6px;
    
}

.node-container > .card > .card-header {
    border-bottom: 0;
    min-width: 350px;
}

.node-container > .card > .card-header, .node-container > .card > .tabs >>> .card-header {
    padding: 0 0.1rem;
    padding-bottom: 0.3rem;
}

.node-container > .card > .card-header > .top-header {
    font-size: 133%;
    margin: 0.1rem 0.3rem;
    cursor: grab;
}

.node-container > .card > .tabs >>> .card-header > .card-header-tabs {
    margin-left: 0;
    margin-right: 0;
    margin-bottom: -0.33rem;
}

.node-container > .card > .tabs >>> .card-header > .card-header-tabs > .nav-item {
    margin-left: 0.1rem;
}

.node-container > .card > .tabs >>> .card-header > .card-header-tabs .nav-link {
    border-radius: 0.15rem;
    padding: 0.15rem 0.3rem;
}

.node-container > .card > .tabs >>> .card-body {
    padding: 0.5rem 0;
}

.node-container > .card > .card-body > table {
    margin-bottom: 0.3rem;
}

.node-container > .card > .card-body > table tr {
    line-height: 0.6rem;
}

.node-container > .card > .card-body > table th {
}

.server-url {
    font-size: 80%;
}
.server-url::before {
    content: "\2012";
}

.server-url .fa {
    font-size: 55%;
}

.footer-comment {
    font-size: 80%;
}

.sync-btn {
    font-size: 80%;
}
</style>