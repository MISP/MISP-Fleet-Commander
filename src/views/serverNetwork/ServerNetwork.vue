<template>
<Layout name="LayoutStretch">
    <div>
        <div class="p-2 position-absolute">
                <b-form-radio-group
                    id="btn-radios-2"
                    v-model="scope"
                    :options="availableScopes"
                    buttons
                    button-variant="outline-primary"
                    size="sm"
                ></b-form-radio-group>
        </div>
        <div id="network" ref="networkContainer" class="w-100 h-100"></div>
        <div
            class="right-panel position-absolute pt-5 mr-2"
            v-show="showInfoSidebar"
        >
            <TheInfoSidebar
                :server="selectedNode"
            ></TheInfoSidebar>
        </div>
    </div>>
</Layout>
</template>

<script>
import Vue from "vue"
import Layout from "@/components/layout/Layout.vue"
import Node from "@/views/serverNetwork/elements/ServerNode.vue"
import TheInfoSidebar from "@/views/serverNetwork/elements/InfoSidebar.vue"
import * as d3 from "d3"

export default {
    name: "TheServerNetwork",
    components: {
        Layout,
        TheInfoSidebar
    },
    data: function () {
        return {
            scope: "simulation",
            showInfoSidebar: true,
            selectedNode: {

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
    methods: {
        toggleInfoSideBar() {
            this.showInfoSidebar = !this.showInfoSidebar
        },
        generateNodeHtml() {
            let ComponentNodeClass = Vue.extend(Node)
            let nodeInstance = new ComponentNodeClass({
                propsData: { 
                    server: this.fetchServers(),
                    event: this.fetchMISPEvent()
                }
            })
            // nodeInstance.$slots.default = ['Click me!']
            nodeInstance.$mount() // pass nothing
            return nodeInstance.$el.outerHTML
        },
        fetchMISPEvent() {
            // eslint-disable-next-line
            return {"Event":{"id":"2","orgc_id":"1","org_id":"1","date":"2020-01-23","threat_level_id":"1","info":"Event 2","published":false,"uuid":"5e29992c-27bc-4eba-a617-04b40a00020f","attribute_count":"5","analysis":"0","timestamp":"1581426985","distribution":"1","proposal_email_lock":false,"locked":false,"publish_timestamp":"0","sharing_group_id":"0","disable_correlation":false,"extends_uuid":"","event_creator_email":"admin@admin.test","Org":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","local":true},"Orgc":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","local":true},"Attribute":[{"id":"6","type":"vulnerability","category":"Payload delivery","to_ids":false,"uuid":"5e29a568-4bb4-47f2-8139-04b40a00020f","event_id":"2","distribution":"5","timestamp":"1579787624","comment":"","sharing_group_id":"0","deleted":false,"disable_correlation":false,"object_id":"0","object_relation":null,"first_seen":null,"last_seen":null,"value":"CVE-2019-20399","Galaxy":[{"id":"28","uuid":"75436e27-cb57-4f32-bf1d-9636dd78a2bf","name":"Backdoor","type":"backdoor","description":"Malware Backdoor galaxy.","version":"1","icon":"door-open","namespace":"misp","GalaxyCluster":[{"id":"5911","uuid":"2bb165dc-9f93-11e8-ae64-d3dbab0dd786","collection_uuid":"75436e27-cb57-4f32-bf1d-9636dd78a2bf","type":"backdoor","value":"Rosenbridge","tag_name":"misp-galaxy:backdoor=\"Rosenbridge\"","description":"The rosenbridge backdoor is a small, non-x86 core embedded alongside the main x86 core in the CPU. It is enabled by a model-specific-register control bit, and then toggled with a launch-instruction. The embedded core is then fed commands, wrapped in a specially formatted x86 instruction. The core executes these commands (which we call the 'deeply embedded instruction set'), bypassing all memory protections and privilege checks.\n\nWhile the backdoor should require kernel level access to activate, it has been observed to be enabled by default on some systems, allowing any unprivileged code to modify the kernel.\n\nThe rosenbridge backdoor is entirely distinct from other publicly known coprocessors on x86 CPUs, such as the Management Engine or Platform Security Processor; it is more deeply embedded than any known coprocessor, having access to not only all of the CPU's memory, but its register file and execution pipeline as well.","galaxy_id":"28","source":"Open Sources","authors":["raw-data"],"version":"6","meta":{"date":["August 2018"],"refs":["https:\/\/www.bleepingcomputer.com\/news\/security\/backdoor-mechanism-discovered-in-via-c3-x86-processors\/","https:\/\/github.com\/xoreaxeaxeax\/rosenbridge","https:\/\/media.defcon.org\/DEF%20CON%2026\/DEF%20CON%2026%20presentations\/Christopher%20Domas\/DEFCON-26-Christopher-Domas-GOD-MODE-%20UNLOCKED-hardware-backdoors-in-x86-CPUs.pdf"]},"tag_id":"33","local":false}]}],"ShadowAttribute":[],"Tag":[{"id":"33","name":"misp-galaxy:backdoor=\"Rosenbridge\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0}]},{"id":"18","type":"attachment","category":"Payload delivery","to_ids":false,"uuid":"5e2aba7e-9864-4fdd-9fba-2cc40a00020f","event_id":"2","distribution":"5","timestamp":"1580116889","comment":"","sharing_group_id":"0","deleted":false,"disable_correlation":false,"object_id":"0","object_relation":null,"first_seen":"2020-01-23T23:30:00.000000+00:00","last_seen":null,"value":"2sbgib.jpg","Galaxy":[],"ShadowAttribute":[]},{"id":"19","type":"attachment","category":"Payload delivery","to_ids":false,"uuid":"5e2ac044-b864-4763-bde1-39ab0a00020f","event_id":"2","distribution":"5","timestamp":"1579860036","comment":"","sharing_group_id":"0","deleted":false,"disable_correlation":false,"object_id":"0","object_relation":null,"first_seen":null,"last_seen":null,"value":"X4HDmYm.gif","Galaxy":[],"ShadowAttribute":[]},{"id":"20","type":"attachment","category":"Payload delivery","to_ids":false,"uuid":"5e2ac282-3b98-4d04-9ea4-33960a00020f","event_id":"2","distribution":"5","timestamp":"1579860610","comment":"","sharing_group_id":"0","deleted":false,"disable_correlation":false,"object_id":"0","object_relation":null,"first_seen":null,"last_seen":null,"value":"esa-logo-transparent.png","Galaxy":[],"ShadowAttribute":[]},{"id":"21","type":"comment","category":"Other","to_ids":false,"uuid":"5e2eacb8-3a78-47b4-a94d-4b060a00020f","event_id":"2","distribution":"5","timestamp":"1580117200","comment":"","sharing_group_id":"0","deleted":false,"disable_correlation":false,"object_id":"0","object_relation":null,"first_seen":"2020-01-21T19:00:00.000000+00:00","last_seen":null,"value":"qwewqe","Galaxy":[],"ShadowAttribute":[]}],"ShadowAttribute":[],"RelatedEvent":[],"Galaxy":[{"id":"26","uuid":"6fcb4472-6de4-11e7-b5f7-37771619e14e","name":"Course of Action","type":"mitre-course-of-action","description":"ATT&CK Mitigation","version":"7","icon":"link","namespace":"mitre-attack","GalaxyCluster":[{"id":"5599","uuid":"c085476e-1964-4d7f-86e1-d8657a7741e8","collection_uuid":"a8825ae8-6dea-11e7-8d57-7728f3cfe086","type":"mitre-course-of-action","value":"Accessibility Features Mitigation - T1015","tag_name":"misp-galaxy:mitre-course-of-action=\"Accessibility Features Mitigation - T1015\"","description":"To use this technique remotely, an adversary must use it in conjunction with RDP. Ensure that Network Level Authentication is enabled to force the remote desktop session to authenticate before the session is created and the login screen displayed. It is enabled by default on Windows Vista and later. (Citation: TechNet RDP NLA)\n\nIf possible, use a Remote Desktop Gateway to manage connections and security configuration of RDP within a network. (Citation: TechNet RDP Gateway)\n\nIdentify and block potentially malicious software that may be executed by an adversary with this technique by using whitelisting (Citation: Beechey 2010) tools, like AppLocker, (Citation: Windows Commands JPCERT) (Citation: NSA MS AppLocker) or Software Restriction Policies (Citation: Corio 2008) where appropriate. (Citation: TechNet Applocker vs SRP)","galaxy_id":"26","source":"https:\/\/github.com\/mitre\/cti","authors":["MITRE"],"version":"16","meta":{"external_id":["T1015"],"refs":["https:\/\/attack.mitre.org\/mitigations\/T1015","https:\/\/technet.microsoft.com\/en-us\/library\/cc732713.aspx","https:\/\/technet.microsoft.com\/en-us\/library\/cc731150.aspx","http:\/\/www.sans.org\/reading-room\/whitepapers\/application\/application-whitelisting-panacea-propaganda-33599","http:\/\/blog.jpcert.or.jp\/2016\/01\/windows-commands-abused-by-attackers.html","https:\/\/www.iad.gov\/iad\/library\/ia-guidance\/tech-briefs\/application-whitelisting-using-microsoft-applocker.cfm","http:\/\/technet.microsoft.com\/en-us\/magazine\/2008.06.srp.aspx","https:\/\/technet.microsoft.com\/en-us\/library\/ee791851.aspx"]},"tag_id":"23","local":false},{"id":"5630","uuid":"f9f9e6ef-bc0a-41ad-ba11-0924e5e84c4c","collection_uuid":"a8825ae8-6dea-11e7-8d57-7728f3cfe086","type":"mitre-course-of-action","value":"Account Use Policies - M1036","tag_name":"misp-galaxy:mitre-course-of-action=\"Account Use Policies - M1036\"","description":"Configure features related to account use like login attempt lockouts, specific login times, etc.","galaxy_id":"26","source":"https:\/\/github.com\/mitre\/cti","authors":["MITRE"],"version":"16","meta":{"external_id":["M1036"],"refs":["https:\/\/attack.mitre.org\/mitigations\/M1036"]},"tag_id":"24","local":false},{"id":"5598","uuid":"e3388c78-2a8d-47c2-8422-c1398b324462","collection_uuid":"a8825ae8-6dea-11e7-8d57-7728f3cfe086","type":"mitre-course-of-action","value":"Active Directory Configuration - M1015","tag_name":"misp-galaxy:mitre-course-of-action=\"Active Directory Configuration - M1015\"","description":"Configure Active Directory to prevent use of certain techniques; use SID Filtering, etc.","galaxy_id":"26","source":"https:\/\/github.com\/mitre\/cti","authors":["MITRE"],"version":"16","meta":{"external_id":["M1015"],"refs":["https:\/\/attack.mitre.org\/mitigations\/M1015"]},"tag_id":"25","local":false},{"id":"5663","uuid":"95c29444-49f9-49f7-8b20-bcd68d8fcaa6","collection_uuid":"a8825ae8-6dea-11e7-8d57-7728f3cfe086","type":"mitre-course-of-action","value":"AppCert DLLs Mitigation - T1182","tag_name":"misp-galaxy:mitre-course-of-action=\"AppCert DLLs Mitigation - T1182\"","description":"Identify and block potentially malicious software that may be executed through AppCert DLLs by using whitelisting (Citation: Beechey 2010) tools, like AppLocker, (Citation: Windows Commands JPCERT) (Citation: NSA MS AppLocker) that are capable of auditing and\/or blocking unknown DLLs.","galaxy_id":"26","source":"https:\/\/github.com\/mitre\/cti","authors":["MITRE"],"version":"16","meta":{"external_id":["T1182"],"refs":["https:\/\/attack.mitre.org\/mitigations\/T1182","http:\/\/www.sans.org\/reading-room\/whitepapers\/application\/application-whitelisting-panacea-propaganda-33599","http:\/\/blog.jpcert.or.jp\/2016\/01\/windows-commands-abused-by-attackers.html","https:\/\/www.iad.gov\/iad\/library\/ia-guidance\/tech-briefs\/application-whitelisting-using-microsoft-applocker.cfm"]},"tag_id":"26","local":false}]},{"id":"10","uuid":"84310ba3-fa6a-44aa-b378-b9e3271c58fa","name":"Android","type":"android","description":"Android malware galaxy based on multiple open sources.","version":"3","icon":"android","namespace":"misp","GalaxyCluster":[{"id":"1315","uuid":"932d18c5-6332-4334-83fc-4af3c46a4992","collection_uuid":"84310ba3-fa6a-44aa-b378-b9e3271c58fa","type":"android","value":"AdMob","tag_name":"misp-galaxy:android=\"AdMob\"","description":"AdMob is an advertisement library that is bundled with certain Android applications. ","galaxy_id":"10","source":"Open Sources","authors":["Unknown"],"version":"20","meta":{"refs":["https:\/\/www.symantec.com\/security_response\/writeup.jsp?docid=2014-052822-3437-99"]},"tag_id":"30","local":false}]}],"Object":[],"Tag":[{"id":"16","name":"tlp:green","colour":"#339900","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0},{"id":"23","name":"misp-galaxy:mitre-course-of-action=\"Accessibility Features Mitigation - T1015\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0},{"id":"24","name":"misp-galaxy:mitre-course-of-action=\"Account Use Policies - M1036\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0},{"id":"25","name":"misp-galaxy:mitre-course-of-action=\"Active Directory Configuration - M1015\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0},{"id":"26","name":"misp-galaxy:mitre-course-of-action=\"AppCert DLLs Mitigation - T1182\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0},{"id":"30","name":"misp-galaxy:android=\"AdMob\"","colour":"#0088cc","exportable":true,"user_id":"0","hide_tag":false,"numerical_value":null,"local":0}]}}
        },
        fetchServers() {
            // eslint-disable-next-line
            let server = [{"Server":{"id":"1","name":"self","url":"https:\/\/127.0.0.1","authkey":"HMg9FljTPLk5V1U8i5oQEh4HpYa1oMYpEKoZ1wby","org_id":"1","push":false,"pull":true,"push_sightings":false,"lastpulledid":null,"lastpushedid":null,"organization":null,"remote_org_id":"1","publish_without_email":false,"unpublish_event":false,"self_signed":true,"pull_rules":"{\"tags\":{\"OR\":[\"tlp:red\"],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]},\"url_params\":\"\"}","push_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]}}","cert_file":null,"client_cert_file":null,"internal":false,"skip_proxy":false,"caching_enabled":true,"priority":"1","cache_timestamp":"1580137725"},"Organisation":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"RemoteOrg":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"User":[]},{"Server":{"id":"2","name":"self-wrong","url":"http:\/\/127.0.0.1:8443","authkey":"HMg9FljTPLk5V1U8i5oQEh4HpYa1oMYpEKoZ1wby","org_id":"1","push":false,"pull":false,"push_sightings":false,"lastpulledid":null,"lastpushedid":null,"organization":null,"remote_org_id":"1","publish_without_email":false,"unpublish_event":false,"self_signed":false,"pull_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]},\"url_params\":\"\"}","push_rules":"{\"tags\":{\"OR\":[],\"NOT\":[]},\"orgs\":{\"OR\":[],\"NOT\":[]}}","cert_file":null,"client_cert_file":null,"internal":false,"skip_proxy":false,"caching_enabled":false,"priority":"2","cache_timestamp":false},"Organisation":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"RemoteOrg":{"id":"1","name":"ORGNAME","uuid":"5e29617d-f100-4370-92f9-50aaa4a3d503","nationality":"Not specified","sector":null,"type":"ADMIN"},"User":[]}]
            return server[0]
        },
        selectNode() {
            this.selectedNode = this.fetchServers()
        }
    },
    mounted() {
        let that = this
        const boundingRect = this.$refs["networkContainer"].getBoundingClientRect()
        const nodeHeight = 500
        const nodeWidth = 300
        const width = boundingRect.width
        const height = boundingRect.height

        const svg = d3.select("#network").append("svg")
            .attr("width", width)
            .attr("height", height)
        const container = svg.append("g")

        const simulation = d3.forceSimulation(this.d3data.nodes)
            .alphaDecay(0.15)
            // .force("link", d3.forceLink(this.d3data.links).id(function(d) { return d.id }))
            .force("link", d3.forceLink(this.d3data.links).id(function(d) { return d.id }).distance(nodeWidth/2).strength(0.5))
            // .force("charge", d3.forceManyBody())
            // .force("charge", d3.forceManyBody().strength(-5000))
            .force("collide", d3.forceCollide(nodeWidth))
            .force("center", d3.forceCenter(width / 2, height / 2))

        const zoom = d3.zoom()
            .scaleExtent([.1, 4])
            .on("zoom", function() { container.attr("transform", d3.event.transform) })
        svg.call(zoom)

        const link = container.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(this.d3data.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .style("stroke-width", function(d) { return Math.sqrt(d.weight) })

        const node = container.append("g")
            .attr("class", "nodes")
            .selectAll("div")
            .data(this.d3data.nodes)
            .enter().append("g")
            .on("click", function(node, index, nodes) {
                that.selectNode(node)
            })
            .call(drag(simulation))

        node.append("foreignObject")
            .attr("height", nodeHeight)
            .attr("width", nodeWidth)
            .append("xhtml:div")
            .attr("style", "height: 100%")
            // .html(d => this.generateNodeHtml(d))
            .html(this.generateNodeHtml())

        simulation
            .nodes(this.d3data.nodes)
            .on("tick", () => {
                link
                    .attr("x1", d => d.source.x + nodeWidth/2)
                    .attr("y1", d => d.source.y + nodeHeight/2)
                    .attr("x2", d => d.target.x + nodeWidth/2)
                    .attr("y2", d => d.target.y + nodeHeight/2)

                node.attr("transform", d => "translate(" + d.x + "," + d.y + ")")
            })

        simulation.force("link")
            .links(this.d3data.links)


        function drag(simulation) {
            function dragstarted(d) {
                if (!d3.event.active) simulation.alphaTarget(0.3).restart()
                d.fx = d.x
                d.fy = d.y
            }
            
            function dragged(d) {
                d.fx = d3.event.x
                d.fy = d3.event.y
            }
            
            function dragended(d) {
                if (!d3.event.active) simulation.alphaTarget(0)
                d.fx = null
                d.fy = null
            }
            
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended)
        }

    }
}
</script>

<style scoped>
.link {
  stroke: #aaa;
}

.node text {
    stroke:#333;
    cursos:pointer;
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
</style>
