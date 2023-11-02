<template>
    <div class="nodeContainer">
        <div class="nodeServer nodeServerMicro p-1 pl-2 top-header">
            <div class="server-name text-monospace text-nowrap mb-0 p-0">
                <span :class="[`text-${getDiodeColor}`, 'status-icon-container']">
                    <b-icon icon="circle-fill"></b-icon>
                </span>
                <span :class="['diode-message text-monospace text-nowrap ml-1', `text-${getDiodeColor}`]" v-show="statusHasError">{{ getStatusMessage }}</span>
                <span class="ml-2 text-center text-monospace" style="flex-grow: 1;" v-show="!statusHasError">{{ getServer.name }}</span>
            </div>
            <div v-show="statusHasError" class="text-monospace">{{ getServer.name }}</div>
            <div class="server-url">
                <a href="#" class="text-muted font-weight-light text-nowrap">
                    {{ getServer.url }}
                    <sup class="fa fa-external-link-alt text-muted"></sup>
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
/* eslint-disable vue/no-unused-components */
import * as d3 from "d3"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"

export default {
    name: "UnmanagedServerNode",
    components: {
        timeSinceRefresh,
    },
    props: {
        d3Node: {
            type: Object,
            required: true
        },
        d3SVGNode: {
            type: SVGSVGElement,
            required: true
        },
        nodeData: {
            type: Object,
            required: true
        },
    },
    data: function () {
        return {
        }
    },
    computed: {
        ...mapState({
            connections: state => state.connections.all,
            server_status: state => state.servers.server_status,
            remote_connections: state => state.servers.remote_connections,
        }),
        getServer: function () {
            return this.nodeData
        },
        getServerStatus: function () {
            return this.getServer.status.status
        },
        getDiodeColor: function () {
            return this.getServerStatus.color
        },
        getStatusMessage: function () {
            return this.getServerStatus.message
        },
        statusHasError: function () {
            return this.getDiodeColor == 'danger'
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
    mounted: function () {
        this.$nextTick(() => {
            this.resizeParentForeignObject()
        })
    }
}
</script>

<style scoped>
.nodeContainer {
    background-color: white;
    border-radius: 1rem;
    width: fit-content;
}

.nodeServer.nodeServerMicro {
    max-width: 1000px;
    border: 1px dashed rgba(0, 0, 0, 0.3);
    background-color: rgba(0, 0, 0, 0.02);
    border-radius: 1rem;
}

.top-header {
    cursor: grab;
}

.nodeServerMicro h2 {
    color: #444;
    display: flex;
    align-items: center;
}

.nodeServerMicro {
    font-size: small;
    line-height: 1.25em;
}

.nodeServerMicro .server-name .status-icon-container {
    font-size: smaller;
}

.diode-message {
    font-size: 0.75em;
    /* line-height: 0.75em; */
}
</style>

<style>
line.link.unmanaged_server {
    stroke-dasharray: 5
}
</style>