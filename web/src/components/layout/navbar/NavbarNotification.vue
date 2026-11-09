<template>
    <div>
        <b-nav-item-dropdown right menu-class="notification-menu">
            <template #button-content>
                <iconButton
                    style="display: inline-block !important"
                    text="Notifications"
                    icon="bell"
                    :title="buttonLabel"
                    :tight="true"
                >
                    <span
                        v-if="attentionCount > 0"
                        :class="['notification-badge', 'ml-1', counts.critical > 0 ? 'sev-critical' : 'sev-warning']"
                    >{{ attentionCount > 99 ? "99+" : attentionCount }}</span>
                    <i
                        v-if="refreshingServers.length > 0"
                        class="fas fa-circle-notch fa-spin notification-spinner ml-1"
                        aria-hidden="true"
                    ></i>
                    <span class="sr-only">{{ buttonLabel }}</span>
                </iconButton>
            </template>

            <b-dropdown-header class="notification-header">
                <span>Needs attention</span>
                <span v-if="loaded && attentionCount > 0" class="notification-header-counts">{{ countsLabel }}</span>
            </b-dropdown-header>

            <b-dropdown-text v-if="!loaded" class="notification-empty">
                <template v-if="loading"><b-spinner small class="mr-2"></b-spinner>Checking your servers</template>
                <template v-else>Health could not be loaded</template>
            </b-dropdown-text>
            <b-dropdown-text v-else-if="topIssues.length === 0" class="notification-empty">
                <i class="fas fa-check mr-2 notification-ok" aria-hidden="true"></i>No issues need attention
            </b-dropdown-text>
            <b-dropdown-item
                v-for="issue in topIssues"
                v-else
                :key="issue.id"
                :to="issueLink(issue)"
                link-class="notification-issue"
            >
                <i :class="[severityMeta[issue.severity].icon, 'fa-fw', 'notification-issue-icon', `sev-${issue.severity}`]" :title="severityMeta[issue.severity].label"></i>
                <span class="notification-issue-main">
                    <span class="notification-issue-title">{{ issue.title }}</span>
                    <span class="notification-issue-server">{{ issue.server_name }} · {{ issue.fleet_name }}</span>
                </span>
            </b-dropdown-item>

            <template v-if="refreshingServers.length > 0">
                <b-dropdown-divider></b-dropdown-divider>
                <b-dropdown-header>Refreshing</b-dropdown-header>
                <b-dropdown-text
                    v-for="server in refreshingServers"
                    :key="`notif-${server.id}`"
                    class="notification-refreshing"
                >
                    <i class="fas fa-circle-notch fa-spin fa-fw mr-1 text-secondary" aria-hidden="true"></i>{{ server.name }}
                </b-dropdown-text>
            </template>

            <b-dropdown-divider></b-dropdown-divider>
            <b-dropdown-item :to="{ name: 'attention' }" link-class="notification-view-all">
                {{ activeCount > 0 ? `View all ${activeCount} ${activeCount === 1 ? "issue" : "issues"}` : "Open Needs attention" }}
                <i class="fas fa-arrow-right ml-1" aria-hidden="true"></i>
            </b-dropdown-item>
        </b-nav-item-dropdown>
    </div>
</template>

<script>
import { mapState, mapGetters } from "vuex"
import iconButton from "@/components/ui/elements/iconButton.vue"
import { SEVERITY_META, countsText } from "@/views/attention/healthLabels"

const SHOWN_ISSUES = 5

export default {
    name: "NavbarNotification",
    components: {
        iconButton,
    },
    data: function () {
        return {
            severityMeta: SEVERITY_META,
            timerWorkersHealthCheck: null,
        }
    },
    computed: {
        ...mapState({
            server_refresh_enqueued: state => state.servers.server_refresh_enqueued,
            loaded: state => state.health.loaded,
            loading: state => state.health.loading,
        }),
        ...mapGetters({
            serverList: "servers/getServerList",
            counts: "health/counts",
            attentionCount: "health/attentionCount",
            activeIssues: "health/activeIssues",
            topIssuesGetter: "health/topIssues",
        }),
        // Same rule as the sidebar badge: info issues do not need attention
        topIssues() {
            return this.topIssuesGetter(SHOWN_ISSUES).filter(issue => issue.severity !== "info")
        },
        activeCount() {
            return this.activeIssues.length
        },
        countsLabel() {
            return countsText({ critical: this.counts.critical, warning: this.counts.warning, info: 0 })
        },
        refreshingServers() {
            return this.serverList.filter((server) => {
                return this.server_refresh_enqueued[server.id]
            })
        },
        buttonLabel() {
            const parts = ["Notifications"]
            if (this.attentionCount > 0) {
                parts.push(`${this.countsLabel} need attention`)
            }
            if (this.refreshingServers.length > 0) {
                parts.push(`refreshing ${this.refreshingServers.length} ${this.refreshingServers.length === 1 ? "server" : "servers"}`)
            }
            return parts.join(", ")
        },
    },
    methods: {
        issueLink(issue) {
            return { name: "attention", query: { server_id: String(issue.server_id) } }
        },
        async runWorkerHealthCheck() {
            try {
                await this.$socket.timeout(3000).emit('workers_health_check')
            } catch (err) {
                console.log(err)
            }
        },
        registerWorkersHealthCheck() {
            this.timerWorkersHealthCheck = setInterval(() => {
                this.runWorkerHealthCheck()
            }, 10000)
        }
    },
    mounted() {
        this.$store.dispatch("health/init")
        this.runWorkerHealthCheck()
        this.registerWorkersHealthCheck()
    },
    beforeDestroy() {
        clearInterval(this.timerWorkersHealthCheck)
    },
}
</script>

<style scoped>
.notification-badge {
    display: inline-block;
    vertical-align: text-bottom;
    min-width: 1.15rem;
    height: 1.15rem;
    padding: 0 0.3rem;
    border-radius: 0.6rem;
    font-size: 0.7rem;
    font-weight: 700;
    line-height: 1.15rem;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

.notification-badge.sev-critical {
    background: var(--health-critical);
    color: #fff;
}

.notification-badge.sev-warning {
    background: var(--health-warning);
    color: #212529;
}

.notification-spinner {
    font-size: 0.8em;
    opacity: 0.8;
}
</style>

<style>
/* Dropdown menu content: b-dropdown-* render their own roots, so scoped styles would not reach them */
.notification-menu {
    width: 22rem;
    max-width: calc(100vw - 1rem);
    padding-bottom: 0.25rem;
}

.notification-menu .notification-header .dropdown-header,
.notification-menu header.notification-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
}

.notification-header-counts {
    text-transform: none;
    font-weight: 400;
}

.notification-menu .notification-empty .b-dropdown-text,
.notification-menu .notification-refreshing .b-dropdown-text {
    font-size: 0.875rem;
    color: #6c757d;
}

.notification-menu .notification-refreshing .b-dropdown-text {
    padding-top: 0.15rem;
    padding-bottom: 0.15rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.notification-ok {
    color: var(--health-ok-ink);
}

.notification-menu .notification-issue {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding-top: 0.4rem;
    padding-bottom: 0.4rem;
    white-space: normal;
}

.notification-issue-icon {
    margin-top: 0.2rem;
}

.notification-issue-icon.sev-critical { color: var(--health-critical-ink); }
.notification-issue-icon.sev-warning { color: var(--health-warning-ink); }
.notification-issue-icon.sev-info { color: var(--health-info-ink); }

.notification-issue-main {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.notification-issue-title {
    font-size: 0.875rem;
    line-height: 1.3;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.notification-issue-server {
    font-size: 0.75rem;
    color: #6c757d;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.notification-menu .notification-view-all {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--var-color-lapislazuli);
}
</style>
