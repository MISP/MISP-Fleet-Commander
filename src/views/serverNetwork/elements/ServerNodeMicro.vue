<template>
    <div class="nodeContainer">
        <div class="nodeServer nodeServerMicro p-2 top-header">
            <h1 class="text-monospace text-nowrap mb-0 p-2">
                <span :class="[getServerStatus.error ? 'text-danger' : 'text-success']">
                    <b-icon icon="circle-fill"></b-icon>
                </span>
                <span class="ml-2">{{ getServer.name }}</span>
            </h1>
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
    name: "ServerNodeMicro",
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
}

.nodeServer.nodeServerMicro {
    max-width: 1000px;
    border: 3px solid rgba(0, 0, 0, 0.3);
    background-color: rgba(0, 0, 0, 0.03);
    border-radius: 1rem;
}

.top-header {
    cursor: grab;
}

.nodeServerMicro h1 {
    font-size: 4rem;
}
</style>