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
                        <table class="table table-sm table-borderless table-striped ">
                            <tbody>
                                <tr>
                                    <td>Events</td>
                                    <th>1733</th>
                                </tr>
                                <tr>
                                    <td scope="row">Attributes</td>
                                    <th>285138</th>
                                </tr>
                                <tr>
                                    <td scope="row">Correlations</td>
                                    <th>28823</th>
                                </tr>
                                <tr>
                                    <td scope="row">Proposals active</td>
                                    <th>17</th>
                                </tr>
                                <tr>
                                    <td scope="row">Users</td>
                                    <th>124</th>
                                </tr>
                                <tr>
                                    <td scope="row">Organisations</td>
                                    <th>33</th>
                                </tr>
                            </tbody>
                        </table>
                        <div class="mx-auto w-50">
                            <!-- https://www.essycode.com/posts/create-sparkline-charts-d3/ -->
                            <svg width="160" height="30"><g><rect class="bar" x="0" y="18.374827518811834" width="3" height="11.625172481188166" fill="MediumSeaGreen"></rect><rect class="bar" x="4" y="11.102444397260975" width="3" height="18.897555602739025" fill="MediumSeaGreen"></rect><rect class="bar" x="8" y="9.273667006950639" width="3" height="20.72633299304936" fill="MediumSeaGreen"></rect><rect class="bar" x="12" y="13.789029580453693" width="3" height="16.210970419546307" fill="MediumSeaGreen"></rect><rect class="bar" x="16" y="26.742308156683976" width="3" height="3.2576918433160245" fill="MediumSeaGreen"></rect><rect class="bar" x="20" y="17.10487825580107" width="3" height="12.895121744198931" fill="MediumSeaGreen"></rect><rect class="bar" x="24" y="10.017543588691574" width="3" height="19.982456411308426" fill="MediumSeaGreen"></rect><rect class="bar" x="28" y="19.253607552518247" width="3" height="10.746392447481753" fill="MediumSeaGreen"></rect><rect class="bar" x="32" y="4.4612246944116265" width="3" height="25.538775305588373" fill="MediumSeaGreen"></rect><rect class="bar" x="36" y="26.36544411893403" width="3" height="3.634555881065971" fill="MediumSeaGreen"></rect><rect class="bar" x="40" y="11.837125511827594" width="3" height="18.162874488172406" fill="MediumSeaGreen"></rect><rect class="bar" x="44" y="1.1297305373061874" width="3" height="28.870269462693813" fill="MediumSeaGreen"></rect><rect class="bar" x="48" y="24.920179509775874" width="3" height="5.079820490224126" fill="MediumSeaGreen"></rect><rect class="bar" x="52" y="25.63147676850483" width="3" height="4.368523231495171" fill="MediumSeaGreen"></rect><rect class="bar" x="56" y="23.48145701314059" width="3" height="6.5185429868594085" fill="MediumSeaGreen"></rect><rect class="bar" x="60" y="1.6881927404231725" width="3" height="28.311807259576828" fill="MediumSeaGreen"></rect><rect class="bar" x="64" y="26.149638657920068" width="3" height="3.850361342079932" fill="MediumSeaGreen"></rect><rect class="bar" x="68" y="26.864977984092263" width="3" height="3.1350220159077367" fill="MediumSeaGreen"></rect><rect class="bar" x="72" y="2.6099277108765833" width="3" height="27.390072289123417" fill="MediumSeaGreen"></rect><rect class="bar" x="76" y="22.635849993187936" width="3" height="7.364150006812064" fill="MediumSeaGreen"></rect><rect class="bar" x="80" y="13.959768458859905" width="3" height="16.040231541140095" fill="MediumSeaGreen"></rect><rect class="bar" x="84" y="8.622163944150337" width="3" height="21.377836055849663" fill="MediumSeaGreen"></rect><rect class="bar" x="88" y="0.5283399428695041" width="3" height="29.471660057130496" fill="MediumSeaGreen"></rect><rect class="bar" x="92" y="28.490276204088023" width="3" height="1.5097237959119774" fill="MediumSeaGreen"></rect><rect class="bar" x="96" y="15.112369169715897" width="3" height="14.887630830284103" fill="MediumSeaGreen"></rect><rect class="bar" x="100" y="28.118181030331744" width="3" height="1.881818969668256" fill="MediumSeaGreen"></rect><rect class="bar" x="104" y="3.5903336372873262" width="3" height="26.409666362712674" fill="MediumSeaGreen"></rect><rect class="bar" x="108" y="4.298631087856755" width="3" height="25.701368912143245" fill="MediumSeaGreen"></rect><rect class="bar" x="112" y="6.131845216718805" width="3" height="23.868154783281195" fill="MediumSeaGreen"></rect><rect class="bar" x="116" y="28.13477834375368" width="3" height="1.8652216562463195" fill="MediumSeaGreen"></rect><rect class="bar" x="120" y="27.003678698198254" width="3" height="2.9963213018017463" fill="MediumSeaGreen"></rect><rect class="bar" x="124" y="5.022775359495785" width="3" height="24.977224640504215" fill="MediumSeaGreen"></rect><rect class="bar" x="128" y="16.406899803161803" width="3" height="13.593100196838197" fill="MediumSeaGreen"></rect><rect class="bar" x="132" y="17.815868714589385" width="3" height="12.184131285410615" fill="MediumSeaGreen"></rect><rect class="bar" x="136" y="25.063316385594195" width="3" height="4.936683614405805" fill="MediumSeaGreen"></rect><rect class="bar" x="140" y="6.444338279202718" width="3" height="23.555661720797282" fill="MediumSeaGreen"></rect><rect class="bar" x="144" y="17.645580584077223" width="3" height="12.354419415922777" fill="MediumSeaGreen"></rect><rect class="bar" x="148" y="13.961431256060127" width="3" height="16.038568743939873" fill="MediumSeaGreen"></rect><rect class="bar" x="152" y="25.98917207958115" width="3" height="4.010827920418851" fill="MediumSeaGreen"></rect><rect class="bar" x="156" y="4.823317800957465" width="3" height="25.176682199042535" fill="MediumSeaGreen"></rect></g></svg>
                        </div>
                        <span class="font-italic text-muted footer-comment">
                            CIRCL MISPPriv is a MISP server for the private sector, including more than 1500 organisations and 2500 users worldwide.
                        </span>
                    </div>
                </div>
            </div>
    </div>
</template>

<script>
import loaderPlaceholder from "@/components/ui/elements/loaderPlaceholder.vue"
import userPerms from "@/views/servers/elements/userPerms.vue"
import timeSinceRefresh from "@/components/ui/elements/timeSinceRefresh.vue"
import proxyStatus from "@/views/servers/elements/proxyStatus.vue"
import workersStatus from "@/views/servers/elements/workersStatus.vue"
import submodulesStatus from "@/views/servers/elements/submodulesStatus.vue"
import zeroMQStatus from "@/views/servers/elements/zeroMQStatus.vue"
import connectionsSummary from "@/views/servers/elements/connectionsSummary.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"

export default {
    name: "Node",
    components: {
        timeSinceRefresh
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