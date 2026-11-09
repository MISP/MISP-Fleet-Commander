<template>
    <span :class="['link-health-level', `level-${level}`, { 'is-unused': unused }]" :title="title">
        <span class="level-mark" aria-hidden="true"><i :class="['fas', meta.glyph]"></i></span>
        <span class="level-label">{{ meta.label }}</span>
        <span v-if="unused" class="unused-tag">unused</span>
    </span>
</template>

<script>
import { LINK_LEVEL_META } from "@/helpers/linkHealth"

// A sync link's health level: the glyph of the graph's badges, in a ring of the link's colour, and its name
export default {
    name: "LinkHealthLevel",
    props: {
        level: {
            type: String,
            default: "unknown",
        },
        unused: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        meta() {
            return LINK_LEVEL_META[this.level] || LINK_LEVEL_META.unknown
        },
        title() {
            return this.unused ? "Push, pull and caching are off: nothing depends on this link" : null
        },
    },
}
</script>

<style scoped>
.link-health-level {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    white-space: nowrap;
    font-weight: 600;
    line-height: 1.4;
}

.level-mark {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    width: 1.5em;
    height: 1.5em;
    border: 2px solid var(--link-unknown);
    border-radius: 50%;
    background: #fff;
    color: #5c636a;
    font-size: 0.8em;
}

.level-ok .level-mark {
    border-color: var(--link-ok);
    color: var(--health-ok-ink);
}

.level-ok .level-label {
    color: var(--health-ok-ink);
}

.level-degraded .level-mark {
    border-color: var(--link-degraded);
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
}

.level-degraded .level-label {
    color: var(--health-warning-ink);
}

.level-broken .level-mark {
    border-color: var(--link-broken);
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.level-broken .level-label {
    color: var(--health-critical-ink);
}

.level-unknown .level-mark {
    border-style: dashed;
}

.level-unknown .level-label {
    color: #5c636a;
}

.is-unused .level-mark,
.is-unused .level-label {
    opacity: 0.6;
}

.unused-tag {
    padding: 0 0.4em;
    border: 1px dashed #adb5bd;
    border-radius: 0.7em;
    color: #6c757d;
    font-size: 0.8em;
    font-weight: 600;
    line-height: 1.4;
}
</style>
