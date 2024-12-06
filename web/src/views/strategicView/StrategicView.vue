<template>
<Layout name="LayoutStretch" class="position-relative">
    <div>
        <div class="network-toolbar position-absolute d-flex px-3 py-1 mx-5 bg-light shadow-sm">

            <b-dropdown variant="primary" size="sm" text="Layout" class="ml-1">
                 <b-dropdown-item
                    @click="zoomFit"
                >
                    <iconButton
                        text="Fit network in the view"
                        icon="expand"
                    ></iconButton>
                </b-dropdown-item>
            </b-dropdown>

            <b-button variant="primary" v-b-toggle.sidebar-network size="sm" class="ml-auto">
                <template v-if="!showSidebar">
                    <i class="fa-solid fa-table-columns"></i> Show Sidebar
                </template>
                <template v-else>
                    <i class="fa-solid fa-table-columns"></i> Hide Sidebar
                </template>
            </b-button>
        </div>
        <div ref="networkContainer" class="w-100 h-100 network-container">
            <svg ref="networkSVG"></svg>
        </div>

        <b-sidebar
            id="sidebar-network"
            v-model="showSidebar"
            body-class="px-2 py-3"
            shadow="lg"
            right
            width="400px"
            no-header
        >
            <div class="d-flex flex-column h-100" style="row-gap: 1em; overflow-x: hidden;">
                <transition name="slide-fade" mode="out-in">
                    <TheNodeInfoCard
                        v-if="selectedNodeID"
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
            class="position-absolute border overflow-hidden p-1 bg-white"
            :style="minimapPosition"
        >
            <!-- <NetworkMinimap
                v-if="svgSelection !== null"
                ref="minimap"
                :network="d3data"
                :svgRootNode="svg"
                :networkSvgSelection="svgSelection"
                :zoom="zoom"
                :redrawCount="minimapRedrawCount"
                :selectedNode="selectedNode"
            ></NetworkMinimap> -->
        </div>
    </div>
</Layout>
</template>

<script>
import Vue from "vue"
import { mapState, mapGetters } from "vuex"
import { websocketMixin } from "@/helpers/websocketMixin"
import Layout from "@/components/layout/Layout.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import ServerNodeGeneric from "@/views/strategicView/elements/ServerNodeGeneric.vue"
import ServerNode from "@/views/strategicView/elements/ServerNode.vue"
import ServerNodeMini from "@/views/strategicView/elements/ServerNodeMini.vue"
import ServerNodeMicro from "@/views/strategicView/elements/ServerNodeMicro.vue"
// import NetworkMinimap from "@/views/strategicView/elements/NetworkMinimap.vue"
import TheNodeInfoCard from "@/views/strategicView/elements/NodeInfoCard.vue"
import TheLinkInfoCard from "@/views/strategicView/elements/LinkInfoCard.vue"
import ThePinCard from "@/views/strategicView/elements/PinCard.vue"
import DraggableComponent from "@/components/ui/DraggableComponent.vue"
import d3Network from "@/helpers/d3Network.js"

export default {
    name: "TheStrategicView",
    mixins: [websocketMixin],
    components: {
        Layout,
        iconButton,
        TheNodeInfoCard,
        TheLinkInfoCard,
        ThePinCard,
        DraggableComponent,
        // NetworkMinimap
    },
    data: function () {
        return {
            refreshInProgress: false,
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
            scaleInfo: {x: 0, y: 0, k: 1},
            minimapPosition: {top: "unset", right: "unset", left: "20px", bottom: "20px"},
            minimapRedrawCount: 0,
            allNodeInstances: [],
        }
    },
    computed: {
        ...mapState({
            selectedFleet: state => state.fleets.selected,
            remote_connections: state => state.servers.remote_connections,
        }),
        ...mapGetters({
            serverCount: "servers/serverCount",
            getServerList: "servers/getServerList",
            serversByURL: "servers/serversByURL",
            serversByUUID: "servers/serversByUUID",
            getConnectionList: "connections/getConnectionList",
        }),
        hasActiveSelection() {
            return this.selectedNodeID !== null || this.selectedLinkID !== null
        }
    },
    methods: {
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
                const destinationURL = link.destination.Server.url
                const destinationURLWithoutTrailing = destinationURL.endsWith('/') ? destinationURL.substr(0, destinationURL.length - 1) : destinationURL
                const destinationUUID = link.destination.connectionTest.uuid
                let knownDestination
                if (this.serversByUUID[destinationUUID]) {
                    knownDestination = this.serversByUUID[destinationUUID]
                } else if (this.serversByURL[destinationURLWithoutTrailing]) {
                    knownDestination = this.serversByURL[destinationURLWithoutTrailing]
                }
                if (knownDestination) {
                    link.target = parseInt(knownDestination.id)
                    link._managed_server = true
                    if (link.filtering_rules.pull_rule_number > 0 || link.filtering_rules.push_rule_number > 0) {
                        link._has_rules = true
                    }
                } else {
                    link.target = 'v' + link.destination.Server.id
                    link.remote_sync_server = link.destination.Server
                    const targetServer = Object.values(this.remote_connections[link.origin.id]).filter((server) => {
                        return server.Server.id == link.destination.Server.id
                    })
                    link.remote_sync_server.status = targetServer[0].connectionTest
                    link._managed_server = false
                }
                link.id = `${link.source}-${link.target}`
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
        this.allNodeInstances.forEach(nodeInstance => {
            nodeInstance.$destroy() // We have to manually destroy the mounted nodes as it's not done automatically
        })
    },
    watch: {
        selectedLinkID: function(id) {
            const allPaths = this.$refs["networkSVG"].querySelectorAll(`path.link`)
            const selectedPath = this.$refs["networkSVG"].querySelector(`path#line_${id}.link`)
            const allMakers = this.$refs["networkSVG"].querySelectorAll(`path.marker`)
            const selectedMaker = this.$refs["networkSVG"].querySelector(`path#marker_${id}.marker`)
            if (allPaths !== null) {
                allPaths.forEach((path) => {
                    path.classList.remove('selected')
                    if (path.classList.contains('has_rules')) {
                        path.setAttribute('marker-end', 'url(#triangle-rule)')
                    } else {
                        path.setAttribute('marker-end', 'url(#triangle)')
                    }
                })
            }
            if (selectedPath !== null) {
                selectedPath.classList.add('selected')
                selectedPath.setAttribute('marker-end', 'url(#triangle-selected)')
            }
            if (allMakers !== null)
                allMakers.forEach((marker) => {
                    marker.classList.remove('selected')
                })
            if (selectedMaker !== null)
                selectedMaker.classList.add('selected')
        },
        hasActiveSelection: function(isActive) {
            this.showSidebar = isActive || this.showSidebar
        }
    }
}
</script>


<style>
#sidebar-network.b-sidebar {
    top: calc(40px + 1px);
    height: calc(100vh - 41px);
}

path.link {
    filter: drop-shadow(0px 1px 1px rgba(0, 0, 0, .7));
    cursor: pointer;
    transition: stroke-width .1s cubic-bezier(0.22, 0.61, 0.36, 1);
}
path.link.selected {
    filter: drop-shadow(0px 2px 2px #2ca1db77) !important;
    stroke: #2ca1db !important;
    stroke-width: 8px !important;
}
path.marker.selected {
    stroke: #e4e6e7 !important;
}
path.marker.has_rules.selected {
    stroke: #ffdf0a !important;
}
path.link:hover {
    filter: drop-shadow(0px 2px 2px rgba(0, 0, 0, .7));
    stroke-width: 8px !important;
    cursor: pointer;
}
</style>

<style scoped>

.network-container {
    background-image: linear-gradient(to right, #66666612 1px, transparent 1px), linear-gradient(to bottom, #66666612 1px, transparent 1px);
    background-size: 20px 20px;
    background-color: white;
}
.network-toolbar {
    width: calc(100% - 6.5em);
    border-bottom-left-radius: 1em;
    border-bottom-right-radius: 1em;
    border: rgba(0, 0, 0, 0.125) 1px solid;
    border-top: 0;
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
