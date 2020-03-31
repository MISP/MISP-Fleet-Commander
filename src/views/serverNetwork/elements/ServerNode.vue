<template>
    <div class="nodeServer">
        <div class="node-container shadow-sm d-inline-block">
            <b-card no-body>
                <template v-slot:header>
                    <div class="top-header d-flex flex-wrap">
                        <div class="d-flex flex-wrap align-items-center mr-1">
                            <span class="server-name mr-1">
                                <i class="fa fa-server"></i>
                                <span class="text-monospace">
                                    {{ server.name }}
                                </span>
                            </span>
                            <span class="server-url">
                                <a href="#" class="text-muted font-weight-light text-wrap">
                                    {{ server.url }}
                                    <sup class="fa fa-external-link-alt text-muted"></sup>
                                </a>
                            </span>
                        </div>
                        <div class="ml-auto">
                            <span class="badge badge-success">Online</span>
                        </div>
                    </div>
                </template>
                <b-tabs card nav-class="card-header-tabs" @input="tabChanged">
                    <b-tab title="Diagnostic" active>
                        <ServerNodeDiagnostic :diagnostic="{}"></ServerNodeDiagnostic>
                    </b-tab>
                    <b-tab title="Usage">
                        <ServerNodeUsage :usage="{}"></ServerNodeUsage>
                    </b-tab>
                    <b-tab title="User">
                        <ServerNodeUsage :usage="{}"></ServerNodeUsage>
                        <ServerNodeUser :user="{}"></ServerNodeUser>
                    </b-tab>
                    <b-tab title="Sync">
                        <ServerNodeSync :sync="{}"></ServerNodeSync>
                    </b-tab>
                    <b-tab title="Content">
                        <ServerNodeContent :content="{}"></ServerNodeContent>
                    </b-tab>
                    <template v-slot:tabs-end>
                        <a class="nav-link disabled ml-auto border-0" href="#" style="pointer-events: auto;">
                            <timeSinceRefresh :timestamp="server.server_info.timestamp" :clockNoMargin="true"></timeSinceRefresh>
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
/* eslint-disable vue/no-unused-components */
import * as d3 from "d3"
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import ServerNodeDiagnostic from "@/views/serverNetwork/elements/nodeElements/ServerNodeDiagnostic.vue"
import ServerNodeUsage from "@/views/serverNetwork/elements/nodeElements/ServerNodeUsage.vue"
import ServerNodeUser from "@/views/serverNetwork/elements/nodeElements/ServerNodeUser.vue"
import ServerNodeSync from "@/views/serverNetwork/elements/nodeElements/ServerNodeSync.vue"
import ServerNodeContent from "@/views/serverNetwork/elements/nodeElements/ServerNodeContent.vue"

export default {
    name: "ServerNode",
    components: {
        timeSinceRefresh,
        ServerNodeDiagnostic,
        ServerNodeUsage,
        ServerNodeUser,
        ServerNodeSync,
        ServerNodeContent
    },
    data: function () {
        return {
        }
    },
    computed: {
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
        }
    },
    props: {
        server: {
            type: Object,
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
    }
}
</script>

<style scoped>
.nodeServer {
    width: unset;
}

.nodeServer > .node-container > div.card > div.card-body {
    flex-grow: 1;
}

.node-container > .card {
    font-size: 75%;
}

.node-container > .card > .card-header {
    border-bottom: 0;
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