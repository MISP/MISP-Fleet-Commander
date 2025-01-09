<template>
    <div class="p-2">
        <b-overlay :show="showOverlay" rounded="sm">
            <div><strong>PUSH Rules</strong> <b-badge :variant="hasPushRules ? 'primary' : 'secondary'">{{ pushRuleNumber }}</b-badge></div>
            <JsonEditorVue
                v-model="editorValuePush"
                :mode="editorMode"
                :mainMenuBar="true"
                :navigationBar="false"
                :onRenderMenu="onRenderMenuItemFunctionPush"
                :validator="getJsonValidator('push')"
                :stringified="false"
            />

            <div class="mt-4"><strong>PULL Rules</strong> <b-badge :variant="hasPullRules ? 'primary' : 'secondary'">{{ pullRuleNumber }}</b-badge></div>
            <JsonEditorVue
                v-model="editorValuePull"
                :mode="editorMode"
                :mainMenuBar="true"
                :navigationBar="false"
                :onRenderMenu="onRenderMenuItemFunctionPull"
                :validator="getJsonValidator('pull')"
                :stringified="false"
            />
        </b-overlay>
    </div>

</template>

<script>
import jsonViewer from "@/components/ui/elements/jsonViewer.vue"
import JsonEditorVue from 'json-editor-vue'
import { Mode, createAjvValidator } from 'vanilla-jsoneditor'

const faFloppyDisk = {
    prefix: "fas",
    iconName: "save",
    "icon": [512, 512,
        [
            "floppy-disk"
        ],
        "f0c7",
        "M64 32C28.7 32 0 60.7 0 96L0 416c0 35.3 28.7 64 64 64l320 0c35.3 0 64-28.7 64-64l0-242.7c0-17-6.7-33.3-18.7-45.3L352 50.7C340 38.7 323.7 32 306.7 32L64 32zm0 96c0-17.7 14.3-32 32-32l192 0c17.7 0 32 14.3 32 32l0 64c0 17.7-14.3 32-32 32L96 224c-17.7 0-32-14.3-32-32l0-64zM224 288a64 64 0 1 1 0 128 64 64 0 1 1 0-128z"
    ]
}

const serverConnectionRuleSchemaBase = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "orgs": {
            "type": "object",
            "properties": {
                "NOT": {
                    "type": "array",
                    "items": {}
                },
                "OR": {
                    "type": "array",
                    "items": {}
                }
            },
            "required": ["NOT", "OR"],
            "additionalProperties": false
        },
        "tags": {
            "type": "object",
            "properties": {
                "NOT": {
                    "type": "array",
                    "items": {}
                },
                "OR": {
                    "type": "array",
                    "items": {}
                }
            },
            "required": ["NOT", "OR"],
            "additionalProperties": false
        },
        "type_attributes": {
            "type": "object",
            "properties": {
                "NOT": {
                    "type": "array",
                    "items": {}
                }
            },
            "required": ["NOT"],
            "additionalProperties": false
        },
        "type_objects": {
            "type": "object",
            "properties": {
                "NOT": {
                    "type": "array",
                    "items": {}
                }
            },
            "required": ["NOT"],
            "additionalProperties": false
        },
    },
    "required": ["orgs", "tags"],
    "additionalProperties": false
}
const serverConnectionRuleSchemaPush = JSON.parse(JSON.stringify(serverConnectionRuleSchemaBase))
const serverConnectionRuleSchemaPull = JSON.parse(JSON.stringify(serverConnectionRuleSchemaBase))
serverConnectionRuleSchemaPull.properties['url_params'] = { "type": "string" }
serverConnectionRuleSchemaPull.required.push('url_params')

export default {
    name: "strategicViewConnectionRules",
    components: {
        jsonViewer,
        JsonEditorVue
    },
    props: {
        connection: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            editorValuePush: {},
            editorValuePull: {},
            editorMode: Mode.text,
            showOverlay: false,
        }
    },
    computed: {
        pushRuleNumber: function() {
            return (this.pushRules?.orgs?.NOT !== undefined ? this.pushRules.orgs.NOT.length : 0) +
                (this.pushRules?.orgs?.OR !== undefined ? this.pushRules.orgs.OR.length : 0) +
                (this.pushRules?.tags?.NOT !== undefined ? this.pushRules.tags.NOT.length : 0) +
                (this.pushRules?.tags?.OR !== undefined ? this.pushRules.tags.OR.length : 0)
        },
        pushRules: function() {
            return typeof this.connection.filtering_rules.push_rules === 'string' ? JSON.parse(this.connection.filtering_rules.push_rules) : this.connection.filtering_rules.push_rules
        },
        hasPushRules: function() {
            return this.pushRuleNumber > 0
        },
        pullRuleNumber: function() {
            return (this.pullRules?.orgs?.NOT !== undefined ? this.pullRules.orgs.NOT.length : 0) +
                (this.pullRules?.orgs?.OR !== undefined ? this.pullRules.orgs.OR.length : 0) +
                (this.pullRules?.tags?.NOT !== undefined ? this.pullRules.tags.NOT.length : 0) +
                (this.pullRules?.tags?.OR !== undefined ? this.pullRules.tags.OR.length : 0) +
                (this.pullRules?.url_params?.length > 0 ? this.pullRules?.url_params.split('/').length : 0)
        },
        pullRules: function() {
            return typeof this.connection.filtering_rules.pull_rules === 'string' ? JSON.parse(this.connection.filtering_rules.pull_rules) : this.connection.filtering_rules.pull_rules
        },
        hasPullRules: function() {
            return this.pullRuleNumber > 0
        },
        server_id: function() {
            return this.connection.source.id
        },
        remote_server_id: function() {
            return this.connection.destination.Server.id
        },
    },
    methods: {
        onRenderMenuItemFunction(items, context, modal, readOnly) {
            const newItems = items.filter((item) => {
                return item.className !== undefined ?
                    item.className.startsWith('jse-group-button') ||
                    item.className.startsWith('jse-format') ||
                    item.className.startsWith('jse-compact') ||
                    item.className.startsWith('jse-sort')
                : false
            })
            newItems.push({type: 'separator'})
            return newItems
        },
        onRenderMenuItemFunctionPush(items, context, modal, readOnly) {
            const newItems = this.onRenderMenuItemFunction(items, context, modal, readOnly)
            newItems.push({
                type: "button",
                icon: faFloppyDisk,
                title: "Save",
                className: "jse-save",
                onClick: this.savePushRule
            })
            return newItems
        },
        onRenderMenuItemFunctionPull(items, context, modal, readOnly) {
            const newItems = this.onRenderMenuItemFunction(items, context, modal, readOnly)
            newItems.push({
                type: "button",
                icon: faFloppyDisk,
                title: "Save",
                className: "jse-save",
                onClick: this.savePullRule
            })
            return newItems
        },
        savePushRule() {
            const payload = {
                server_id: this.server_id,
                remote_server_id: this.remote_server_id,
                payload: this.editorValuePush
            }
            this.showOverlay = true
            this.$store.dispatch('connections/savePushRules', payload)
                .then(() => {
                })
                .catch(error => {
                    this.$bvToast.toast(error.message !== undefined ? error.message : error, {
                        title: `Could not save push rules`,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.showOverlay = false
                })
            
        },
        savePullRule() {
            const payload = {
                server_id: this.server_id,
                remote_server_id: this.remote_server_id,
                payload: this.editorValuePull
            }
            this.showOverlay = true
            this.$store.dispatch('connections/savePullRules', payload)
                .then(() => {
                })
                .catch(error => {
                    this.$bvToast.toast(error.message !== undefined ? error.message : error, {
                        title: `Could not save pull rules`,
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.showOverlay = false
                })
        },
        getJsonValidator(method) {
            if (method == 'push') {
                return createAjvValidator({ schema: serverConnectionRuleSchemaPush, schemaDefinitions: {} })
            } else {
                return createAjvValidator({ schema: serverConnectionRuleSchemaPull, schemaDefinitions: {} })
            }
        },
        setPushRules() {
            if (this.pushRuleNumber > 0) {
                this.editorValuePush = JSON.parse(JSON.stringify(this.pushRules))
            } else {
                this.editorValuePush = {
                    orgs: {
                        NOT: [],
                        OR: []
                    },
                    tags: {
                        NOT: [],
                        OR: []
                    },
                }
            }
        },
        setPullRules() {
            if (this.pullRuleNumber > 0) {
                this.editorValuePull = JSON.parse(JSON.stringify(this.pullRules))
            } else {
                this.editorValuePull = {
                    orgs: {
                        NOT: [],
                        OR: []
                    },
                    tags: {
                        NOT: [],
                        OR: []
                    },
                    url_params: ""
                }
            }
        },
    },
    watch: {
        pushRules: function() {
            this.setPushRules()
        },
        pullRules: function() {
            this.setPullRules()
        },
    },
    mounted: function() {
        this.setPushRules()
        this.setPullRules()
    },
}
</script>

<style scoped>
strong {
    font-size: 1.2em;
}
</style>
<style>
.jse-main .jse-save {
    margin-left: auto !important;
}
</style>