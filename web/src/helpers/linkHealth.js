import { mapState } from "vuex"
import moment from "moment"
import { LINK_LEVELS } from "@/store/modules/connections"
import { websocketMixin } from "@/helpers/websocketMixin"

// How each link level is named and drawn (the graph uses the same glyphs)
export const LINK_LEVEL_META = {
    broken: { label: "Broken", glyph: "fa-times" },
    degraded: { label: "Degraded", glyph: "fa-exclamation" },
    unknown: { label: "Not tested", glyph: "fa-question" },
    ok: { label: "OK", glyph: "fa-check" },
}

// Reasons about the MISP versions at both ends of a link
const VERSION_REASON_CODES = ["incompatible", "pull_only", "compatibility", "version_mismatch", "remote_outdated"]

export function linkLevel(link) {
    const level = link && link.health && link.health.level
    return LINK_LEVEL_META[level] ? level : "unknown"
}

export function linkIsUnused(link) {
    return Boolean(link && link.health && link.health.disabled)
}

// Sort rank: most severe first, links in use before unused ones
export function linkHealthRank(link) {
    return (linkIsUnused(link) ? LINK_LEVELS.length : 0) + LINK_LEVELS.indexOf(linkLevel(link))
}

// Why the link is not OK
export function linkReasons(link) {
    return ((link && link.health && link.health.reasons) || []).filter(reason => reason.level !== "ok")
}

export function linkVersionReasons(link) {
    return linkReasons(link).filter(reason => VERSION_REASON_CODES.includes(reason.code))
}

export function linkTestedAt(link) {
    return (link && (link.tested_at || (link.health && link.health.tested_at))) || null
}

// -1, 0 or 1. Versions such as "2.5.51" or "3.0.0"; anything else sorts after them
export function compareVersions(a, b) {
    if (!a || !b) {
        return a ? -1 : (b ? 1 : 0)
    }
    return String(a).localeCompare(String(b), undefined, { numeric: true })
}

export function agoLabel(timestamp, now) {
    const seconds = Math.max(0, Math.round(now / 1000 - timestamp))
    return seconds < 60 ? "just now" : `${moment.duration(seconds, "seconds").humanize()} ago`
}

// A single-link test reports back through its server's link test state; past this, the button is usable again
const TEST_GIVE_UP_MS = 2 * 60 * 1000

// Tests one sync link at a time and follows each test until its server reports back.
// `now` ticks so that relative times ("tested 2 minutes ago") stay current
export const linkTestMixin = {
    mixins: [websocketMixin],
    data() {
        return {
            now: Date.now(),
            linkTestTicker: null,
            // "<server_id>-<remote_id>" -> time the test was asked for
            testsAsked: {},
        }
    },
    computed: {
        ...mapState({
            server_link_test: state => state.servers.server_link_test,
        }),
    },
    methods: {
        serverTesting(serverID) {
            return Boolean(this.server_link_test[serverID] && this.server_link_test[serverID].testing)
        },
        // `testing` while the test asked for this link runs (or has not started yet); `error` once it could not run
        linkTestState(serverID, remoteID) {
            const askedAt = this.testsAsked[`${serverID}-${remoteID}`]
            if (askedAt === undefined) {
                return { testing: false, error: null }
            }
            const state = this.server_link_test[serverID] || {}
            const reported = (state.updated || 0) >= askedAt
            if (reported && !state.testing) {
                return { testing: false, error: state.error || null }
            }
            return { testing: this.now - askedAt < TEST_GIVE_UP_MS, error: null }
        },
        testLink(serverID, remoteID) {
            this.$set(this.testsAsked, `${serverID}-${remoteID}`, Date.now())
            this.now = Date.now()
            this.wsServerLinkTest(serverID, Number(remoteID))
        },
    },
    mounted() {
        this.linkTestTicker = setInterval(() => { this.now = Date.now() }, 15 * 1000)
    },
    beforeDestroy() {
        clearInterval(this.linkTestTicker)
    },
}
