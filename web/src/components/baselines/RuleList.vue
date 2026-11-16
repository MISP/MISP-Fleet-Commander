<template>
    <ul class="rule-list">
        <li v-for="item in items" :key="item.id" :class="['rule-list-item', `is-${tone}`]">
            <span v-if="marker" class="rule-list-marker" aria-hidden="true">{{ marker }}</span>
            <i :class="['rule-list-type', typeIcon(item.rule)]" :title="typeLabel(item.rule)" aria-hidden="true"></i>
            <span class="rule-list-name">
                <span class="rule-list-title" :title="item.rule.key">{{ title(item.rule) }}</span>
                <span v-if="subtitle(item.rule)" class="rule-list-subtitle">{{ subtitle(item.rule) }}</span>
            </span>
            <span class="rule-list-side">
                <template v-if="item.change">
                    <span v-if="item.change.expected" class="rule-list-change">
                        <span class="rule-list-before">{{ item.change.expected[0] }}</span>
                        <i class="fas fa-arrow-right rule-list-arrow" aria-label="becomes"></i>
                        <span class="rule-list-after">{{ item.change.expected[1] }}</span>
                    </span>
                    <span v-if="item.change.others.length > 0" class="rule-list-others">{{ item.change.others.join(" · ") }}</span>
                </template>
                <span v-else class="rule-list-expected">{{ expected(item.rule) }}</span>
                <span v-if="showSeverity" :class="['rule-list-severity', `is-${item.rule.severity}`]">{{ item.rule.severity }}</span>
                <span v-if="item.rule.forced" class="rule-list-forced" title="A server-specific setting, kept on purpose">forced</span>
            </span>
            <span v-if="editable" class="rule-list-actions">
                <button type="button" class="rule-list-action" :aria-label="`Edit ${title(item.rule)}`" title="Edit" @click="$emit('edit', item.rule)">
                    <i class="fas fa-pen" aria-hidden="true"></i>
                </button>
                <button type="button" class="rule-list-action is-danger" :aria-label="`Remove ${title(item.rule)}`" title="Remove" @click="$emit('delete', item.rule)">
                    <i class="fas fa-trash-can" aria-hidden="true"></i>
                </button>
            </span>
        </li>
    </ul>
</template>

<script>
import { TYPE_META, expectedText, ruleTitle } from "./baselineFormat"

// Rules read-only: a source's rules, or what a copy adds, changes or removes
export default {
    name: "RuleList",
    props: {
        // [{id, rule, change?}], change = ruleChange(current, next)
        items: { type: Array, required: true },
        tone: { type: String, default: "plain" },
        showSeverity: { type: Boolean, default: true },
        // Edit and remove buttons on each row (`edit` / `delete` events with the rule)
        editable: { type: Boolean, default: false },
    },
    computed: {
        marker() {
            return { added: "+", removed: "−", changed: "~" }[this.tone] || ""
        },
    },
    methods: {
        typeIcon(rule) {
            return (TYPE_META[rule.type] || { icon: "fas fa-circle" }).icon
        },
        typeLabel(rule) {
            return (TYPE_META[rule.type] || { label: rule.type }).label
        },
        title(rule) {
            return ruleTitle(rule)
        },
        // A setting's name or a taxonomy's namespace under its label (UUIDs are not telling)
        subtitle(rule) {
            if ((rule.type === "setting" || rule.type === "taxonomy_enabled") && rule.label && rule.label !== rule.key) {
                return rule.key
            }
            return ""
        },
        expected(rule) {
            return expectedText(rule)
        },
    },
}
</script>

<style scoped>
.rule-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.rule-list-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0.75rem;
    border-top: 1px solid #f0f2f5;
    font-size: 0.875rem;
}

.rule-list-item:first-child {
    border-top: none;
}

.rule-list-marker {
    flex: 0 0 0.75rem;
    font-weight: 700;
    text-align: center;
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.is-added .rule-list-marker {
    color: var(--health-ok-ink);
}

.is-removed .rule-list-marker {
    color: var(--health-critical-ink);
}

.is-changed .rule-list-marker {
    color: var(--health-warning-ink);
}

.rule-list-type {
    flex: 0 0 1rem;
    text-align: center;
    color: #6c737d;
}

.rule-list-name {
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-direction: column;
}

.rule-list-title,
.rule-list-subtitle {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rule-list-title {
    color: var(--var-color-yankeesblue);
}

.is-removed .rule-list-title {
    color: #5a6270;
    text-decoration: line-through;
    text-decoration-color: rgba(90, 98, 112, 0.45);
}

.rule-list-subtitle {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.75rem;
    color: #6c737d;
}

.rule-list-side {
    flex: 0 1 auto;
    max-width: 55%;
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 0.25rem 0.5rem;
}

.rule-list-expected,
.rule-list-change {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.8rem;
    color: #3b4250;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
}

.rule-list-change {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

.rule-list-before,
.rule-list-after {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0 0.35rem;
    border-radius: 3px;
}

.rule-list-before {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
    text-decoration: line-through;
    text-decoration-color: rgba(181, 42, 55, 0.45);
}

.rule-list-after {
    background: #eaf6ef;
    color: var(--health-ok-ink);
}

.rule-list-arrow {
    color: #8a919c;
    font-size: 0.75rem;
}

.rule-list-others {
    font-size: 0.78rem;
    color: #5a6270;
}

.rule-list-severity,
.rule-list-forced {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
}

.rule-list-severity.is-critical {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.rule-list-severity.is-warning {
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
}

.rule-list-severity.is-info {
    background: var(--health-info-tint);
    color: var(--health-info-ink);
}

.rule-list-forced {
    background: #eef0f3;
    color: #4a5260;
}

.rule-list-actions {
    flex: 0 0 auto;
    display: inline-flex;
    gap: 0.15rem;
    margin-left: 0.25rem;
}

.rule-list-action {
    width: 1.75rem;
    height: 1.75rem;
    border: none;
    border-radius: 4px;
    background: none;
    color: #6c737d;
    font-size: 0.8rem;
}

.rule-list-action:hover {
    background: #eef0f3;
    color: var(--var-color-yankeesblue);
}

.rule-list-action.is-danger:hover {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.rule-list-action:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

@media (max-width: 575.98px) {
    .rule-list-item {
        flex-wrap: wrap;
    }

    .rule-list-name {
        flex: 1 1 0;
    }

    /* The buttons stay on the name's line, the expected value goes under it */
    .rule-list-actions {
        order: 1;
    }

    .rule-list-side {
        order: 2;
        max-width: 100%;
        flex-basis: 100%;
        justify-content: flex-start;
        padding-left: 1.6rem;
    }
}
</style>
