<template>
<Layout name="LayoutStretch" class="position-relative">
    <div>
        <div class="network-toolbar position-absolute px-3 py-1 mx-5 bg-light shadow-sm">
            <b-form-radio-group
                id="btn-radios-2"
                v-model="scope"
                :options="availableScopes"
                buttons
                button-variant="outline-primary"
                size="sm"
            ></b-form-radio-group>
             <b-dropdown variant="primary" size="sm" text="Layout">
                <b-dropdown-item
                    @click="resetPositions"
                >
                    <iconButton
                        text="Reset info window location"
                        icon="window-restore"
                    ></iconButton>
                </b-dropdown-item>
            </b-dropdown>
        </div>
        <div id="network" ref="networkContainer" class="w-100 h-100"></div>
        <DraggableComponent
            class="right-panel"
            :positions.sync="infoCard.position"
            draggableContainer="networkInfoPanel"
            handleClass=".card-header"
        >
            <TheInfoCard
                :server="selectedNode"
                :open.sync="infoCard.show"
            ></TheInfoCard>
        </DraggableComponent>
    </div>
</Layout>
</template>

<script>
import Vue from "vue"
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import iconButton from "@/components/ui/elements/iconButton.vue"
import Node from "@/views/serverNetwork/elements/ServerNode.vue"
import TheInfoCard from "@/views/serverNetwork/elements/InfoCard.vue"
import DraggableComponent from "@/components/ui/DraggableComponent.vue"
import d3Network from "@/helpers/d3Network.js"

export default {
    name: "TheServerNetwork",
    components: {
        Layout,
        iconButton,
        TheInfoCard,
        DraggableComponent
    },
    data: function () {
        return {
            scope: "administration",
            refreshInProgress: false,
            infoCard: {
                show: false,
                position: {top: "4em", left: "unset", right: "1em"}
            },
            selectedNode: {},
            availableScopes: [
                { text: "Administration", value: "administration" },
                { text: "Realtime Sharing Simulation", value: "simulation" }
            ],
            d3data: {
                nodes: [],
                links: []
            },
        }
    },
    computed: {
        ...mapState({
            getServers: state => state.servers.all,
            getConnections: state => state.connections.all
        })
    },
    methods: {
        toggleInfoSideBar(show) {
            if (show === undefined) {
                this.infoCard.show = !this.infoCard.show
            } else {
                this.infoCard.show = show
            }
        },
        resetPositions() {
            this.infoCard.position.top = "4em"
            this.infoCard.position.left = "unset"
            this.infoCard.position.right = "1em"
        },
        generateNodeHtml(node) {
            let ComponentNodeClass = Vue.extend(Node)
            let nodeInstance = new ComponentNodeClass({
                propsData: { 
                    // server: this.fetchServers(),
                    server: node,
                    event: {}
                }
            })
            // nodeInstance.$slots.default = ['Click me!']
            nodeInstance.$mount() // pass nothing
            return nodeInstance.$el.outerHTML
        },
        tempgenerateNodeHtml() {
            return "<div style='border:1px solid black;background-color: blue;height:100%'>Node</div>"
        },
        selectNode(node) {
            this.selectedNode = node
        },
        constructNetwork() {
            const vm = this
            let eventHandlers = {
                nodeClick: function(node) {
                    vm.selectNode(node)
                    vm.toggleInfoSideBar(true)
                }
            }
            let htmlTemplateGenerator = {
                nodeHtml: function(node) {
                    // return vm.tempgenerateNodeHtml(node)
                    return vm.generateNodeHtml(node)
                }
            }
            if (this.$refs["networkContainer"] !== undefined) {
                d3Network.constructNetwork(
                    "#network",
                    this.$refs["networkContainer"].getBoundingClientRect(),
                    this.d3data,
                    htmlTemplateGenerator,
                    eventHandlers
                )
            }
        },
        refreshServers(init_only=false) {
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/getAllServers", {init_only: init_only})
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
            this.refreshInProgress = true
            return new Promise((resolve, reject) => {
                this.$store.dispatch("servers/refreshAllConnectionState")
                    .then(() => {
                        resolve()
                    })
                    .catch(error => {
                        this.$bvToast.toast(error, {
                            title: "Could not reach Server",
                            variant: "danger",
                        })
                        reject()
                    })
                    .finally(() => {
                        this.refreshInProgress = false
                    })
            })
        },
        syncWithStore() {
            this.d3data.nodes = JSON.parse(JSON.stringify(this.getServers))
            this.d3data.links = JSON.parse(JSON.stringify(this.getConnections))
            this.d3data.links.forEach(link => { // remap source -> origin
                link.origin = link.source
                link.source = parseInt(link.origin.id)
                link.target = parseInt(link.destination.Server.id)
                link.id = `${link.source}-${link.target}`
            })
        }
    },
    mounted() {
        Promise.all([
            this.refreshServers(true),
            this.refreshConnections(true),
            this.refreshAllServerOnlineStatus()
        ])
            .then(() => {
                this.syncWithStore()
                this.constructNetwork()
            })
    }
}
</script>

<style scoped>
.network-toolbar {
    width: calc(100% - 6.5em);
    border-bottom-left-radius: 1em;
    border-bottom-right-radius: 1em;
    border: rgba(0, 0, 0, 0.125) 1px solid;
    border-top: 0;
    z-index: 10;
}

.link {
  stroke: #aaa;
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
    width: 25em;
}
</style>
