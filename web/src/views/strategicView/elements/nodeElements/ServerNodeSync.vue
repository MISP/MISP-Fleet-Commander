<template>
    <div class="node-sync">
        <p v-if="rows.length === 0" class="sync-empty">This server has no sync links.</p>
        <template v-else>
            <div class="sync-counts" :aria-label="countsLabel">
                <span
                    v-for="count in counts"
                    :key="count.key"
                    :class="['count-chip', `count-${count.key}`]"
                >
                    <i v-if="count.glyph" :class="['fas', count.glyph]" aria-hidden="true"></i>
                    {{ count.count }} {{ count.label }}
                </span>
            </div>
            <ul v-if="problems.length > 0" class="problem-list">
                <li
                    v-for="row in shownProblems"
                    :key="row.key"
                    :class="['problem', `level-${row.level}`]"
                    :title="row.reasonsText"
                >
                    <i :class="['fas', row.glyph, 'problem-glyph']" aria-hidden="true"></i>
                    <span class="sr-only">{{ row.levelLabel }}:</span>
                    <span class="problem-name">{{ row.name }}</span>
                    <span class="problem-reason">{{ row.reason }}</span>
                </li>
                <li v-if="problems.length > shownProblems.length" class="problem-more">
                    and {{ problems.length - shownProblems.length }} more
                </li>
            </ul>
            <p v-else class="sync-ok">
                <i class="fas fa-check-circle" aria-hidden="true"></i>
                {{ inUseCount === 1 ? "The link in use is OK" : `All ${inUseCount} links in use are OK` }}
            </p>
        </template>
        <div class="sync-actions">
            <button
                v-if="rows.length > 0"
                type="button"
                class="btn btn-outline-primary test-button"
                :disabled="testing"
                @click="testLinks"
            >
                <i :class="['fas', testing ? 'fa-circle-notch fa-spin' : 'fa-link']" aria-hidden="true"></i>
                {{ testing ? "Testing…" : "Test links" }}
            </button>
            <router-link :to="detailsLink" class="details-link">
                Details and activity <i class="fas fa-arrow-right" aria-hidden="true"></i>
            </router-link>
        </div>
        <div v-if="testError" class="test-error" role="status">
            <i class="fas fa-exclamation-circle" aria-hidden="true"></i> Could not test: {{ testError }}
        </div>
    </div>
</template>

<script>
import { mapGetters, mapState } from "vuex"
import { websocketMixin } from "@/helpers/websocketMixin"

const LEVEL_META = {
    broken: { label: "broken", glyph: "fa-times" },
    degraded: { label: "degraded", glyph: "fa-exclamation" },
    unknown: { label: "not tested", glyph: "fa-question" },
    ok: { label: "OK", glyph: "fa-check" },
}
const LEVEL_ORDER = ["broken", "degraded", "unknown", "ok"]
const MAX_PROBLEMS = 3
// Past this without news from the workers, the button is usable again
const TEST_GIVE_UP_MS = 15 * 1000

// Compact sync summary for the Strategic View's server card; the full view is the server page's Synchronization tab
export default {
    name: "ServerNodeSync",
    mixins: [websocketMixin],
    props: {
        server_id: {
            type: Number,
            required: true
        }
    },
    data() {
        return {
            testAskedAt: null,
            now: Date.now(),
            ticker: null,
        }
    },
    computed: {
        ...mapState({
            server_link_test: state => state.servers.server_link_test,
        }),
        ...mapGetters({
            linksOfServer: "connections/linksOfServer",
        }),
        rows() {
            return this.linksOfServer(this.server_id).outgoing.map(link => {
                const health = link.health || {}
                const level = LEVEL_META[health.level] ? health.level : "unknown"
                const remote = link.destination.Server || {}
                const reasons = (health.reasons || []).filter(reason => reason.level !== "ok").map(reason => reason.message)
                return {
                    key: `${this.server_id}-${remote.id}`,
                    level,
                    levelLabel: LEVEL_META[level].label,
                    glyph: LEVEL_META[level].glyph,
                    unused: Boolean(health.disabled),
                    name: remote.name || remote.url || `#${remote.id}`,
                    reason: reasons[0] || (level === "unknown" ? "Not tested yet" : ""),
                    reasonsText: reasons.join("\n"),
                }
            })
        },
        // Links in use that are not OK, most severe first
        problems() {
            return this.rows
                .filter(row => !row.unused && row.level !== "ok")
                .sort((a, b) => LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level) || a.name.localeCompare(b.name))
        },
        shownProblems() {
            return this.problems.slice(0, MAX_PROBLEMS)
        },
        inUseCount() {
            return this.rows.filter(row => !row.unused).length
        },
        counts() {
            const counts = LEVEL_ORDER
                .map(level => ({
                    key: level,
                    label: LEVEL_META[level].label,
                    glyph: LEVEL_META[level].glyph,
                    count: this.rows.filter(row => !row.unused && row.level === level).length,
                }))
            const unused = this.rows.filter(row => row.unused).length
            counts.push({ key: "unused", label: "unused", glyph: null, count: unused })
            return counts.filter(count => count.count > 0)
        },
        countsLabel() {
            return `Sync links: ${this.counts.map(count => `${count.count} ${count.label}`).join(", ")}`
        },
        linkTestState() {
            return this.server_link_test[this.server_id] || {}
        },
        testing() {
            if (this.linkTestState.testing) {
                return true
            }
            // Asked, and the workers have not reported on this server since
            return this.testAskedAt !== null && (this.linkTestState.updated || 0) < this.testAskedAt && this.now - this.testAskedAt < TEST_GIVE_UP_MS
        },
        testError() {
            const reported = this.testAskedAt !== null && (this.linkTestState.updated || 0) >= this.testAskedAt
            return reported && !this.linkTestState.testing ? this.linkTestState.error || null : null
        },
        detailsLink() {
            return { name: "servers.view", params: { server_id: this.server_id }, query: { tab: "sync" } }
        },
    },
    methods: {
        testLinks() {
            this.testAskedAt = Date.now()
            this.now = Date.now()
            this.wsServerLinkTest(this.server_id)
        },
    },
    mounted() {
        this.ticker = setInterval(() => { this.now = Date.now() }, 5 * 1000)
    },
    beforeDestroy() {
        clearInterval(this.ticker)
    },
}
</script>

<style scoped>
.node-sync {
    min-width: 26em;
    padding: 0 0.6em;
    color: var(--var-color-yankeesblue);
}

.sync-empty,
.sync-ok {
    margin: 0 0 0.4em;
    color: #5a6270;
}

.sync-ok i {
    color: var(--health-ok);
}

.sync-counts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3em;
    margin-bottom: 0.45em;
}

.count-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    padding: 0 0.55em;
    border: 1px solid var(--link-unknown);
    border-radius: 0.8em;
    background: #f1f3f5;
    color: #5c636a;
    font-weight: 600;
    font-size: 0.95em;
    line-height: 1.6;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.count-chip i {
    font-size: 0.85em;
}

.count-broken {
    color: var(--health-critical-ink);
    background: var(--health-critical-tint);
    border-color: var(--link-broken);
}

.count-degraded {
    color: var(--health-warning-ink);
    background: var(--health-warning-tint);
    border-color: var(--link-degraded);
}

.count-unknown {
    border-style: dashed;
}

.count-ok {
    color: var(--health-ok-ink);
    background: #eef8f2;
    border-color: var(--link-ok);
}

.count-unused {
    border-style: dashed;
    font-weight: 400;
}

.problem-list {
    list-style: none;
    margin: 0 0 0.4em;
    padding: 0;
}

.problem {
    display: flex;
    align-items: baseline;
    gap: 0.4em;
    min-width: 0;
    padding: 0.12em 0;
    line-height: 1.4;
}

.problem-glyph {
    flex: none;
    width: 1em;
    text-align: center;
    font-size: 0.9em;
}

.level-broken .problem-glyph {
    color: var(--health-critical-ink);
}

.level-degraded .problem-glyph {
    color: var(--health-warning-ink);
}

.level-unknown .problem-glyph {
    color: #6c757d;
}

.problem-name {
    flex: none;
    max-width: 45%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 600;
}

.problem-reason {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #5a6270;
}

.problem-more {
    padding-left: 1.4em;
    color: #6c757d;
}

.sync-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5em;
    padding-top: 0.4em;
    border-top: 1px solid var(--health-rule);
}

.test-button {
    padding: 0.1em 0.6em;
    font-size: 0.95em;
    line-height: 1.5;
    border-radius: 0.2rem;
    white-space: nowrap;
}

.details-link {
    margin-left: auto;
    font-weight: 600;
    white-space: nowrap;
}

.details-link i {
    font-size: 0.85em;
}

.test-error {
    margin-top: 0.3em;
    color: var(--health-critical-ink);
}
</style>
