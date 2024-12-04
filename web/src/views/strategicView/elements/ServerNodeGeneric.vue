<template>
    <div v-if="nodeData._managed_server">
        <ServerNodeMicro
            v-if="scale < 0.2"
            :server_id="server_id"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></ServerNodeMicro>
        <ServerNodeMini
            v-else-if="scale < 0.33"
            :server_id="server_id"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></ServerNodeMini>
        <ServerNode
            v-else
            :scale="scale"
            :server_id="server_id"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
            @nodeFunctions="propagatedNodeFunctions"
        ></ServerNode>
    </div>
    <div v-else>
        <UnmanagedServerNode
            :nodeData="nodeData"
            :d3Node="d3Node"
            :d3SVGNode="d3SVGNode"
        ></UnmanagedServerNode>
    </div>
</template>

<script>
import ServerNode from "@/views/strategicView/elements/ServerNode.vue"
import ServerNodeMini from "@/views/strategicView/elements/ServerNodeMini.vue"
import ServerNodeMicro from "@/views/strategicView/elements/ServerNodeMicro.vue"
import UnmanagedServerNode from "@/views/strategicView/elements/UnmanagedServerNode.vue"

export default {
    name: "ServerNodeGeneric",
    components: {
        ServerNode,
        ServerNodeMini,
        ServerNodeMicro,
        UnmanagedServerNode,
    },
    props: {
        scaleInfo: {
            type: Object,
            required: true
        },
        server_id: {
            required: false
        },
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
    data: function() {
        return {
        }
    },
    computed: {
        scale() {
            return this.scaleInfo.k
        }
    },
    methods: {
        propagatedNodeFunctions(nodeFunctions) {
            this.$emit('nodeFunctions', nodeFunctions);
        }
    },
    mounted: function() {
    }
}
</script>

<style>
path.link:hover {
    stroke: #00f;
    cursor: pointer;
}
</style>

<style scoped>
</style>