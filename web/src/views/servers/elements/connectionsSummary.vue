<template>
    <div v-if="connectionCount == 0">
        <small class="text-muted">- No connections -</small>
    </div>
    <div v-else-if="hasValidConnections">
        <div v-if="connectionCount > 0">
            <div :id="`badge-connections-${row_index}`" class="badge-list">
                <template v-if="use_diode">
                    <span
                        v-for="(connection, index) in getConnectionList"
                        v-bind:key="index"
                        :id="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                        :class="['text-nowrap', `text-${getConnectionBadgeVariant(connection)}`]"
                    >
                        <b-icon icon="circle-fill"></b-icon>
                        {{ labelText(connection) }}
                        <b-popover
                            href="#" tabindex="0"
                            triggers="hover"
                            placement="top"
                            boundary="viewport"
                            :target="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                            :variant="getConnectionBadgeVariant(connection)"
                        >
                            <connectionState v-if="connection.connectionTest" :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                            <span v-else>
                                The Connection Test has not been done or is ongoing.
                            </span>
                        </b-popover>
                    </span>
                </template>
                <template v-else>
                    <b-badge
                        v-if="expand_issue_only && !hasError"
                        :id="`connection-popover-${row_index}-OK}`"
                        :variant="getOkConnectionSummary.variant"
                        rounded
                    >
                        {{ getOkConnectionSummary.text }}
                        <b-popover
                            v-if="getOkConnectionSummary.names.length > 0"
                            href="#" tabindex="0"
                            triggers="hover"
                            placement="top"
                            boundary="viewport"
                            :target="`connection-popover-${row_index}-OK}`"
                            :variant="getOkConnectionSummary.variant"
                        >
                            <ul class="mb-0" style="padding-inline-start: 20px;">
                                <li v-for="(name) in getOkConnectionSummary.names" :key="`ok-${name}`">
                                    {{ name }}
                                </li>
                            </ul>
                        </b-popover>
                    </b-badge>
                    <template
                        v-for="(connection, index) in getConnectionList"
                    >
                        <b-badge
                            v-if="!connection.error"
                            v-bind:key="index"
                            :id="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                            :class="getRoundedClass(index)"
                            :variant="getConnectionBadgeVariant(connection)"
                        >
                            {{ labelText(connection) }}
                            <b-popover
                                href="#" tabindex="0"
                                triggers="hover"
                                placement="top"
                                boundary="viewport"
                                :target="`connection-popover-${row_index}-${index}-${getUUID(connection)}`"
                                :variant="getConnectionBadgeVariant(connection)"
                            >
                                <connectionState v-if="connection.connectionTest" :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                                <span v-else>
                                    The Connection Test has not been done or is ongoing.
                                </span>
                            </b-popover>
                        </b-badge>
                        <b-badge
                            v-else
                            v-bind:key="index"
                            :id="`connection-popover-${row_index}-OK}`"
                            variant="danger"
                            rounded
                        >
                            {{ connection.error }}
                        </b-badge>
                    </template>
                </template>
            </div>
        </div>
        <div v-else>
            <b-badge
                v-if="expand_issue_only"
                :id="`connection-popover-${row_index}-OK}`"
                :variant="getOkConnectionSummary.variant"
                rounded
            >
                {{ getOkConnectionSummary.text }}
                <b-popover
                    href="#" tabindex="0"
                    triggers="hover"
                    placement="top"
                    boundary="viewport"
                    :target="`connection-popover-${row_index}-OK}`"
                    :variant="getOkConnectionSummary.variant"
                >
                    <ul class="mb-0" style="padding-inline-start: 20px;">
                        <li v-for="(name) in getOkConnectionSummary.names" :key="`ok-${name}`">
                            {{ name }}
                        </li>
                    </ul>
                </b-popover>
            </b-badge>
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
            vidToUUID: {},
        }
    },
    computed: {
        connectionCheckNotDone() {
            return this.connections !== undefined &&
                this.getAllConnectionsList.length > 0 &&
                this.getAllConnectionsList[0]['error'] === undefined &&
                this.getAllConnectionsList[0].Server !== undefined &&
                this.getAllConnectionsList[0]?.connectionTest?.status === undefined
        },
        hasValidConnections() {
            return this.connections !== undefined && this.getAllConnectionsList.length > 0 && this.getAllConnectionsList[0]['error'] === undefined
        },
        connectionCount() {
            return this.getAllConnectionsList.length
        },
        getConnections() {
            return this.expand_issue_only ? this.getIssueConnections : this.connections
        },
        getConnectionList() {
            return Object.values(this.getConnections)
        },
        getAllConnectionsList() {
            return this.connections === undefined ? {} : Object.values(this.connections)
        },
        getIssueConnections() {
            if (this.hasError) {
                return this.connections
            }
            return this.getAllConnectionsList.filter(connection => {
                if (connection.connectionTest !== undefined) {
                    return connection.connectionTest.status.color !== "success"
                } else {
                    return true
                }
            })
        },
        getOkConnections() {
            if (this.hasError) {
                return []
            }
            return this.getAllConnectionsList.filter(connection => {
                if (connection.connectionTest !== undefined) {
                    return connection.connectionTest.status.color === "success"
                } else {
                    return false
                }
            })
        },
        getOkConnectionSummary() {
            let summary = {}
            if (this.hasError) {
                return summary
            }
            let variant = ''
            if (this.connectionCheckNotDone) {
                variant = 'secondary'
            } else if (this.getOkConnections.length == 0 && this.getAllConnectionsList.length > 0) {
                variant = 'danger'
            } else {
                variant = 'success'
            }
            const summaryText = `${this.getOkConnections.length} / ${this.getAllConnectionsList.length} OK`
            summary = {
                names: this.getOkConnections.map(connection => (connection.Server.name != '' ? connection.Server.name : connection.Server.url)),
                text: summaryText,
                variant: variant
            }
            return summary
        },
        hasError() {
            return this.getAllConnectionsList.length == 1 && this.getAllConnectionsList[0].error !== undefined
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
            return this.text_in_badge !== "" ? this.text_in_badge : (connection.Server.name != '' ? connection.Server.name : connection.Server.url)
        },
        getUUID(connection) {
            if (this.vidToUUID[connection.vid] === undefined) {
                this.vidToUUID[connection.vid] = this.$uuid()
            }
            return this.vidToUUID[connection.vid]
        },
        getConnectionBadgeVariant(connection) {
            return connection?.connectionTest?.status?.color ?? 'secondary'
        },
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
