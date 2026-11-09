<template>
    <section class="network-legend shadow-sm" :class="{ collapsed: collapsed }" aria-label="Legend">
        <button
            type="button"
            class="legend-toggle"
            :aria-expanded="collapsed ? 'false' : 'true'"
            aria-controls="network-legend-body"
            @click="toggle"
        >
            <i class="fas fa-shapes" aria-hidden="true"></i>
            <span>Legend</span>
            <i :class="['fas', collapsed ? 'fa-chevron-up' : 'fa-chevron-down', 'legend-chevron']" aria-hidden="true"></i>
        </button>
        <div v-show="!collapsed" id="network-legend-body" class="legend-body">
            <h3 class="legend-title">Sync links</h3>
            <ul class="legend-list legend-links">
                <li v-for="item in linkItems" :key="item.key" :title="item.title">
                    <svg class="legend-swatch" width="34" height="10" viewBox="0 0 34 10" aria-hidden="true">
                        <line
                            x1="3" y1="5" x2="25" y2="5"
                            :stroke="item.color"
                            :stroke-width="item.width"
                            :stroke-dasharray="item.dash"
                            :opacity="item.opacity"
                            stroke-linecap="round"
                        />
                        <path d="M 25 1 L 33 5 L 25 9 z" :fill="item.color" :opacity="item.opacity" />
                    </svg>
                    <span>{{ item.label }}</span>
                    <i
                        v-if="item.glyph"
                        :class="['fas', item.glyph, 'legend-level-glyph', `legend-level-${item.key}`]"
                        title="Also shown in the link's badge"
                        aria-hidden="true"
                    ></i>
                </li>
            </ul>
            <h3 class="legend-title">Link badge</h3>
            <ul class="legend-list legend-columns">
                <li><span class="legend-glyph legend-fa">&#xf062;</span><span>Push</span></li>
                <li><span class="legend-glyph legend-fa">&#xf063;</span><span>Pull</span></li>
                <li title="Push, with sightings, galaxy clusters and analyst data">
                    <span class="legend-glyph legend-fa">&#xf35b;</span><span>Push all</span>
                </li>
                <li title="Pull, with galaxy clusters and analyst data">
                    <span class="legend-glyph legend-fa">&#xf358;</span><span>Pull all</span>
                </li>
                <li><span class="legend-glyph"><i class="fas fa-filter text-muted"></i></span><span>Rules</span></li>
                <li title="The remote belongs to the same organisation">
                    <span class="legend-glyph"><i class="fas fa-building text-muted"></i></span><span>Internal</span>
                </li>
            </ul>
            <h3 class="legend-title">Servers</h3>
            <ul class="legend-list legend-columns">
                <li><span class="legend-node"></span><span>Managed</span></li>
                <li title="A remote this fleet does not manage"><span class="legend-node legend-node-remote"></span><span>Remote</span></li>
            </ul>
            <p class="legend-hint">Hover a link for the reasons of its health.</p>
        </div>
    </section>
</template>

<script>
const STORAGE_KEY = "mfc.strategicView.legendCollapsed"

export default {
    name: "NetworkLegend",
    data() {
        return {
            collapsed: false,
            linkItems: [
                { key: "ok", label: "OK", color: "var(--link-ok)", width: 4, dash: null, opacity: 1 },
                { key: "degraded", label: "Degraded", color: "var(--link-degraded)", width: 4, dash: null, opacity: 1, glyph: "fa-exclamation" },
                { key: "broken", label: "Broken", color: "var(--link-broken)", width: 4, dash: null, opacity: 1, glyph: "fa-times" },
                { key: "unknown", label: "Not tested", color: "var(--link-unknown)", width: 4, dash: "5 5", opacity: 1, glyph: "fa-question" },
                { key: "unused", label: "Unused", title: "Push, pull and caching are off. Coloured by its health", color: "var(--link-ok)", width: 2.5, dash: null, opacity: 0.45 },
            ],
        }
    },
    created() {
        try {
            this.collapsed = window.localStorage.getItem(STORAGE_KEY) === "1"
        } catch (e) {
            this.collapsed = false
        }
    },
    methods: {
        toggle() {
            this.collapsed = !this.collapsed
            try {
                window.localStorage.setItem(STORAGE_KEY, this.collapsed ? "1" : "0")
            } catch (e) {
                // Not remembered, no harm
            }
        },
    },
}
</script>

<style scoped>
.network-legend {
    width: 14.5rem;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(0, 0, 0, 0.125);
    border-radius: 0.35rem;
    font-size: 0.8rem;
    color: #343a40;
}

.network-legend.collapsed {
    width: auto;
}

.legend-toggle {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    padding: 0.35rem 0.6rem;
    border: 0;
    background: transparent;
    font-weight: 600;
    color: inherit;
    text-align: left;
}

.legend-toggle:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
    border-radius: 0.35rem;
}

.legend-chevron {
    margin-left: auto;
    font-size: 0.7em;
    opacity: 0.6;
}

.legend-body {
    padding: 0 0.6rem 0.5rem;
    border-top: 1px solid var(--health-rule);
}

.legend-title {
    margin: 0.5rem 0 0.25rem;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #6c757d;
}

.legend-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.legend-list li {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    line-height: 1.6;
    white-space: nowrap;
}

.legend-links .legend-swatch {
    width: 26px;
}

.legend-columns,
.legend-links {
    display: grid;
    grid-template-columns: 1fr 1fr;
    column-gap: 0.5rem;
}

.legend-swatch {
    flex: none;
}

.legend-glyph {
    display: inline-flex;
    justify-content: center;
    width: 1.1rem;
    flex: none;
}

.legend-fa {
    font-family: FontAwesome;
}

.legend-node {
    flex: none;
    width: 1.6rem;
    height: 0.9rem;
    border: 1px solid #adb5bd;
    border-radius: 0.2rem;
    background: white;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
}

.legend-node-remote {
    border-style: dashed;
    border-radius: 0.45rem;
    background: rgba(0, 0, 0, 0.02);
    box-shadow: none;
}

.legend-level-glyph {
    font-size: 0.7rem;
}

.legend-level-degraded { color: var(--link-degraded); }
.legend-level-broken { color: var(--link-broken); }
.legend-level-unknown { color: #6c757d; }

.legend-hint {
    margin: 0.45rem 0 0;
    color: #6c757d;
    font-size: 0.72rem;
}
</style>
