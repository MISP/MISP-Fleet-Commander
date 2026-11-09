<template>
    <div class="server-sync">
        <section class="sync-section" :aria-labelledby="`sync-links-title-${server_id}`">
            <header class="sync-head">
                <h6 :id="`sync-links-title-${server_id}`" class="sync-title">Sync links</h6>
                <span v-if="links.outgoing.length > 0" class="sync-head-note">{{ outgoingSummary }}</span>
                <button
                    v-if="links.outgoing.length > 0"
                    type="button"
                    class="btn btn-sm btn-outline-primary test-all-button"
                    :disabled="serverTesting(server_id) || testAllPending"
                    @click="testAllLinks"
                >
                    <i :class="['fas', serverTesting(server_id) || testAllPending ? 'fa-circle-notch fa-spin' : 'fa-link']" aria-hidden="true"></i>
                    {{ serverTesting(server_id) || testAllPending ? "Testing links…" : "Test all links" }}
                </button>
            </header>
            <div v-if="connectionsLoading && links.outgoing.length === 0" class="activity-state" role="status">
                <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Loading the sync links…
            </div>
            <div v-else-if="connectionsError && links.outgoing.length === 0" class="activity-state activity-error" role="alert">
                <i class="fas fa-exclamation-triangle" aria-hidden="true"></i> Could not load the sync links
            </div>
            <p v-else-if="links.outgoing.length === 0" class="sync-empty">This server has no sync links.</p>
            <template v-for="group in linkGroups">
                <h6 v-if="group.incoming" :key="`${group.key}-title`" class="sync-subtitle">From other servers of this fleet</h6>
                <ul :key="group.key" class="link-list">
                    <li
                        v-for="row in group.rows"
                        :key="row.key"
                        :class="['link-row', `level-${row.level}`, { 'is-unused': row.unused }]"
                    >
                        <span class="level-mark" :title="row.levelLabel" aria-hidden="true">
                            <i :class="['fas', row.glyph]"></i>
                        </span>
                        <div class="link-name">
                            <span class="sr-only">{{ row.levelLabel }}:</span>
                            <span class="remote-name">{{ row.name }}</span>
                            <a v-if="row.url && !group.incoming" :href="row.url" class="remote-url" :title="row.url" target="_blank" rel="noopener">{{ row.urlLabel }}</a>
                        </div>
                        <div class="link-side">
                            <span class="tested-at" :title="row.testedTitle">{{ row.testedLabel }}</span>
                            <button
                                type="button"
                                class="btn btn-outline-secondary test-button"
                                :disabled="row.testing || serverTesting(row.sourceID)"
                                :title="row.testing ? 'Testing this link…' : 'Test this link'"
                                :aria-label="group.incoming ? `Test the link from ${row.name}` : `Test the link to ${row.name}`"
                                @click="testLink(row.sourceID, row.remoteID)"
                            >
                                <i :class="['fas', row.testing ? 'fa-circle-notch fa-spin' : 'fa-redo-alt']" aria-hidden="true"></i>
                            </button>
                        </div>
                        <div class="link-meta">
                            <span v-if="row.unused" class="flow flow-off" title="Push, pull and caching are off">Unused</span>
                            <template v-else-if="group.incoming">
                                <span v-if="row.push" class="flow" title="That server pushes to this one"><i class="fas fa-arrow-down" aria-hidden="true"></i> Pushes here</span>
                                <span v-if="row.pull" class="flow" title="That server pulls from this one"><i class="fas fa-arrow-up" aria-hidden="true"></i> Pulls from here</span>
                            </template>
                            <template v-else>
                                <span v-if="row.push" class="flow"><i class="fas fa-arrow-up" aria-hidden="true"></i> Push</span>
                                <span v-if="row.pull" class="flow"><i class="fas fa-arrow-down" aria-hidden="true"></i> Pull</span>
                                <span v-if="!row.push && !row.pull" class="flow" title="Push and pull are off, but the link is used (caching or sightings)">Other</span>
                            </template>
                            <span
                                v-for="reason in row.reasons"
                                :key="reason.code + reason.message"
                                :class="['reason', `reason-${reason.level}`]"
                            >{{ reason.message }}</span>
                            <span v-if="row.versions && !group.incoming" class="meta-item" title="Local version → remote version">{{ row.versions }}</span>
                            <span v-if="row.user && !group.incoming" class="meta-item" :title="row.userTitle">
                                <i class="fas fa-user" aria-hidden="true"></i>
                                {{ row.user }}
                                <i
                                    v-if="row.syncFlag !== null"
                                    :class="['fas', row.syncFlag ? 'fa-check sync-flag-on' : 'fa-times sync-flag-off']"
                                    aria-hidden="true"
                                ></i>
                                <span v-if="row.syncFlag !== null" class="sr-only">{{ row.syncFlag ? "has" : "lacks" }} the sync permission</span>
                            </span>
                        </div>
                        <div v-if="row.testError" class="test-error" role="status">
                            <i class="fas fa-exclamation-circle" aria-hidden="true"></i> Could not test: {{ row.testError }}
                        </div>
                    </li>
                </ul>
            </template>
        </section>

        <section class="sync-section" :aria-labelledby="`sync-activity-title-${server_id}`">
            <header class="sync-head">
                <h6 :id="`sync-activity-title-${server_id}`" class="sync-title">Sync activity</h6>
                <span class="sync-head-note">{{ activityWindowLabel }}</span>
                <button
                    type="button"
                    class="btn btn-link refresh-button"
                    :disabled="activityLoading"
                    title="Read the MISP logs again"
                    aria-label="Read the sync activity again"
                    @click="loadActivity(true)"
                >
                    <i :class="['fas', 'fa-sync', { 'fa-spin': activityLoading }]" aria-hidden="true"></i>
                </button>
            </header>

            <div v-if="activityLoading && activity === null" class="activity-state" role="status">
                <i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Reading the MISP logs…
            </div>
            <div v-else-if="activityError" class="activity-state activity-error" role="alert">
                <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
                {{ activityError }}
            </div>
            <template v-else-if="activity !== null">
                <p v-if="activityRows.length === 0" class="sync-empty">
                    No pull or push in the last {{ windowText }}.
                </p>
                <div v-else class="activity-scroll">
                <table class="activity-table">
                    <thead class="sr-only">
                        <tr>
                            <th scope="col">Sync server</th>
                            <th scope="col">Direction</th>
                            <th scope="col">Runs per day</th>
                            <th scope="col">Runs</th>
                            <th scope="col">Status</th>
                        </tr>
                    </thead>
                    <tbody v-for="remote in activityRows" :key="remote.id">
                        <template v-for="(entry, index) in remote.directions">
                            <tr :key="entry.direction" :class="['activity-row', { 'is-failing': entry.failing }]">
                                <th v-if="index === 0" scope="rowgroup" :rowspan="remote.rowCount" class="activity-remote">
                                    <span class="remote-name" :title="remote.url">{{ remote.name }}</span>
                                </th>
                                <td class="activity-direction">
                                    <i :class="['fas', entry.direction === 'pull' ? 'fa-arrow-down' : 'fa-arrow-up']" aria-hidden="true"></i>
                                    <span class="direction-label">{{ entry.direction === "pull" ? "Pull" : "Push" }}</span>
                                </td>
                                <td class="activity-spark">
                                    <svg
                                        :viewBox="`0 0 ${sparkWidth} ${SPARK_HEIGHT}`"
                                        :width="`${sparkWidth / 10}em`"
                                        :height="`${SPARK_HEIGHT / 10}em`"
                                        role="img"
                                        :aria-label="entry.sparkLabel"
                                    >
                                        <g v-for="bar in entry.bars" :key="bar.index">
                                            <title>{{ bar.title }}</title>
                                            <rect :x="bar.x" y="0" :width="SPARK_BAR" :height="SPARK_HEIGHT" class="spark-hit" />
                                            <rect v-if="bar.runs === 0" :x="bar.x" :y="SPARK_HEIGHT - 1.5" :width="SPARK_BAR" height="1.5" class="spark-none" />
                                            <rect v-if="bar.okHeight > 0" :x="bar.x" :y="SPARK_HEIGHT - bar.okHeight - bar.failHeight" :width="SPARK_BAR" :height="bar.okHeight" class="spark-ok" />
                                            <rect v-if="bar.failHeight > 0" :x="bar.x" :y="SPARK_HEIGHT - bar.failHeight" :width="SPARK_BAR" :height="bar.failHeight" class="spark-failed" />
                                        </g>
                                    </svg>
                                </td>
                                <td class="activity-runs" :title="entry.transferredTitle">
                                    <template v-for="(part, partIndex) in entry.runParts">
                                        <span :key="part.key" :class="['run-part', part.className]">{{ partIndex > 0 ? "· " : "" }}{{ part.text }}</span>{{ " " }}
                                    </template>
                                </td>
                                <td class="activity-status">
                                    <span v-if="entry.failing" class="status-failing" :title="entry.lastFailureTitle">
                                        <i class="fas fa-times-circle" aria-hidden="true"></i> Failing
                                    </span>
                                    <span v-else class="status-ok" :title="entry.lastSuccessTitle">
                                        <i class="fas fa-check-circle" aria-hidden="true"></i> {{ entry.lastSuccessLabel }}
                                    </span>
                                </td>
                            </tr>
                            <tr v-if="entry.failing" :key="`${entry.direction}-detail`" class="activity-detail-row">
                                <td colspan="4" class="activity-detail">
                                    <span class="detail-error" :title="entry.lastError">
                                        Failing {{ entry.failingSince }}: {{ entry.lastError }}
                                    </span>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
                </div>
                <p class="activity-footnote" :title="activityReadTitle">{{ activityFootnote }}</p>
            </template>
        </section>
    </div>
</template>

<script>
import { mapGetters, mapState } from "vuex"
import moment from "moment"
import api from "@/api/servers"
import { LINK_LEVEL_META as LEVEL_META, agoLabel, linkTestMixin } from "@/helpers/linkHealth"
import { LINK_LEVELS as LEVEL_ORDER } from "@/store/modules/connections"

const PULL_COUNTERS = [
    ["events", "event", "events"],
    ["proposals", "proposal", "proposals"],
    ["sightings", "sighting", "sightings"],
    ["galaxy_clusters", "galaxy cluster", "galaxy clusters"],
    ["analyst_data", "analyst data", "analyst data"],
    ["collections", "collection", "collections"],
]
const PUSH_COUNTERS = [
    ["events", "event", "events"],
    ["collections", "collection", "collections"],
]
const SPARK_BAR = 6
const SPARK_GAP = 2
const SPARK_HEIGHT = 16

function plural(count, one, many) {
    return `${count} ${count === 1 ? one : many}`
}

export default {
    name: "ServerSync",
    mixins: [linkTestMixin],
    props: {
        server_id: {
            type: Number,
            required: true
        }
    },
    data() {
        return {
            activity: null,
            activityError: null,
            activityLoading: false,
            connectionsLoading: false,
            connectionsError: false,
            reloadTimer: null,
            testAllAskedAt: null,
            SPARK_BAR,
            SPARK_HEIGHT,
        }
    },
    computed: {
        ...mapState({
            servers: state => state.servers.servers,
            remote_connections: state => state.servers.remote_connections,
        }),
        // Asked for, and the server has not reported a start or an end since (workers may be busy)
        testAllPending() {
            if (this.testAllAskedAt === null) {
                return false
            }
            const state = this.server_link_test[this.server_id] || {}
            return (state.updated || 0) < this.testAllAskedAt && this.now - this.testAllAskedAt < 15 * 1000
        },
        ...mapGetters({
            linksOfServer: "connections/linksOfServer",
        }),
        links() {
            return this.linksOfServer(this.server_id)
        },
        outgoingRows() {
            return this.links.outgoing
                .map(link => this.linkRow(link, this.server_id))
                .sort((a, b) => Number(a.unused) - Number(b.unused) || a.rank - b.rank || a.name.localeCompare(b.name))
        },
        incomingRows() {
            return this.links.incoming
                .map(link => {
                    const row = this.linkRow(link, link.source.id)
                    const source = this.servers[link.source.id] || link.source
                    row.name = source.name || `Server #${link.source.id}`
                    return row
                })
                .sort((a, b) => Number(a.unused) - Number(b.unused) || a.rank - b.rank || a.name.localeCompare(b.name))
        },
        linkGroups() {
            const groups = [{ key: "outgoing", incoming: false, rows: this.outgoingRows }]
            if (this.incomingRows.length > 0) {
                groups.push({ key: "incoming", incoming: true, rows: this.incomingRows })
            }
            return groups
        },
        outgoingSummary() {
            const counts = {}
            this.outgoingRows.forEach(row => {
                const key = row.unused ? "unused" : row.level
                counts[key] = (counts[key] || 0) + 1
            })
            return [...LEVEL_ORDER, "unused"]
                .filter(key => counts[key])
                .map(key => `${counts[key]} ${key === "unused" ? "unused" : LEVEL_META[key].label.toLowerCase()}`)
                .join(" · ")
        },
        // Sync server id -> name, from this server's links
        remoteNames() {
            const names = {}
            this.links.outgoing.forEach(link => {
                const remote = link.destination.Server
                names[String(remote.id)] = remote.name || remote.url
            })
            return names
        },
        windowDays() {
            return (this.activity && this.activity.window_days) || 7
        },
        windowText() {
            return this.windowDays === 1 ? "24 hours" : `${this.windowDays} days`
        },
        activityWindowLabel() {
            return `last ${this.windowText}`
        },
        sparkWidth() {
            return this.windowDays * (SPARK_BAR + SPARK_GAP) - SPARK_GAP
        },
        activityRows() {
            if (this.activity === null || !Array.isArray(this.activity.remotes)) {
                return []
            }
            return this.activity.remotes.map(remote => {
                const directions = ["pull", "push"]
                    .filter(direction => remote[direction])
                    .map(direction => this.activityEntry(direction, remote[direction]))
                return {
                    id: remote.remote_server_id,
                    name: this.remoteNames[String(remote.remote_server_id)] || remote.url,
                    url: remote.url,
                    directions,
                    // One row per direction, plus one for the error of a failing direction
                    rowCount: directions.length + directions.filter(entry => entry.failing).length,
                    failing: directions.some(entry => entry.failing),
                }
            }).sort((a, b) => Number(b.failing) - Number(a.failing) || a.name.localeCompare(b.name))
        },
        activityFootnote() {
            if (this.activity === null) {
                return ""
            }
            const parts = ["Pulls and pushes started by this server, from its MISP logs."]
            if (this.activity.truncated) {
                parts.push("The log is too busy to read in full: some runs are missing.")
            }
            parts.push(`Read ${this.ago(this.activity.timestamp)}.`)
            return parts.join(" ")
        },
        activityReadTitle() {
            return this.activity ? `${moment.unix(this.activity.timestamp).format("LLL")}${this.activity.cached ? " (cached)" : ""}` : ""
        },
    },
    methods: {
        ago(timestamp) {
            return agoLabel(timestamp, this.now)
        },
        linkRow(link, serverID) {
            const health = link.health || {}
            const level = LEVEL_META[health.level] ? health.level : "unknown"
            const remote = link.destination.Server || {}
            const test = link.destination.connectionTest || {}
            const user = link.destination.connectionUser || {}
            const testedAt = link.tested_at || health.tested_at || null
            const remoteID = remote.id
            const testState = this.linkTestState(serverID, remoteID)
            let versions = null
            if (test.localVersion && test.remoteVersion) {
                versions = `${test.localVersion} → ${test.remoteVersion}`
            } else if (test.remoteVersion) {
                versions = `remote ${test.remoteVersion}`
            }
            const hasUser = Boolean(user.email)
            return {
                key: `${serverID}-${remoteID}`,
                remoteID,
                sourceID: serverID,
                level,
                rank: LEVEL_ORDER.indexOf(level),
                levelLabel: health.disabled ? `${LEVEL_META[level].label}, unused` : LEVEL_META[level].label,
                glyph: LEVEL_META[level].glyph,
                unused: Boolean(health.disabled),
                name: remote.name || remote.url || `#${remoteID}`,
                url: remote.url || "",
                urlLabel: (remote.url || "").replace(/^https?:\/\//, ""),
                push: health.push !== undefined ? Boolean(health.push) : Boolean(remote.push),
                pull: health.pull !== undefined ? Boolean(health.pull) : Boolean(remote.pull),
                versions,
                user: hasUser ? user.email : null,
                userTitle: hasUser ? `Remote user: ${user.email}${user.role_name ? ` (${user.role_name})` : ""}, sync permission ${user.sync_flag ? "on" : "off"}` : "",
                syncFlag: hasUser ? Boolean(user.sync_flag) : null,
                reasons: (health.reasons || []).filter(reason => reason.level !== "ok"),
                testedLabel: testedAt ? `tested ${this.ago(testedAt)}` : "never tested",
                testedTitle: testedAt ? moment.unix(testedAt).format("LLL") : "",
                testing: testState.testing,
                testError: testState.error,
            }
        },
        activityEntry(direction, data) {
            const failing = data.last_failure !== null && (data.last_success === null || data.last_failure > data.last_success)
            const maxRuns = Math.max(1, ...data.daily.map(day => day.runs))
            const days = data.daily.length
            const bars = data.daily.map((day, index) => {
                const ok = day.runs - day.failures
                const toEnd = days - index
                const when = toEnd === 1 ? "Last 24 hours" : `${toEnd - 1}–${toEnd} days ago`
                const title = day.runs === 0
                    ? `${when}: no run`
                    : `${when}: ${plural(day.runs, "run", "runs")}${day.failures ? `, ${day.failures} failed` : ""}, ${plural(day.events, "event", "events")}`
                return {
                    index,
                    x: index * (SPARK_BAR + SPARK_GAP),
                    runs: day.runs,
                    okHeight: (ok / maxRuns) * SPARK_HEIGHT,
                    failHeight: (day.failures / maxRuns) * SPARK_HEIGHT,
                    title,
                }
            })
            const counters = direction === "pull" ? PULL_COUNTERS : PUSH_COUNTERS
            const parts = counters
                .filter(([key]) => data.totals[key] > 0)
                .map(([key, one, many]) => plural(data.totals[key], one, many))
            const transferred = parts.length > 0 ? parts.join(", ") : "nothing new"
            const okRuns = data.runs - data.failures
            return {
                direction,
                failing,
                failures: data.failures,
                sparkLabel: `${plural(data.runs, "run", "runs")} in the last ${this.windowText}, ${okRuns} OK, ${data.failures} failed`,
                bars,
                runParts: [
                    { key: "runs", text: plural(data.runs, "run", "runs"), className: "" },
                    { key: "failed", text: `${data.failures} failed`, className: "runs-failed", show: data.failures > 0 },
                    { key: "events", text: plural(data.totals.events, "event", "events"), className: "", show: data.totals.events > 0 },
                ].filter(part => part.show !== false),
                transferredTitle: `${direction === "pull" ? "Pulled or updated" : "Pushed or updated"}: ${transferred}`,
                lastError: data.last_error || "no reason given",
                failingSince: data.last_success === null ? `for the whole ${this.windowText}` : `since ${this.ago(data.last_success)}`,
                lastFailureTitle: data.last_failure ? `Last failure ${moment.unix(data.last_failure).format("LLL")}` : "",
                lastSuccessLabel: data.last_success ? `OK ${this.ago(data.last_success)}` : "OK",
                lastSuccessTitle: data.last_success ? `Last success ${moment.unix(data.last_success).format("LLL")}` : "",
            }
        },
        testAllLinks() {
            this.testAllAskedAt = Date.now()
            this.now = Date.now()
            this.wsServerLinkTest(this.server_id)
        },
        loadConnections() {
            this.connectionsLoading = true
            this.connectionsError = false
            return this.$store.dispatch("connections/getConnections")
                .catch(() => { this.connectionsError = true })
                .finally(() => { this.connectionsLoading = false })
        },
        loadActivity(refresh = false) {
            this.activityLoading = true
            this.activityError = null
            return api.syncOvertime(this.server_id, refresh)
                .then(data => {
                    if (data && data.error) {
                        this.activityError = data.error
                    } else {
                        this.activity = data
                    }
                })
                .catch(error => {
                    const status = error && error.response && error.response.status
                    this.activityError = status ? `Could not read the sync activity (HTTP ${status})` : "Could not read the sync activity"
                })
                .finally(() => {
                    this.activityLoading = false
                    this.now = Date.now()
                })
        },
    },
    watch: {
        // Link tests and refreshes update the server's connections: reload the links (once they settle)
        "remote_connections": {
            handler() {
                clearTimeout(this.reloadTimer)
                this.reloadTimer = setTimeout(() => this.loadConnections(), 500)
            },
            deep: true,
        },
    },
    mounted() {
        // Mounted when the tab is first opened: the log search can be slow
        this.loadConnections()
        this.loadActivity()
    },
    beforeDestroy() {
        clearTimeout(this.reloadTimer)
    },
}
</script>

<style scoped>
.server-sync {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 1.25rem 2rem;
    padding: 0.75rem 1rem 1rem;
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.sync-section + .sync-section {
    padding-top: 1rem;
    border-top: 1px solid var(--health-rule);
}

@media (min-width: 1200px) {
    .server-sync {
        grid-template-columns: minmax(0, 7fr) minmax(0, 5fr);
    }

    .sync-section + .sync-section {
        padding-top: 0;
        padding-left: 2rem;
        border-top: 0;
        border-left: 1px solid var(--health-rule);
    }
}

.test-all-button {
    margin-left: auto;
    font-size: 0.8125rem;
    white-space: nowrap;
}

.sync-head {
    display: flex;
    align-items: baseline;
    gap: 0.6em;
    margin-bottom: 0.35em;
}

.sync-title {
    margin: 0;
    font-size: 1.1em;
    font-weight: 700;
}

.sync-subtitle {
    margin: 0.7em 0 0.3em;
    font-size: 0.95em;
    font-weight: 600;
    color: #5a6270;
}

.sync-head-note {
    color: #6c757d;
    font-size: 0.95em;
    font-variant-numeric: tabular-nums;
}

.refresh-button {
    margin-left: auto;
    padding: 0 0.3em;
    color: #6c757d;
    font-size: 0.95em;
    line-height: 1.5;
}

.refresh-button:hover,
.refresh-button:focus {
    color: var(--var-color-lapislazuli);
}

.sync-empty {
    margin: 0.2em 0 0;
    color: #6c757d;
}

.link-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.link-row {
    display: grid;
    grid-template-columns: 1.5em minmax(0, 1fr) auto;
    grid-template-areas:
        "mark name side"
        "mark meta meta"
        "mark error error";
    column-gap: 0.55em;
    align-items: center;
    padding: 0.35em 0.2em;
    border-top: 1px solid var(--health-rule);
}

.link-row:first-child {
    border-top: 0;
}

.level-mark {
    grid-area: mark;
    align-self: start;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5em;
    height: 1.5em;
    margin-top: 0.1em;
    border: 2px solid var(--link-unknown);
    border-radius: 50%;
    font-size: 0.85em;
    background: #fff;
}

.level-ok .level-mark {
    border-color: var(--link-ok);
    color: var(--health-ok-ink);
}

.level-degraded .level-mark {
    border-color: var(--link-degraded);
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
}

.level-broken .level-mark {
    border-color: var(--link-broken);
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
}

.level-unknown .level-mark {
    border-style: dashed;
    color: #5c636a;
}

.is-unused .level-mark,
.is-unused .remote-name {
    opacity: 0.6;
}


.link-name {
    grid-area: name;
    display: flex;
    align-items: baseline;
    column-gap: 0.45em;
    min-width: 0;
    line-height: 1.35;
}

.remote-name {
    flex: 0 0 auto;
    max-width: 70%;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 600;
    white-space: nowrap;
}

.activity-remote .remote-name {
    display: block;
}

.remote-url {
    flex: 0 3 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #6c757d;
    font-size: 0.9em;
}

.remote-url:hover {
    color: var(--var-color-lapislazuli);
}

.link-meta {
    grid-area: meta;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.15em 0.6em;
    margin-top: 0.1em;
    color: #5a6270;
    font-size: 0.95em;
}

.flow {
    display: inline-flex;
    align-items: center;
    gap: 0.25em;
    padding: 0 0.45em;
    border: 1px solid #ced4da;
    border-radius: 0.8em;
    background: #fff;
    font-weight: 600;
    font-size: 0.9em;
    line-height: 1.5;
}

.flow i {
    font-size: 0.85em;
}

.flow-off {
    color: #6c757d;
    border-style: dashed;
}

.meta-item {
    font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere;
}

.meta-item .fa-user {
    font-size: 0.85em;
    color: #8a929a;
}

.sync-flag-on {
    color: var(--health-ok-ink);
}

.sync-flag-off {
    color: var(--health-critical-ink);
}



.reason {
    overflow-wrap: anywhere;
}

.reason-broken {
    color: var(--health-critical-ink);
}

.reason-degraded {
    color: var(--health-warning-ink);
}

.reason-unknown {
    color: #5a6270;
}

.test-error {
    grid-area: error;
    margin-top: 0.15em;
    color: var(--health-critical-ink);
    font-size: 0.95em;
}

.link-side {
    grid-area: side;
    display: flex;
    align-items: center;
    gap: 0.4em;
}

.tested-at {
    color: #6c757d;
    font-size: 0.9em;
    white-space: nowrap;
}


.test-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.9em;
    height: 1.9em;
    padding: 0;
    font-size: 0.9em;
    line-height: 1;
    border-radius: 0.2rem;
    background: #fff;
}

.test-button:hover:not(:disabled) {
    background: #f1f3f5;
    color: var(--var-color-yankeesblue);
}

.activity-state {
    padding: 0.5em 0;
    color: #5a6270;
}

.activity-error {
    color: var(--health-critical-ink);
}

.activity-table {
    width: 100%;
    border-collapse: collapse;
}

.activity-table tbody + tbody {
    border-top: 1px solid var(--health-rule);
}

.activity-table th,
.activity-table td {
    padding: 0.3em 0.35em 0;
    vertical-align: middle;
}

.activity-remote {
    width: 22%;
    vertical-align: top !important;
    padding-top: 0.45em !important;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.activity-direction {
    white-space: nowrap;
    color: #5a6270;
}

.activity-direction i {
    font-size: 0.85em;
}

.activity-spark svg {
    display: block;
}

.spark-hit {
    fill: transparent;
}

.spark-none {
    fill: #ced4da;
}

.spark-ok {
    fill: var(--link-ok);
}

.spark-failed {
    fill: var(--link-broken);
}

.run-part {
    white-space: nowrap;
}

.activity-runs {
    font-variant-numeric: tabular-nums;
    color: #5a6270;
}

.runs-failed {
    color: var(--health-critical-ink);
}

.activity-status {
    text-align: right;
    white-space: nowrap;
}

.status-ok {
    color: var(--health-ok-ink);
}

.status-failing {
    color: var(--health-critical-ink);
    font-weight: 600;
}

.activity-detail {
    padding-top: 0 !important;
    padding-bottom: 0.2em !important;
    color: #6c757d;
    font-size: 0.92em;
}

.activity-detail-row:last-child .activity-detail {
    padding-bottom: 0.45em !important;
}

.detail-error {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: var(--health-critical-ink);
    overflow-wrap: anywhere;
}

.activity-footnote {
    margin: 0.4em 0 0;
    color: #6c757d;
    font-size: 0.9em;
}

.activity-scroll {
    overflow-x: auto;
}

@media (max-width: 575.98px) {
    .server-sync {
        padding: 0.5rem 0.5rem 0.75rem;
    }

    /* Arrow only, the word stays for screen readers */
    .link-name .remote-url {
        display: none;
    }

    .link-name .remote-name {
        max-width: 100%;
    }

    .direction-label {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
    }

    .activity-table {
        min-width: 22rem;
    }
}
</style>
