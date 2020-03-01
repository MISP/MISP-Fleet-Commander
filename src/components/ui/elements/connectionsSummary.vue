<template>
    <div v-if="connectionCount > 0">
        <div :id="`badge-connections-${server_id}`" class="badge-list">
            <b-badge
                v-for="(connection, index) in connections"
                v-bind:key="index"
                :id="`connection-popover-${index}`"
                :class="getRoundedClass(index)"
                :variant="connection.connectionTest.status_color"
            >
                {{ connection.Server.name }}
                <b-popover
                    href="#" tabindex="0"
                    triggers="hover"
                    placement="top"
                    :target="`connection-popover-${index}`"
                    :variant="connection.connectionTest.status_color"
                >
                    <connectionState :connection="connection.connectionTest" :user="connection.connectionUser"></connectionState>
                </b-popover>
            </b-badge>
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
        server_id: {
            type: Number,
            required: true
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