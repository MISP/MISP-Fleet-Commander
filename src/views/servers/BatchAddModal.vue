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
                        <b-badge variant="primary" class="">{{ getRangeBound.startText }}</b-badge>
                        <i class="fas fa-arrow-right ml-3"></i>
                        <b-badge variant="primary" class="ml-3">{{ getRangeBound.endText }}</b-badge>
                        <b-badge
                            v-if="getRangeBound.type == 'char' && getRangeBound.overflow"
                            variant="danger" class="ml-3"
                        >
                            <i class="fas fa-exclamation"></i>
                            Only one letter is taken into account for the range
                        </b-badge>
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

        <h4>Server to add</h4>

        <batchAddTableServer
            :servers="elligibleServers"
            :skip_ssl="skip_ssl"
        ></batchAddTableServer>

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
import batchAddTableServer from "@/components/ui/elements/batchAddTableServer.vue"

export default {
    name: "BatchAddModal",
    components: {
        batchAddTableServer
    },
    data: function() {
        return {
            url: "",
            skip_ssl: false,
            authkey: "",
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
            rangeRegex: /\[(?<start>\S+)(?:,|, )(?<end>\S+)\]/,
            elligibleServers: [],
            postInProgress: false,
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
            let range = {start: "_", end: "_", startText: "_", endText: "_", type: "?"}
            let parsed = this.rangeRegex.exec(this.url)
            if (parsed !== null) {
                if (isNaN(parsed.groups.start) && isNaN(parsed.groups.end)) { // characters range
                    range.start = parsed.groups.start[0]
                    range.end = parsed.groups.end[0]
                    range.startText = range.start
                    range.endText = range.end
                    range.type = "char"
                    range.overflow = parsed.groups.start.length > 1
                } else if (!isNaN(parsed.groups.start) && !isNaN(parsed.groups.end)) { // number range
                    range.start = parseInt(parsed.groups.start)
                    range.end = parseInt(parsed.groups.end)
                    range.startText = parsed.groups.start
                    range.endText = parsed.groups.end
                    range.type = "number"
                    const paddedRegex = /^(?<padding>0+)\d+$/
                    let parsedPadded = paddedRegex.exec(parsed.groups.start)
                    if (parsedPadded !== null && parsedPadded.groups.padding.length > 0) {
                        range.padding = parsed.groups.start.length
                    } else {
                        range.padding = 0
                    }
                }
            }
            return range
        },
        getRange() {
            let range = []
            if (this.getRangeBound.type == "char") {
                range = this.charRange(this.getRangeBound.start, this.getRangeBound.end)
            } else if (this.getRangeBound.type == "number") {
                range = this.numberRange(this.getRangeBound.start, this.getRangeBound.end, this.getRangeBound.padding)
            }
            return range
        }
    },
    methods: {
        resetModal() {
            this.url = "",
            this.skip_ssl = false,
            this.authkey = "",
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
                        select: {selected: false, disabled: false},
                    }
                )
            })
        },
        numberRange(start, end, padding) {
            let range = []
            let iterCount = 0
            const maxIterCount = 300
            for (let i=start; i<=end && iterCount<maxIterCount; i++) {
                let number = i
                if (padding > 0) {
                    number = String(i).padStart(padding, "0")
                }
                range.push(number)
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
        authMethodSelected: function(newValue) {
            this.elligibleServers.forEach(elServer => {
                elServer.authkey = newValue == "api" ? this.authkey : this.basicauth
            })
        },
        authkey: function(newValue) {
            this.elligibleServers.forEach(elServer => {
                elServer.authkey = newValue
            })
        },
        basicauth: function(newValue) {
            this.elligibleServers.forEach(elServer => {
                elServer.basicauth = newValue
            })
        },
    }
}
</script>

<style scoped>

</style>