<template>
    <div class="nodeServer">
        <div class="node-container shadow-sm d-inline-block">
                <div class="card">
                    <div class="card-header">
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
                        <ul class="nav nav-tabs card-header-tabs">
                            <li class="nav-item">
                                <a class="nav-link" href="#">Diagnostic</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link active" href="#">Usage</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="#">User</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="#">Sync</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link disabled" href="#" tabindex="-1" aria-disabled="true"
                                title="Only available when Sync test is enabled">Content</a>
                            </li>
                            <li class="nav-item ml-auto">
                                <a class="nav-link disabled pb-0" href="#" style="pointer-events: auto;">
                                    <timeSinceRefresh :timestamp="server.server_info.timestamp"></timeSinceRefresh>
                                    <button type="button btn-sm" class="btn btn-link sync-btn p-0">
                                        <i class="fas fa-sync"></i>
                                    </button>
                                </a>
                            </li>
                        </ul>
                    </div>
                    <div class="card-body">
                        <ServerNodeUsage :usage="{}"></ServerNodeUsage>
                        <ServerNodeDiagnostic :diagnostic="{}"></ServerNodeDiagnostic>
                        <ServerNodeUser :user="{}"></ServerNodeUser>
                        <ServerNodeSync :sync="{}"></ServerNodeSync>
                        <ServerNodeContent :content="{}"></ServerNodeContent>
                    </div>
                </div>
            </div>
    </div>
</template>

<script>
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import ServerNodeDiagnostic from "@/views/serverNetwork/elements/nodeElements/ServerNodeDiagnostic.vue"
import ServerNodeUsage from "@/views/serverNetwork/elements/nodeElements/ServerNodeUsage.vue"
import ServerNodeUser from "@/views/serverNetwork/elements/nodeElements/ServerNodeUser.vue"
import ServerNodeSync from "@/views/serverNetwork/elements/nodeElements/ServerNodeSync.vue"
import ServerNodeContent from "@/views/serverNetwork/elements/nodeElements/ServerNodeContent.vue"

export default {
    name: "Node",
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
    },
    props: {
        server: {
            type: Object,
            required: true
        }
    }
}
</script>

<style scoped>
.nodeServer {
    height: 100%
}

.nodeServer > .node-container, .nodeServer > .node-container > div.card {
    height: 100%
}

.nodeServer > .node-container > div.card > div.card-body {
    flex-grow: 1;
}

.node-container > .card {
    font-size: 75%;
}

.node-container > .card > .card-header {
    padding: 0 0.1rem;
    padding-bottom: 0.3rem;
}

.node-container > .card > .card-header > .top-header {
    font-size: 133%;
    margin: 0.1rem 0.3rem;
    cursor: grab;
}

.node-container > .card > .card-header > .card-header-tabs {
    margin-left: 0;
    margin-right: 0;
    margin-bottom: -0.3rem;
}

.node-container > .card > .card-header > .card-header-tabs > .nav-item {
    margin-left: 0.1rem;
}

.node-container > .card > .card-header > .card-header-tabs > .nav-item > .nav-link {
    border-radius: 0.15rem;
    padding: 0.15rem 0.3rem;
}

.node-container > .card > .card-body {
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