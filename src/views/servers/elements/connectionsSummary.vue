<template>
    <div v-if="connectionCount > 0">
        <div :id="`badge-connections-${row_index}`" class="badge-list">
            <template v-if="use_diode">
                <span
                    v-for="(connection, index) in getConnections"
                    v-bind:key="index"
                    :id="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                    :class="['text-nowrap', `text-${connection.connectionTest.status.color}`]"
                >
                    <b-icon icon="circle-fill"></b-icon>
                    {{ labelText(connection) }}
                    <b-popover
                        href="#" tabindex="0"
                        triggers="hover"
                        placement="top"
                        boundary="viewport"
                        :target="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                        :variant="connection.connectionTest.status.color"
                    >
                        <connectionState :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                    </b-popover>
                </span>
            </template>
            <template v-else>

                <b-badge
                    v-if="expand_issue_only"
                    :id="`connection-popover-${row_index}-OK}`"
                    variant="success"
                    rounded
                >
                    {{ getOkConnectionSummary.text }}
                    <b-popover
                        href="#" tabindex="0"
                        triggers="hover"
                        placement="top"
                        boundary="viewport"
                        :target="`connection-popover-${row_index}-OK}`"
                        variant="success"
                    >
                        <ul class="mb-0" style="padding-inline-start: 20px;">
                            <li v-for="(name) in getOkConnectionSummary.names" :key="`ok-${name}`">
                                {{ name }}
                            </li>
                        </ul>
                    </b-popover>
                </b-badge>
                <b-badge
                    v-for="(connection, index) in getConnections"
                    v-bind:key="index"
                    :id="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                    :class="getRoundedClass(index)"
                    :variant="connection.connectionTest.status.color"
                >
                    {{ labelText(connection) }}
                    <b-popover
                        href="#" tabindex="0"
                        triggers="hover"
                        placement="top"
                        boundary="viewport"
                        :target="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                        :variant="connection.connectionTest.status.color"
                    >
                        <connectionState :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                    </b-popover>
                </b-badge>
            </template>
        </div>
    </div>
</template>

<script>
import connectionState from "@/views/servers/elements/connectionState.vue"

export default {
    name: "connectionsSummary",
    components: {
        connectionState
    },
    props: {
        connections: {},
        row_index: {
            type: Number,
            required: true
        },
        text_in_badge: {
            type: String,
            default: function() { return "" }
        },
        use_diode: {
            type: Boolean,
            default: function() { return false }
        },
        expand_issue_only: {
            type: Boolean,
            default: function() { return true }
        }
    },
    data: function() {
        return {
            vidToUUID: {}
        }
    },
    computed: {
        connectionCount() {
            return this.getConnections.length
        },
        getConnections() {
            return this.expand_issue_only ? this.getIssueConnections : this.connections
        },
        getIssueConnections() {
            if (Array.isArray(this.connections)) {
                return this.connections.filter(connection => {
                    return connection.connectionTest.status.color !== "success"
                })
            } else {
                return this.connections
            }
        },
        getOkConnections() {
            if (Array.isArray(this.connections)) {
                return this.connections.filter(connection => {
                    return connection.connectionTest.status.color === "success"
                })
            } else {
                return this.connections
            }
        },
        getOkConnectionSummary() {
            return {
                names: this.getOkConnections.map(connection => connection.Server.name),
                text: `${this.getOkConnections.length} / ${this.connections.length} OK`
            }
        }
    },
    methods: {
        getRoundedClass(index) {
            if (this.connectionCount == 1) {
                return ""
            } else if (index == 0) {
                return "rounded-left flat-right"
            } else if (index == this.connectionCount-1) {
                return "rounded-right flat-left"
            } else {
                return "rounded-0"
            }
        },
        labelText(connection) {
            return this.text_in_badge !== "" ? this.text_in_badge : connection.Server.name
        },
        getUUID(connection) {
            if (this.vidToUUID[connection.vid] === undefined) {
                this.vidToUUID[connection.vid] = this.$uuid()
            }
            return this.vidToUUID[connection.vid]
        }
    }
}
</script>

<style scoped>
    .badge-list {
        width: fit-content;
    }

    .badge-list > .badge {
        cursor: default;
    }

    .badge-list > .badge:not(:last-child) {
        border-right: 1px solid #dee2e6
    }

    .flat-right {
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
    }

    .flat-left {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0
    }
</style>