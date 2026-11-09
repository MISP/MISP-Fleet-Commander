<template>
    <div v-if="connectionCount == 0">
        <small class="text-muted">- No connections -</small>
    </div>
    <div v-else-if="hasValidConnections">
        <div :id="`badge-connections-${row_index}`" class="badge-list">
            <template v-if="use_diode">
                <span
                    v-for="(link, index) in diodes"
                    :key="index"
                    :id="`${idPrefix}-diode-${index}`"
                    :class="['text-nowrap', link.textClass]"
                >
                    <b-icon icon="circle-fill"></b-icon>
                    {{ link.label }}
                    <b-popover
                        triggers="hover"
                        placement="top"
                        boundary="viewport"
                        :target="`${idPrefix}-diode-${index}`"
                        :variant="link.popoverVariant"
                    >
                        <div v-if="link.healthText" class="mb-1"><strong>{{ link.healthText }}</strong></div>
                        <connectionState v-if="link.connection.connectionTest" :connection="link.connection.connectionTest" :user="link.connection.connectionUser"></connectionState>
                        <span v-else>
                            The Connection Test has not been done or is ongoing.
                        </span>
                    </b-popover>
                </span>
            </template>
            <template v-else>
                <b-badge
                    v-show="summary.ok.shown"
                    :id="`${idPrefix}-ok`"
                    :variant="summary.ok.variant"
                    rounded
                >
                    {{ summary.ok.count }} / {{ connectionCount }} OK
                    <b-popover
                        v-if="summary.ok.names.length > 0"
                        triggers="hover"
                        placement="top"
                        boundary="viewport"
                        :target="`${idPrefix}-ok`"
                    >
                        <ul class="mb-0 summary-list">
                            <li v-for="name in summary.ok.names" :key="`ok-${name}`">{{ name }}</li>
                        </ul>
                    </b-popover>
                </b-badge>
                <b-badge
                    v-for="(group, index) in summary.groups"
                    :key="group.key"
                    :id="`${idPrefix}-group-${index}`"
                    :variant="group.badge.variant"
                    :class="['rounded', group.badge.class]"
                >
                    <span>{{ group.label }} <span class="group-count">{{ group.items.length }}</span></span>
                    <b-popover
                        triggers="hover"
                        placement="right"
                        boundary="viewport"
                        :target="`${idPrefix}-group-${index}`"
                    >
                        <h6 class="mb-1">{{ group.heading }}</h6>
                        <ul class="mb-0 summary-list">
                            <li v-for="(item, itemIndex) in group.items" :key="itemIndex">
                                {{ item.name }}
                                <div v-if="item.detail" class="text-muted small">{{ item.detail }}</div>
                            </li>
                        </ul>
                    </b-popover>
                </b-badge>
            </template>
        </div>
    </div>
</template>

<script>
import connectionState from "@/views/servers/elements/connectionState.vue"
import { LINK_LEVEL_META } from "@/helpers/linkHealth"
import { healthCellMixin, toneBadge, toneTextClass } from "@/helpers/healthCells"

// Groups of the summary, in this order. `unused` = configured, but push, pull and caching are off
const GROUP_ORDER = ["broken", "degraded", "unknown", "unused", "unchecked"]
const GROUP_LABELS = {
    broken: LINK_LEVEL_META.broken.label,
    degraded: LINK_LEVEL_META.degraded.label,
    unknown: LINK_LEVEL_META.unknown.label,
    unused: "Unused",
    unchecked: "Not checked",
}
const PENDING = "Connection Test Pending"

function linkName(connection) {
    return connection.Server.name != "" ? connection.Server.name : connection.Server.url
}

export default {
    name: "connectionsSummary",
    mixins: [healthCellMixin],
    components: {
        connectionState
    },
    props: {
        connections: {},
        // The server these links belong to: with it, colours come from its sync link issues
        server_id: {
            type: Number,
            default: null,
        },
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
    },
    computed: {
        idPrefix() {
            return `connection-popover-${this._uid}-${this.row_index}`
        },
        allConnections() {
            return this.connections === undefined || this.connections === null ? [] : Object.values(this.connections)
        },
        connectionCount() {
            return this.allConnections.length
        },
        hasValidConnections() {
            return this.connectionCount > 0 && this.allConnections[0].error === undefined
        },
        connectionCheckNotDone() {
            return this.hasValidConnections &&
                this.allConnections[0].Server !== undefined &&
                this.allConnections[0]?.connectionTest?.status === undefined
        },
        usesHealth() {
            return this.healthTone(this.server_id, "sync_link") !== null
        },
        // Per link: its health (from the server's sync link issue), or what MISP's connection test says
        links() {
            return this.allConnections.map((connection) => {
                if (!this.usesHealth) {
                    const status = connection?.connectionTest?.status
                    const color = status?.color ?? "secondary"
                    return {
                        connection,
                        ok: color === "success",
                        group: status?.message !== undefined ? status.message : PENDING,
                        variant: color,
                        textClass: `text-${color}`,
                        detail: "",
                    }
                }
                const tone = this.healthTone(this.server_id, "sync_link", { subject: connection.Server.id })
                const issue = tone.issues[0]
                let level = tone.level === "unchecked" ? "unchecked" : "ok"
                if (issue) {
                    level = issue.evidence && issue.evidence.disabled ? "unused" : ((issue.evidence && issue.evidence.level) || "unknown")
                }
                const badge = toneBadge(tone, "success")
                return {
                    connection,
                    ok: level === "ok",
                    level,
                    acked: tone.acked,
                    group: `${level}${tone.acked ? "-acked" : ""}`,
                    variant: badge.variant,
                    badgeClass: badge.class,
                    textClass: toneTextClass(tone),
                    detail: issue ? issue.detail : "",
                }
            })
        },
        summary() {
            const okLinks = this.links.filter(link => link.ok)
            const groups = {}
            this.links.filter(link => !link.ok).forEach((link) => {
                if (groups[link.group] === undefined) {
                    groups[link.group] = this.newGroup(link)
                }
                groups[link.group].items.push({ name: linkName(link.connection), detail: link.detail })
            })
            let okVariant = "success"
            if (this.usesHealth) {
                okVariant = okLinks.length > 0 ? "success" : "light"
            } else if (this.connectionCheckNotDone) {
                okVariant = "secondary"
            } else if (okLinks.length == 0) {
                okVariant = "danger"
            }
            return {
                ok: {
                    count: okLinks.length,
                    names: okLinks.map(link => linkName(link.connection)),
                    variant: okVariant,
                    shown: this.usesHealth || !this.connectionCheckNotDone,
                },
                groups: Object.values(groups).sort((a, b) => a.rank - b.rank),
            }
        },
        diodes() {
            return this.links.map(link => ({
                connection: link.connection,
                label: this.text_in_badge !== "" ? this.text_in_badge : linkName(link.connection),
                textClass: link.textClass,
                popoverVariant: this.usesHealth ? (link.ok ? "success" : link.variant) : link.variant,
                healthText: this.usesHealth && !link.ok
                    ? `${GROUP_LABELS[link.level]}${link.acked ? " (acknowledged)" : ""}${link.detail ? `: ${link.detail}` : ""}`
                    : "",
            }))
        },
    },
    methods: {
        newGroup(link) {
            if (!this.usesHealth) {
                return { key: link.group, label: link.group, heading: link.group, badge: { variant: link.variant, class: "" }, rank: 0, items: [] }
            }
            const label = GROUP_LABELS[link.level]
            return {
                key: link.group,
                label,
                heading: link.acked ? `${label} (acknowledged)` : label,
                badge: { variant: link.variant, class: link.badgeClass },
                rank: GROUP_ORDER.indexOf(link.level) + (link.acked ? GROUP_ORDER.length : 0),
                items: [],
            }
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
        margin-right: 0.2rem;
    }

    .group-count {
        display: inline-block;
        font-size: 80%;
        padding: 0.1em 0.4em;
        margin-left: 0.15em;
        border-radius: 0.25em;
        background-color: rgba(255, 255, 255, 0.75);
        color: #343a40;
    }

    .health-acked-badge .group-count {
        background-color: rgba(0, 0, 0, 0.06);
        color: inherit;
    }

    .summary-list {
        padding-inline-start: 20px;
    }
</style>
