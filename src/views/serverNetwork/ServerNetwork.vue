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
            <b-button
                @click="resetPositions"
            >Reset positions</b-button>
        </div>
        <div id="network" ref="networkContainer" class="w-100 h-100"></div>
        <div
            class="right-panel position-absolute"
            :style="{top: infoCard.position.top, right: infoCard.position.right, left: infoCard.position.left}"
        >
            <TheInfoCard
                :server="selectedNode"
                :open.sync="infoCard.show"
                :cardPosition.sync="infoCard.position"
            ></TheInfoCard>
        </div>
    </div>>
</Layout>
</template>

<script>
import Vue from "vue"
import { mapState, mapGetters } from "vuex"
import Layout from "@/components/layout/Layout.vue"
import Node from "@/views/serverNetwork/elements/ServerNode.vue"
import TheInfoCard from "@/views/serverNetwork/elements/InfoCard.vue"
import d3Network from "@/helpers/d3Network.js"

export default {
    name: "TheServerNetwork",
    components: {
        Layout,
        TheInfoCard
    },
    data: function () {
        return {
            scope: "administration",
            infoCard: {
                show: false,
                position: {top: "4em", left: "unset", right: "1em"}
            },
            selectedNode: {
                Server: {
                    name: "",
                    url: "",
                    authkey: "",
                    push: "",
                    pull: "",
                },
                Organisation: {
                    name: "",
                    uuid: "",
                    type: ""
                }
            },
            availableScopes: [
                { text: "Administration", value: "administration" },
                { text: "Realtime Sharing Simulation", value: "simulation" }
            ],
            MISP: {
            },
            d3data: {
                "nodes":[
                    {"id": "node1", "name":"node1","group":1},
                    {"id": "node2", "name":"node2","group":2},
                    {"id": "node3", "name":"node3","group":2},
                    {"id": "node4", "name":"node4","group":3},
                    {"id": "node5", "name":"node5","group":1}
                ],
                "links":[
                    {"source": "node2","target": "node1","weight":1},
                    {"source": "node1","target": "node3","weight":3},
                    {"source": "node4","target": "node5","weight":3}
                ]
            }
        }
    },
    computed: {
        ...mapState({
            getServers: state => state.servers.all,
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
        generateNodeHtml() {
            let ComponentNodeClass = Vue.extend(Node)
            let nodeInstance = new ComponentNodeClass({
                propsData: { 
                    server: this.fetchServers(),
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
        selectNode() {
            // eslint-disable-next-line
            this.selectedNode = {"Server":{"id":"1","name":"self","url":"https:\/\/127.0.0.1","authkey":"HMg9FljTPLk5V1U8i5oQEh4HpYa1oMYpEKoZ1wby","org_id":"1","push":false,"pull":true,"push_sightings":false,"lastpulledid":null,"lastpushedid":null,"organization":null,"remote_org_id":"1","publish_without_email":false,"unpublish_event":false,"self_signed":true,"pull_rules":"{\"tags\":{\"OR\":[\"tlp:red\"],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]},\"url_params\":\"\"}","push_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]}}","cert_file":null,"client_cert_file":null,"internal":false,"skip_proxy":false,"caching_enabled":true,"priority":"1","cache_timestamp":"1580137725"},"Organisation":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"RemoteOrg":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"User":[]},{"Server":{"id":"2","name":"self-wrong","url":"http:\/\/127.0.0.1:8443","authkey":"HMg9FljTPLk5V1U8i5oQEh4HpYa1oMYpEKoZ1wby","org_id":"1","push":false,"pull":false,"push_sightings":false,"lastpulledid":null,"lastpushedid":null,"organization":null,"remote_org_id":"1","publish_without_email":false,"unpublish_event":false,"self_signed":false,"pull_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]},\"url_params\":\"\"}","push_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]}}","cert_file":null,"client_cert_file":null,"internal":false,"skip_proxy":false,"caching_enabled":false,"priority":"2","cache_timestamp":false},"Organisation":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"RemoteOrg":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"User":[]}
        }
    },
    mounted() {
        const vm = this
        let eventHandlers = {
            nodeClick: function(node) {
                vm.selectNode(node)
                vm.toggleInfoSideBar(true)
            }
        }
        let htmlTemplateGenerator = {
            nodeHtml: function(node) {
                return vm.tempgenerateNodeHtml(node)
            }
        }
        d3Network.constructNetwork(
            "#network",
            this.$refs["networkContainer"].getBoundingClientRect(),
            this.d3data,
            htmlTemplateGenerator,
            eventHandlers
        )
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
