<template>
<Layout name="LayoutStretch" class="position-relative h-100">
    <div>
        <div class="network-toolbar position-absolute d-flex flex-column px-3 py-1 bg-light shadow-sm">

            <b-button v-show="!showSidebar" variant="link" v-b-toggle.sidebar-network size="sm" class="ml-auto text-nowrap text-decoration-none">
                <i class="fa-solid fa-table-columns"></i> Show Sidebar
            </b-button>
        </div>
        <div ref="networkContainer" class="w-100 h-100 network-container">
            <svg ref="networkSVG"></svg>
        </div>

        <b-sidebar
            id="sidebar-network"
            v-model="showSidebar"
            body-class="px-2 py-1"
            shadow="lg"
            right
            width="400px"
            no-header
        >
            <b-button variant="link" v-b-toggle.sidebar-network size="xs" class="ml-auto position-absolute text-decoration-none px-2 py-1" style="box-shadow: 0 0.1rem 0.35rem rgba(0, 0, 0, 0.175); right: 0.25em;"
                @click="$event.target.blur()"
            >
                <i class="fa-solid fa-close"></i> Hide Sidebar
            </b-button>
            <div class="d-flex flex-column pt-4" style="row-gap: 1em; overflow-x: hidden; height: calc(100% - 1.5rem)">
                <transition name="slide-fade" mode="out-in">
                    <TheNodeInfoCard
                        v-if="selectedNodeID && Number.isInteger(selectedNodeID)"
                        :server_id="selectedNodeID"
                    ></TheNodeInfoCard>
        
                    <TheLinkInfoCard
                        v-if="selectedLinkID"
                        :link_id="selectedLinkID"
                        :link="selectedLink"
                        class=""
                    ></TheLinkInfoCard>
                </transition>
    
                <ThePinCard
                    :open.sync="pinCard.show"
                    @showPinnedContentOnNodes="showPinnedContentOnNodes"
                    class="mt-auto"
                    style="max-height: 50%;"
                ></ThePinCard>
            </div>
        </b-sidebar>

        <div
            class="network-action-bar position-absolute border py-1 px-2 bg-white shadow"
            :style="actionBarPosition"
        >
            <div class="action-group" role="group" aria-label="Refresh">
                <b-button
                    variant="primary"
                    class="ml-auto"
                    size="sm"
                    title="Quick refresh: check that each server answers"
                    aria-label="Quick refresh"
                    @click="fleetStatusRefresh()"
                >
                    <i class="fas fa-redo-alt"></i>
                </b-button>
                <b-button
                    :variant="linkTestInProgress ? 'dark' : 'primary'"
                    :disabled="linkTestInProgress || serverCount === 0"
                    size="sm"
                    class="text-nowrap"
                    title="Test every sync link of the fleet, without a full refresh"
                    @click="fleetLinkTest()"
                >
                    <span v-if="linkTestInProgress">
                        <i class="fas fa-circle-notch fa-spin"></i>
                        Testing links<span v-if="linkTestRunning > 1"> ({{ linkTestRunning }} servers)</span>
                    </span>
                    <span v-else>
                        <i class="fas fa-link"></i>
                        Test links
                    </span>
                </b-button>
                <b-button
                    :variant="getRefreshEnqueued ? 'dark' : 'primary'"
                    :disabled="getRefreshEnqueued"
                    size="sm"
                    title="Enqueue full refresh"
                    href="#"
                    @click="fleetRefresh()"
                >
                    <span v-if="getRefreshEnqueued">
                        <i class="fas fa-sync-alt fa-spin"></i>
                        Refresh in progress
                    </span>
                    <span v-else>
                        <i class="fas fa-sync-alt"></i>
                        Full refresh
                    </span>
                </b-button>
            </div>
            <div class="action-group action-group-view" role="group" aria-label="View">
                <NetworkNodeSearch :nodes="searchableNodes" @select="locateNode"></NetworkNodeSearch>
                <b-form-checkbox
                    v-model="problemsOnly"
                    switch
                    class="problems-switch text-nowrap"
                    title="Dim the healthy links and servers"
                >
                    Problems only
                    <span
                        v-if="problemsOnly"
                        :class="['problems-count', problemFocus.links.size > 0 ? 'has-problems' : '']"
                    >{{ problemFocus.links.size }}</span>
                </b-form-checkbox>
            </div>
            <div v-if="problemsOnly && graphReady && problemFocus.links.size === 0 && problemFocus.nodes.size === 0" class="problems-none" role="status">
                <i class="fas fa-check" aria-hidden="true"></i> No broken or degraded link, no server with issues
            </div>
        </div>

        <NetworkLegend class="network-legend-position position-absolute"></NetworkLegend>
    </div>
</Layout>
</template>

<script>
import Vue from "vue"
import store from "@/store/index"
import { mapState, mapGetters } from "vuex"
import { websocketMixin } from "@/helpers/websocketMixin"
import Layout from "@/components/layout/Layout.vue"
import ServerNodeGeneric from "@/views/strategicView/elements/ServerNodeGeneric.vue"
import ServerNode from "@/views/strategicView/elements/ServerNode.vue"
import ServerNodeMini from "@/views/strategicView/elements/ServerNodeMini.vue"
import ServerNodeMicro from "@/views/strategicView/elements/ServerNodeMicro.vue"
import TheNodeInfoCard from "@/views/strategicView/elements/NodeInfoCard.vue"
import TheLinkInfoCard from "@/views/strategicView/elements/LinkInfoCard.vue"
import ThePinCard from "@/views/strategicView/elements/PinCard.vue"
import NetworkLegend from "@/views/strategicView/elements/NetworkLegend.vue"
import NetworkNodeSearch from "@/views/strategicView/elements/NetworkNodeSearch.vue"
import d3Network from "@/helpers/d3Network.js"
import { LINK_LEVELS, isProblemLink, managedTarget } from "@/store/modules/connections"

const LINK_TEST_START_TIMEOUT = 15000
const PROBLEMS_ONLY_KEY = "mfc.strategicView.problemsOnly"

function endpointID(endpoint) {
    // d3's force layout replaces a link's source and target IDs by the node objects
    return endpoint !== null && typeof endpoint === "object" ? endpoint.id : endpoint
}

function readProblemsOnly() {
    try {
        return window.localStorage.getItem(PROBLEMS_ONLY_KEY) === "1"
    } catch (e) {
        return false
    }
}

export default {
    name: "TheStrategicView",
    mixins: [websocketMixin],
    components: {
        Layout,
        TheNodeInfoCard,
        TheLinkInfoCard,
        ThePinCard,
        NetworkLegend,
        NetworkNodeSearch,
    },
    data: function () {
        return {
            refreshInProgress: false,
            graphReady: false,
            network: null,
            problemsOnly: readProblemsOnly(),
            linkTest: {
                startedAt: null, // When the link test was asked for from here, until its outcome is reported
                waiting: false, // Asked for, not started by the workers yet
                timer: null,
            },
            showSidebar: false,
            nodeInfoCard: {
                show: false,
                position: {top: "4em", left: "unset", right: "1em"}
            },
            linkInfoCard: {
                show: false,
                position: {top: "4em", left: "unset", right: "1em"}
            },
            pinCard: {
                show: true,
                position: {top: "4em", left: "unset", right: "1em"}
            },
            selectedNode: {},
            selectedNodeID: null,
            selectedLink: {},
            selectedLinkID: null,
            d3data: {
                nodes: [],
                links: []
            },
            nodeFunctions: [],
            svg: null,
            svgSelection: null,
            zoom: null,
            updateData: null,
            scaleInfo: {x: 0, y: 0, k: 1},
            actionBarPosition: {top: "15px", right: "unset", left: "15px", bottom: "unset"},
            minimapRedrawCount: 0,
            allNodeInstances: [],
        }
    },
    computed: {
        ...mapState({
            selectedFleet: state => state.fleets.selected,
            remote_connections: state => state.servers.remote_connections,
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
            server_link_test: state => state.servers.server_link_test,
        }),
        ...mapGetters({
            serverCount: "servers/serverCount",
            getServerList: "servers/getServerList",
            serversByURL: "servers/serversByURL",
            serversByUUID: "servers/serversByUUID",
            getServerRefreshEnqueued: "servers/getServerRefreshEnqueued",
            getConnectionList: "connections/getConnectionList",
            serverWorst: "health/serverWorst",
        }),
        // What stays visible with "Problems only": broken and degraded links (unused ones aside), their two ends,
        // and the servers with critical or warning issues
        problemFocus() {
            const links = new Set()
            const nodes = new Set()
            this.d3data.links.forEach(link => {
                if (isProblemLink(link)) {
                    links.add(link.vid)
                    nodes.add(endpointID(link.source))
                    nodes.add(endpointID(link.target))
                }
            })
            this.getServerList.forEach(server => {
                const worst = this.serverWorst[server.id]
                if (worst === "critical" || worst === "warning") {
                    nodes.add(server.id)
                }
            })
            return { links, nodes }
        },
        // Worst level of the links reaching each node, for the search results
        incomingLinkLevel() {
            const levels = {}
            this.d3data.links.forEach(link => {
                if (link.health && link.health.disabled) {
                    return
                }
                const target = endpointID(link.target)
                const level = (link.health && link.health.level) || "unknown"
                if (levels[target] === undefined || LINK_LEVELS.indexOf(level) < LINK_LEVELS.indexOf(levels[target])) {
                    levels[target] = level
                }
            })
            return levels
        },
        searchableNodes() {
            return this.d3data.nodes.map(node => {
                if (node._managed_server) {
                    return {
                        id: node.id,
                        name: node.name || node.url || `#${node.id}`,
                        url: node.url || "",
                        managed: true,
                        level: this.serverWorst[node.id] || "ok",
                    }
                }
                return {
                    id: node.id,
                    name: node.name || node.url || String(node.id),
                    url: node.url || "",
                    managed: false,
                    level: this.incomingLinkLevel[node.id] || "unknown",
                }
            })
        },
        hasActiveSelection() {
            return this.selectedNodeID !== null || this.selectedLinkID !== null
        },
        getRefreshEnqueued: function() {
            // the server list only holds the servers of the selected fleet
            return this.getServerList.some(server => this.server_refresh_enqueued[server.id])
        },
        linkTestRunning() {
            return this.getServerList.filter(server => this.server_link_test[server.id]?.testing).length
        },
        linkTestSeen() {
            // Servers the workers reported on since the test was asked for. Compared by time, not by watching the
            // running count: a server without API key starts and ends within the same tick
            if (this.linkTest.startedAt === null) {
                return []
            }
            return this.getServerList.filter(server => (this.server_link_test[server.id]?.updated || 0) >= this.linkTest.startedAt)
        },
        linkTestInProgress() {
            return this.linkTestRunning > 0 || (this.linkTest.waiting && this.linkTestSeen.length === 0)
        },
        linkTestFinished() {
            return this.linkTest.startedAt !== null && this.linkTestSeen.length > 0 && this.linkTestRunning === 0
        },
    },
    methods: {
        fleetRefresh() {
            this.wsFleetRefresh(this.selectedFleet.id)
        },
        applyProblemFocus() {
            if (this.network !== null) {
                this.network.setFocus(this.problemsOnly ? this.problemFocus : null)
            }
        },
        locateNode(nodeID) {
            if (this.network === null || !this.network.focusNode(nodeID)) {
                return
            }
            const node = this.d3data.nodes.find(n => n.id === nodeID)
            if (node !== undefined && node._managed_server) {
                this.selectNode(node)
            }
        },
        fleetLinkTest() {
            // Disabled right away: the workers report the start of each server's test a moment later
            this.linkTest.startedAt = Date.now()
            this.linkTest.waiting = true
            clearTimeout(this.linkTest.timer)
            this.linkTest.timer = setTimeout(() => {
                // Still queued: the button is usable again, and the outcome is reported if the test starts later
                this.linkTest.waiting = false
                if (this.linkTest.startedAt !== null && this.linkTestSeen.length === 0) {
                    this.$bvToast.toast("The workers have not started it yet: they may be busy with other tasks, or not running. It runs as soon as one is free.", {
                        title: "Link test waiting",
                        variant: "warning",
                    })
                }
            }, LINK_TEST_START_TIMEOUT)
            this.wsFleetLinkTest(this.selectedFleet.id)
        },
        reportLinkTest() {
            const failed = this.linkTestSeen
                .filter(server => this.server_link_test[server.id]?.error)
                .map(server => `${server.name}: ${this.server_link_test[server.id].error}`)
            if (failed.length > 0) {
                const h = this.$createElement
                this.$bvToast.toast([h("ul", { class: "mb-0 pl-3" }, failed.map(text => h("li", text)))], {
                    title: `Links of ${failed.length} server${failed.length > 1 ? "s" : ""} could not be tested`,
                    variant: "danger",
                })
            } else {
                this.$bvToast.toast("The links are shown with their latest test results.", {
                    title: "Links tested",
                    variant: "success",
                    autoHideDelay: 3000,
                })
            }
        },
        fleetStatusRefresh() {
            this.wsFleetConnectionTest(this.selectedFleet.id)
        },
        toggleNodeInfoSideBar(show) {
            if (show === undefined) {
                this.nodeInfoCard.show = !this.nodeInfoCard.show
            } else {
                this.nodeInfoCard.show = show
            }
        },
        toggleLinkInfoSideBar(show) {
            if (show === undefined) {
                this.linkInfoCard.show = !this.linkInfoCard.show
            } else {
                this.linkInfoCard.show = show
            }
        },
        resetPositionsInfo() {
            this.nodeInfoCard.position.top = "4em"
            this.nodeInfoCard.position.left = "unset"
            this.nodeInfoCard.position.right = "1em"
            this.linkInfoCard.position.top = "4em"
            this.linkInfoCard.position.left = "unset"
            this.linkInfoCard.position.right = "1em"
        },
        resetPositionsPin() {
            this.pinCard.position.top = "4em"
            this.pinCard.position.left = "unset"
            this.pinCard.position.right = "1em"
        },
        togglePinPanel() {
            this.pinCard.show = !this.pinCard.show
            this.resetPositionsPin()
        },
        showPinnedContentOnNodes() {
            this.nodeFunctions.forEach(nodeFunctions => {
                nodeFunctions.setTabIndex(3)
            });
        },
        zoomFit() {
            if (this.$refs["minimap"]) {
                this.$refs["minimap"].zoomFit()
            }
        },
        generateGenericNodeComponent(node, htmlNode, d3Node, d3SVGNode) {
            let ComponentGenericServerNodeClass = Vue.extend(ServerNodeGeneric)
            let nodeInstance = new ComponentGenericServerNodeClass({
                parent: this,
                propsData: {
                    scaleInfo: this.scaleInfo,
                    server_id: node.id,
                    d3Node: d3Node,
                    d3SVGNode: d3SVGNode,
                    nodeData: node,
                }
            })
            // nodeInstance.$slots.default = ['Click me!']
            nodeInstance.$on('nodeFunctions', (nodeFunctions) => {
                this.nodeFunctions.push(nodeFunctions)
            })
            nodeInstance.$mount(htmlNode)
            this.allNodeInstances.push(nodeInstance)
            return nodeInstance
        },
        selectNode(node) {
            this.unselectAll()
            this.selectedNode = node
            this.selectedNodeID = node.id
        },
        selectLink(link) {
            this.unselectAll()
            this.selectedLink = link
            this.selectedLinkID = link.vid
        },
        unselectAll() {
            this.selectedNode = null
            this.selectedNodeID = null
            this.selectedLink = null
            this.selectedLinkID = null
        },
        constructNetwork() {
            const vm = this
            let eventHandlers = {
                nodeClick: function(node) {
                    vm.selectNode(node)
                    vm.toggleNodeInfoSideBar(true)
                },
                refreshMinimap: function() {
                    vm.minimapRedrawCount++
                },
                zoomFit: function() {
                    vm.zoomFit()
                },
                updateScale: function(scaleInfo) {
                    vm.scaleInfo = Object.assign(vm.scaleInfo, scaleInfo)
                },
                linkClicked: function(link) {
                    vm.selectLink(link)
                    vm.toggleLinkInfoSideBar(true)
                },
                canvasClicked: function() {
                    vm.unselectAll()
                },
            }
            let componentGenerator = {
                nodeComponent: function(node, htmlNode, d3Node, d3SVGNode) {
                    return vm.generateNodeComponent(node, htmlNode, d3Node, d3SVGNode)
                },
                miniNodeComponent: function(node, htmlNode, d3Node, d3SVGNode) {
                    return vm.generateMiniNodeComponent(node, htmlNode, d3Node, d3SVGNode)
                },
                microNodeComponent: function(node, htmlNode, d3Node, d3SVGNode) {
                    return vm.generateMicroNodeComponent(node, htmlNode, d3Node, d3SVGNode)
                },
                genericNodeComponent: function(node, htmlNode, d3Node, d3SVGNode) {
                    return vm.generateGenericNodeComponent(node, htmlNode, d3Node, d3SVGNode)
                }
            }
            if (this.$refs["networkContainer"] !== undefined) {
                let callbacks = {
                    simulationDone: () => { console.info("simu done") }
                }
                const network = d3Network.constructNetwork(
                    this.$refs["networkSVG"],
                    this.$refs["networkContainer"],
                    this.d3data,
                    componentGenerator,
                    eventHandlers,
                    callbacks
                )
                this.svgSelection = network.svgSelection
                this.zoom = network.zoom
                this.updateData = network.updateData
                this.network = Object.freeze({ setFocus: network.setFocus, focusNode: network.focusNode })
                this.graphReady = true
                this.applyProblemFocus()
            }
        },
        refreshServers(force=true) {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/fetchServers", {force: force})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch server index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
        refreshConnections(init_only=false) {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("connections/getConnections", {init_only: init_only})
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not fetch connection index",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
        refreshAllServerOnlineStatus() {
            this.wsFleetConnectionTest(this.selectedFleet.id)
        },
        syncWithStore() {
            this.d3data.nodes = JSON.parse(JSON.stringify(this.getServerList))
            this.d3data.links = JSON.parse(JSON.stringify(this.getConnectionList))
            this.d3data.links.forEach((link, index) => { // remap source -> origin
                link.origin = link.source
                link.source = parseInt(link.origin.id)
                const knownDestination = managedTarget(link, this.serversByUUID, this.serversByURL)
                if (knownDestination) {
                    link.target = parseInt(knownDestination.id)
                    link._managed_server = true
                } else {
                    link.target = 'v' + link.destination.Server.id
                    link.remote_sync_server = link.destination.Server
                    const targetServer = Object.values(this.remote_connections[link.origin.id] || {}).filter((server) => {
                        return server.Server.id == link.destination.Server.id
                    })
                    link.remote_sync_server.status = targetServer[0] ? targetServer[0].connectionTest : undefined
                    link._managed_server = false
                }
                if (link.filtering_rules.pull_rule_number > 0 || link.filtering_rules.push_rule_number > 0) {
                    link._has_rules = true
                }
                link._internal_sync = link.destination.Server.internal
                link.id = `${link.source}-${link.target}`
                link.vid = `${link.source}-${link.destination.Server.id}`
                link._has_rules = link._has_rules ? true : false
            })
            // Add fake nodes
            this.d3data.links
                .filter(l => !l._managed_server)
                .forEach(link => {
                    const virtualNode = Object.assign({}, link.remote_sync_server)
                    virtualNode.id = link.target
                    virtualNode._managed_server = false
                    this.d3data.nodes.push(virtualNode)
                })
            this.d3data.nodes = this.d3data.nodes.map(node => {
                node._managed_server = node._managed_server === undefined ? true : node._managed_server;
                return node
            })
        },
        updateWithStore() {
            this.getConnectionList.forEach((newConnectionLink, index) => {
                for (let i = 0; i < this.d3data.links.length; i++) {
                    if (this.d3data.links[i].vid == newConnectionLink.vid) {
                        const newConnectionLinkHasRules = newConnectionLink.filtering_rules.push_rule_number > 0 || newConnectionLink.filtering_rules.pull_rule_number > 0
                        this.d3data.links[i]._has_rules = newConnectionLinkHasRules
                        this.d3data.links[i]._internal_sync = newConnectionLink.destination.Server.internal
                        this.d3data.links[i].filtering_rules = newConnectionLink.filtering_rules
                        this.d3data.links[i].destination = newConnectionLink.destination
                        this.d3data.links[i].health = newConnectionLink.health
                        this.d3data.links[i].tested_at = newConnectionLink.tested_at
                    }
                }
            })
            if (typeof this.updateData === 'function') {
                this.updateData(this.d3data)
            }
        }
    },
    mounted() {
        this.svg = this.$refs["networkSVG"]
        Promise.all([
            this.refreshServers(false),
            this.refreshConnections(true),
            this.refreshAllServerOnlineStatus()
        ])
            .then(() => {
                this.syncWithStore()
                this.constructNetwork()
            })
    },
    destroyed() {
        clearTimeout(this.linkTest.timer)
        this.allNodeInstances.forEach(nodeInstance => {
            nodeInstance.$destroy() // We have to manually destroy the mounted nodes as it's not done automatically
        })
    },
    watch: {
        hasActiveSelection: function(isActive) {
            this.showSidebar = isActive || this.showSidebar
        },
        getConnectionList: function() {
            this.updateWithStore()
        },
        problemsOnly: function(enabled) {
            try {
                window.localStorage.setItem(PROBLEMS_ONLY_KEY, enabled ? "1" : "0")
            } catch (e) {
                // Not remembered, no harm
            }
            this.applyProblemFocus()
        },
        problemFocus: function() {
            if (this.problemsOnly) {
                this.applyProblemFocus()
            }
        },
        linkTestFinished: function(finished) {
            if (finished) {
                this.reportLinkTest()
                this.linkTest.startedAt = null
                this.linkTest.waiting = false
                clearTimeout(this.linkTest.timer)
            }
        },
        remote_connections: {
            handler: function() {
                this.refreshConnections()
            },
            deep: true,
        },
    },
    beforeRouteEnter(to, from, next) {
        if (store.getters["fleets/selectedFleet"] === null) {
            store.dispatch("fleets/selectFleet", {data: {id: to.params.fleet_id}}).then(() => {
                store.dispatch("servers/fetchServers", {force: true})
                next()
            }).catch(() => {
                next("/home")
            })
        } else {
            next()
        }
    },
}
</script>


<style>
#sidebar-network.b-sidebar {
    top: calc(54px + 1px);
    height: calc(100vh - 41px);
}

/* Sync links: colour and line style tell the health only. Arrowheads take the colour of their line */
path.link {
    stroke: var(--link-unknown);
    stroke-width: 5px;
    filter: drop-shadow(0px 1px 1px rgba(0, 0, 0, .35));
    cursor: pointer;
    transition: stroke-width .1s cubic-bezier(0.22, 0.61, 0.36, 1), opacity .2s ease;
}
path.link.link-ok {
    stroke: var(--link-ok);
}
path.link.link-degraded {
    stroke: var(--link-degraded);
}
path.link.link-broken {
    stroke: var(--link-broken);
}
path.link.link-unknown {
    stroke: var(--link-unknown);
    stroke-dasharray: 10 9;
}
/* Links to servers this fleet does not manage: slightly lighter */
path.link.unmanaged_server {
    stroke-width: 4px;
}
/* Configured but not used (push, pull and caching off) */
path.link.link-unused {
    stroke-width: 2.5px;
    opacity: .45;
}
path.link:hover {
    stroke-width: 7px;
    filter: drop-shadow(0px 2px 2px rgba(0, 0, 0, .45));
}
path.link.selected {
    stroke-width: 7px;
    opacity: 1;
    filter: drop-shadow(0 0 2px var(--var-color-misp-blue)) drop-shadow(0 0 4px var(--var-color-misp-blue));
}

path.marker.selected {
    stroke: #e4e6e7 !important;
}

.link-badge {
    overflow: visible;
    cursor: pointer;
    transition: opacity .2s ease;
}

.badge-container {
    font-family: FontAwesome;
    padding: 2px 5px;
    background-color: #ffffffee;
    border: 1px solid #adb5bd;
    border-radius: 4px;
    width: min-content;
    line-height: calc(24px - 4px - 2px);
    text-wrap: nowrap;
    color: #343a40;
}
.badge-empty {
    display: none;
}
.badge-icons i {
    font-size: 0.8em;
}
.badge-icons .badge-health {
    margin-right: 1px;
    font-size: 0.85em;
}
.badge-icons .badge-rules,
.badge-icons .badge-internal {
    color: #6c757d;
}
.badge-health-broken {
    color: var(--link-broken);
}
.badge-health-degraded {
    color: var(--link-degraded);
}
.badge-health-unknown {
    color: #6c757d;
}
.link-badge.link-broken .badge-container {
    border-color: var(--link-broken);
    background-color: #fff6f7ee;
}
.link-badge.link-degraded .badge-container {
    border-color: var(--link-degraded);
    background-color: #fffaf0ee;
}
.link-badge.link-unknown .badge-container {
    border-style: dashed;
}
.link-badge.link-unused {
    opacity: .6;
}
.link-badge.selected .badge-container {
    box-shadow: 0 0 0 2px #2ca1db66;
}

/* "Problems only": the rest stays in place, faded, so that the layout does not move */
path.link.dimmed,
.link-badge.dimmed,
foreignObject.nodeFO.dimmed {
    opacity: .15;
}
foreignObject.nodeFO {
    transition: opacity .2s ease;
}

/* A node found with the search */
foreignObject.nodeFO.node-located > div {
    animation: node-located 1s ease-out 2;
}
@keyframes node-located {
    0% { filter: drop-shadow(0 0 0 rgba(44, 161, 219, 0)); }
    40% { filter: drop-shadow(0 0 14px rgba(44, 161, 219, .95)); }
    100% { filter: drop-shadow(0 0 0 rgba(44, 161, 219, 0)); }
}
@media (prefers-reduced-motion: reduce) {
    foreignObject.nodeFO.node-located > div {
        animation: none;
        filter: drop-shadow(0 0 10px rgba(44, 161, 219, .95));
    }
    path.link, .link-badge, foreignObject.nodeFO {
        transition: none;
    }
}
</style>

<style scoped>

.network-action-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
    max-width: calc(100% - 30px);
    border-radius: 0.3rem;
    z-index: 5;
}

.action-group {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.action-group-view {
    gap: 0.75rem;
    padding-left: 0.75rem;
    border-left: 1px solid var(--health-rule);
}

.problems-switch {
    font-size: 0.85rem;
    user-select: none;
}

.problems-count {
    display: inline-block;
    min-width: 1.3rem;
    margin-left: 0.2rem;
    padding: 0 0.35rem;
    border-radius: 0.6rem;
    background: #eef8f2;
    color: var(--health-ok-ink);
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

.problems-count.has-problems {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.problems-none {
    flex-basis: 100%;
    font-size: 0.8rem;
    color: var(--health-ok-ink);
}

.network-legend-position {
    left: 15px;
    bottom: 15px;
    z-index: 4;
}

@media (max-width: 767.98px) {
    .action-group-view {
        flex-wrap: wrap;
        padding-left: 0;
        border-left: 0;
    }
    .action-group-view >>> .node-search {
        width: 100%;
    }
}

.network-container {
    background-image: linear-gradient(to right, #66666612 1px, transparent 1px), linear-gradient(to bottom, #66666612 1px, transparent 1px);
    background-size: 20px 20px;
    background-color: white;
}
.network-toolbar {
    top: 2em;
    right: 0em;
    /* max-width: 8em; */
    border-top-left-radius: 3px;
    border-bottom-left-radius: 3px;
    border: rgba(0, 0, 0, 0.125) 1px solid;
    z-index: 10;
}

.node text {
    stroke:#333;
    cursor:pointer;
}

.node circle{
    stroke:#fff;
    stroke-width:3px;
    fill:#555;
}

.right-panel {
    top: 2em;
    right: 0;
    width: 30em;
}

.slide-fade-enter-active {
  transition: all .3s cubic-bezier(0, 0, 0.23, 0.96)
}
.slide-fade-leave-active {
  transition: all .3s cubic-bezier(0, 0, 0.23, 0.96)
}
.slide-fade-enter, .slide-fade-leave-to {
  transform: translateX(10px);
  opacity: 0;
}
</style>
