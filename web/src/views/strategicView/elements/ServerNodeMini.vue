<template>
    <div class="nodeContainer">
        <div class="nodeServer nodeServerMini p-2">
            <h2 class="text-monospace top-header">
                {{ getServer.name }}
            </h2>
            <h5 class="server-url">
                <a href="#" class="text-muted font-weight-light text-wrap">
                    {{ getServer.url }}
                    <sup class="fa fa-external-link-alt text-muted"></sup>
                </a>
            </h5>
            <div class="d-flex justify-content-between align-items-center">
                <span :class="['badge', 'big-badge', getServerStatus.error ? 'badge-danger' : 'badge-success']">
                    {{ getServerStatus.data }}
                </span>
                <span class="ml-2 border-0" href="#" style="pointer-events: auto; font-size: 1.3rem;">
                    <timeSinceRefresh :timestamp="lastRefreshTimestamp" :clockNoMargin="true"></timeSinceRefresh>
                    <button type="button btn-sm" class="btn btn-link sync-btn p-0">
                        <i class="fas fa-sync"></i>
                    </button>
                </span>
            </div>
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

export default {
    name: "ServerNodeMini",
    components: {
        timeSinceRefresh,
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
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            server_usage: state => state.servers.server_usage,
            remote_connections: state => state.servers.remote_connections,
        }),
        getServer: function() {
            return this.servers[this.server_id] || null
        },
        getServerStatus: function() {
            return this.server_status[this.server_id]
        },
        getServerUsage: function() {
            return this.server_usage[this.server_id]
        },
        getQueryInProgress: function() {
            return this.server_query_in_progress[this.server_id]
        },
        isOnline: function() {
            return !this.getServerStatus.error
        },
        lastRefreshTimestamp: function() {
            return this.getServer?.server_info?.timestamp || null
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
            const parentFO = this.$el.closest("foreignObject.nodeFO")
            parentFO.setAttribute("width", `${divBoundingRect.width * tranformScaleInverse}px`)
            parentFO.setAttribute("height", `${divBoundingRect.height * tranformScaleInverse}px`)
        }
    },
    updated: function () {
        this.$nextTick(() => {
            this.resizeParentForeignObject()
        })
    },
    mounted: function() {
        this.$nextTick(() => {
            this.resizeParentForeignObject()
        })
    }
}
</script>

<style scoped>
.nodeContainer {
    background-color: white;
    width: fit-content;
    max-width: 500px;
}

.nodeServer.nodeServerMini {
    border: 1px solid rgba(0, 0, 0, 0.3);
    background-color: rgba(0, 0, 0, 0.03);
    border-radius: 0.5rem;
}

.nodeServer.nodeServerMini div, .nodeServer.nodeServerMini h2, .nodeServer.nodeServerMini h5 {
    white-space: nowrap;
}

.top-header {
    cursor: grab;
}

.badge.big-badge {
    font-size: 1.7rem;
}

.server-url .fa {
    font-size: 55%;
}

.sync-btn {
    font-size: 80%;
}
</style>