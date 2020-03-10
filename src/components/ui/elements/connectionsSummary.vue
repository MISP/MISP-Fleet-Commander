<template>
    <div v-if="connectionCount > 0">
        <div :id="`badge-connections-${row_index}`" class="badge-list">
            <template v-if="use_diode">
                <span
                    v-for="(connection, index) in connections"
                    v-bind:key="index"
                    :id="`connection-popover-${row_index}-${index}`"
                    :class="['text-nowrap', `text-${connection.connectionTest.status.color}`]"
                >
                    <b-icon icon="circle-fill"></b-icon>
                    {{ labelText(connection) }}
                    <b-popover
                        href="#" tabindex="0"
                        triggers="hover"
                        placement="top"
                        :target="`connection-popover-${row_index}-${index}`"
                        :variant="connection.connectionTest.status.color"
                    >
                        <connectionState :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                    </b-popover>
                </span>
            </template>
            <template v-else>
                <b-badge
                    v-for="(connection, index) in connections"
                    v-bind:key="index"
                    :id="`connection-popover-${row_index}-${index}`"
                    :class="getRoundedClass(index)"
                    :variant="connection.connectionTest.status.color"
                >
                    {{ labelText(connection) }}
                    <b-popover
                        href="#" tabindex="0"
                        triggers="hover"
                        placement="top"
                        :target="`connection-popover-${row_index}-${index}`"
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
import connectionState from "@/components/ui/elements/connectionState.vue"

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
        }
    },
    data: function() {
        return {}
    },
    computed: {
        connectionCount() {
            return this.connections.length
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