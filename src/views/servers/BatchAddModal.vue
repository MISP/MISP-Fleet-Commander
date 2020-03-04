<template>
    <b-modal 
        id="modal-batch-add"
        :title="`Batch Add Server`"
        size="xl"
        scrollable
        @hidden="resetModal"
        @ok="handleSubmission"
    >
        <b-form-group
            label="Server URL:"
            label-for="input-url"
            description="The URL to access the server. A numeric or character range can be defined by using the `[start, end]` constructor, where start and end can either be a number or a character"
        >

            <template v-slot:label>
                <div class="d-flex">
                    <span>Server URL:</span>
                    <span
                        v-if="getRangeBound.start != 0 || getRangeBound.end != 0"
                        class="d-flex align-items-center ml-4"
                    >
                        <b-badge variant="primary" class="">{{ getRangeBound.start }}</b-badge>
                        <i class="fas fa-arrow-right ml-3"></i>
                        <b-badge variant="primary" class="ml-3">{{ getRangeBound.end }}</b-badge>
                    </span>
                </div>
            </template>

            <b-input-group>
                <b-form-input
                    v-model="url"
                    placeholder="https://misp.[0,5].local.test"
                    type="url"
                ></b-form-input>
                <template v-slot:append>
                    <b-input-group-text>
                        <b-form-checkbox v-model="skip_ssl" switch>
                            <small>Allow Skip SSL validation</small>
                        </b-form-checkbox>
                    </b-input-group-text>
                </template>
            </b-input-group>
        </b-form-group>

        <b-form-group
            label="User Authorization Key:"
            label-for="input-authkey"
            description="The authorisation information of the user"
        >
            <template v-slot:label>
                <div class="d-flex">
                    Authorization:
                    <b-form-radio-group
                        class="d-inline-block ml-auto"
                        v-model="authMethodSelected"
                        :options="authMethodOptions"
                        name="radio-inline"
                    ></b-form-radio-group>
                </div>
            </template>

            <div v-if="authMethodSelected == 'api'">
                <b-form-input
                    v-model="authkey"
                    placeholder="3vl1KgDgQ1m0W3rwKMgB5z6MqfYkUZobGwIj3Urw"
                    autocomplete="off"
                ></b-form-input>
            </div>
            <div v-else>
                <b-input-group class="mb-2">
                    <template v-slot:prepend>
                        <b-input-group-text ><i class="fas fa-at"></i></b-input-group-text>
                    </template>
                    <b-form-input
                        v-model="basicEmail"
                        placeholder="admin@admin.test"
                        autocomplete="off"
                        type="search"
                    ></b-form-input>
                </b-input-group>
                <b-input-group>
                    <template v-slot:prepend>
                        <b-input-group-text ><i class="fas fa-key"></i></b-input-group-text>
                    </template>
                    <b-form-input
                        v-model="basicPassword"
                        type="password"
                        placeholder="Password1234"
                        autocomplete="off"
                    ></b-form-input>
                </b-input-group>
            </div>
        </b-form-group>

        <b-form-group
            description="By checking this box, it will try to add other MISP Servers connected to this one using known remote Servers"
        >
            <b-form-checkbox v-model="recursive_add">Recursively Add Servers</b-form-checkbox>
        </b-form-group>

        <h4>
            Server to add
            <b-button
                size="sm" variant="primary" :disabled="refreshInProgress"
                @click="refreshServers"
                v-b-tooltip.hover="'Test all server'">
                <i :class="['fas fa-sync-alt', refreshInProgress ? 'fa-spin' : '']"></i>
            </b-button>
        </h4>
        <b-table-lite
            small
            :items="elligibleServers"
            :fields="table.fields"
        >
            <template v-slot:head(select)>
                <b-form-checkbox
                    id="checkbox-head"
                    v-model="allChecked"
                    @change="setCheckOnServers"
                ></b-form-checkbox>
            </template>

            <template v-slot:cell(status)="row">
                <b-badge 
                    v-if="row.value.message !== undefined"
                    :variant="row.value.color"
                >
                    <div>{{ row.value.message }}</div>
                    <div>{{ row.value.version }}</div>
                </b-badge>
            </template>
            <template v-slot:cell(select)="row">
                <b-form-checkbox
                    :id="`checkbox-${row.index}`"
                    v-model="row.value.selected"
                    :disabled="row.value.disabled"
                ></b-form-checkbox>
            </template>
            <template v-slot:cell(name)="row">
                <b-form-input
                    v-model="row.value"
                ></b-form-input>
            </template>
            <template v-slot:cell(skip_ssl)="row">
                <b-form-checkbox v-model="row.value" switch>
                </b-form-checkbox>
            </template>
            <template v-slot:cell(authkey)="row">
                <b-form-input
                    v-model="row.value"
                ></b-form-input>
            </template>
        </b-table-lite>

        <template v-slot:modal-footer="{ ok, cancel }">
            <b-button variant="primary" @click="ok()" :disabled="!haveElligibleServers">
                <b-spinner 
                    small
                    v-if="postInProgress"
                ></b-spinner>
                <span class="sr-only">Saving...</span>
                <span v-if="!postInProgress">Save</span>
            </b-button>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
        </template>
    </b-modal>
</template>

<script>
import axios from "axios"

export default {
    name: "BatchAddModal",
    data: function() {
        return {
            url: "",
            skip_ssl: false,
            authkey: "",
            recursive_add: "true",
            basic: {
                email: "",
                password: ""
            },
            basicauth: "",
            authMethodSelected: "api",
            authMethodOptions: [
                { text: "API authorisation", value: "api" },
                { text: "Basic authorisation (email:password)", value: "basic" }
            ],
            allChecked: false,
            rangeRegex: /\[(?<start>\S+)(?:,|, )(?<end>\S+)\]/,
            elligibleServers: [],
            postInProgress: false,
            refreshInProgress: false,
            table: {
                fields: [
                    {key: "select", label: ""},
                    "status",
                    "name",
                    "url",
                    "authkey",
                    "skip_ssl"
                ]
            }
        }
    },
    computed: {
        basicEmail: {
            get: function() {
                return this.basic.email
            },
            set: function(newValue) {
                this.basic.email = newValue
                this.basicauth = `${this.basic.email}:${this.basic.password}`
            }
        },
        basicPassword: {
            get: function() {
                return this.basic.password
            },
            set: function(newValue) {
                this.basic.password = newValue
                this.basicauth = `${this.basic.email}:${this.basic.password}`
            }
        },
        haveElligibleServers() {
            return this.elligibleServers.filter(server => { return server.select.selected }).length > 0
        },
        getRangeBound() {
            let range = {start: "_", end: "_", type: "?"}
            let parsed = this.rangeRegex.exec(this.url)
            if (parsed !== null) {
                if (isNaN(parsed.groups.start) && isNaN(parsed.groups.end)) { // characters range
                    range.start = parsed.groups.start
                    range.end = parsed.groups.end
                    range.type = "char"
                } else if (!isNaN(parsed.groups.start) && !isNaN(parsed.groups.end)) { // number range
                    range.start = parseInt(parsed.groups.start)
                    range.end = parseInt(parsed.groups.end)
                    range.type = "number"
                }
            }
            return range
        },
        getRange() {
            let range = []
            if (this.getRangeBound.type == "char") {
                range = this.charRange(this.getRangeBound.start, this.getRangeBound.end)
            } else if (this.getRangeBound.type == "number") {
                range = this.numberRange(this.getRangeBound.start, this.getRangeBound.end)
            }
            return range
        }
    },
    methods: {
        resetModal() {
            this.url = "",
            this.skip_ssl = false,
            this.authkey = "",
            this.recursive_add = "true",
            this.basic = {
                email: "",
                password: ""
            },
            this.basicauth = "",
            this.authMethodSelected = "api"
        },
        handleSubmission() {
        },
        genElligibleServers() {
            this.elligibleServers.splice(0, this.elligibleServers.length)
            this.getRange.forEach(i => {
                const url = this.url.replace(this.rangeRegex, i)
                this.elligibleServers.push( // Seems not to be tracked by reactivity
                    {
                        status: {},
                        name: url,
                        url: url,
                        authkey: this.authMethodSelected == "api" ? this.authkey : this.basicauth,
                        skip_ssl: this.skip_ssl,
                        select: {selected: false, disabled: false}
                    }
                )
            })
        },
        setSkipSslForAllServers() {
            this.elligibleServers.forEach(server => {
                server.skip_ssl = this.skip_ssl
            })
        },
        setCheckOnServers(newValue) {
            this.elligibleServers.forEach(server => {
                server.select.selected = newValue
            })
        },
        refreshServers() {
            this.refreshInProgress = true
            const url = "http://127.0.0.1:5000/servers/batchTest"
            axios.post(url, this.elligibleServers)
                .then((response) => {
                    response.data.forEach(server => {
                        let elServer = this.elligibleServers.filter(elServer => {
                            return elServer.name == server.name && elServer.url == server.url && elServer.authkey == server.authkey
                        })
                        if (elServer.length > 0) {
                            elServer = elServer[0]
                            elServer.status = server.testResult
                            if (server.testResult.color == "success") {
                                elServer.select.selected = true
                            }
                        }
                    })
                })
                .catch(error => {
                    this.$bvToast.toast(error, {
                        title: "Could not test Servers",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.refreshInProgress = false
                })
        },
        numberRange(start, end) {
            let range = []
            let iterCount = 0
            const maxIterCount = 300
            for (let i=start; i<=end && iterCount<maxIterCount; i++) {
                range.push(i)
            }
            return range
        },
        charRange(startChar, endChar) {
            const startNum = startChar.charCodeAt()
            const endNum = endChar.charCodeAt()
            const numberRange = this.numberRange(startNum, endNum)
            let charRange = []
            numberRange.forEach(i => {
                charRange.push(String.fromCharCode(i))
            })
            return charRange
        }
    },
    watch: {
        url: function() {
            this.genElligibleServers()
        },
        authMethodSelected: function() {
            this.genElligibleServers()
        },
        authkey: function() {
            this.genElligibleServers()
        },
        skip_ssl: function() {
            this.setSkipSslForAllServers()
        }
    }
}
</script>

<style scoped>

</style>