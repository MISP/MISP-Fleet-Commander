<template>
    <b-modal
        :id="modalId"
        :title="title"
        size="xl"
        scrollable
        body-class="imp-modal-body"
        @show="onShow"
        @hidden="onHidden"
    >
        <div v-if="libraryLoading" class="imp-state" role="status">
            <b-spinner small class="mr-2"></b-spinner>Loading presets and saved baselines…
        </div>
        <b-alert :show="!!libraryError" variant="danger" class="m-3">
            Could not load the baselines: {{ libraryError }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="loadLibrary">Try again</b-button>
        </b-alert>

        <div v-if="library" :class="['imp', { 'is-single': !!fixedSource }]">
            <!-- Sources -->
            <aside v-if="!fixedSource" class="imp-sources" aria-label="Baselines to import">
                <b-input-group v-if="sourceCount > 6" size="sm" class="imp-search">
                    <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
                    <b-form-input v-model="search" type="search" placeholder="Search" aria-label="Search baselines"></b-form-input>
                </b-input-group>
                <section v-for="group in groups" :key="group.kind" class="imp-group" :aria-labelledby="`imp-group-${group.kind}`">
                    <h3 :id="`imp-group-${group.kind}`" class="imp-group-title">
                        <i :class="[group.icon, 'fa-fw']" aria-hidden="true"></i>{{ group.title }}
                    </h3>
                    <p v-if="group.items.length === 0" class="imp-group-empty">{{ group.empty }}</p>
                    <div v-else role="radiogroup" :aria-labelledby="`imp-group-${group.kind}`">
                        <button
                            v-for="item in group.items"
                            :key="item.key"
                            type="button"
                            role="radio"
                            :aria-checked="item.key === selectedKey ? 'true' : 'false'"
                            :disabled="item.rule_count === 0"
                            :class="['imp-source', { active: item.key === selectedKey }]"
                            @click="select(item)"
                        >
                            <span class="imp-source-name">{{ item.name }}</span>
                            <span class="imp-source-meta">
                                {{ item.rule_count === 0 ? "No rules" : ruleCount(item.rule_count) }}
                                <span class="imp-source-types" aria-hidden="true">
                                    <i v-for="chip in chips(item)" :key="chip.type" :class="chip.icon" :title="chip.text"></i>
                                </span>
                            </span>
                        </button>
                    </div>
                </section>
            </aside>

            <!-- The selected source, and what importing it changes -->
            <section class="imp-detail" aria-live="polite">
                <template v-if="selected">
                    <header class="imp-head">
                        <span class="imp-kind"><i :class="[kindMeta(selected).icon, 'mr-1']" aria-hidden="true"></i>{{ kindMeta(selected).label }}</span>
                        <h3 class="imp-name">{{ selected.name }}</h3>
                        <p v-if="selected.description" class="imp-description">{{ selected.description }}</p>
                        <div class="imp-chips">
                            <span v-for="chip in chips(selected)" :key="chip.type" class="imp-chip">
                                <i :class="[chip.icon, 'mr-1']" aria-hidden="true"></i>{{ chip.text }}
                            </span>
                        </div>
                    </header>

                    <b-form-group v-if="fleetId === null" label="Into fleet" label-for="imp-target" class="imp-target">
                        <b-form-select id="imp-target" v-model="targetId" :options="targetOptions">
                            <template #first>
                                <b-form-select-option :value="null" disabled>Pick a fleet</b-form-select-option>
                            </template>
                        </b-form-select>
                    </b-form-group>

                    <div v-if="target && target.rule_count > 0" class="imp-mode" role="radiogroup" aria-label="This fleet's current rules">
                        <button
                            v-for="option in modeOptions"
                            :key="option.value"
                            type="button"
                            role="radio"
                            :aria-checked="mode === option.value ? 'true' : 'false'"
                            :class="['imp-mode-option', { active: mode === option.value }]"
                            @click="mode = option.value"
                        >
                            <span class="imp-mode-title">
                                <i :class="[option.icon, 'mr-1']" aria-hidden="true"></i>{{ option.title }}
                            </span>
                            <span class="imp-mode-text">{{ option.text }}</span>
                        </button>
                    </div>

                    <div v-if="target" class="imp-preview">
                        <div v-if="previewLoading && !preview" class="imp-state" role="status">
                            <b-spinner small class="mr-2"></b-spinner>Comparing with {{ target.name }}'s baseline…
                        </div>
                        <b-alert :show="!!previewError" variant="danger" class="mb-0">
                            <strong>{{ previewError && previewError.message }}</strong>
                            <ul v-if="previewError && previewError.items.length > 0" class="imp-errors">
                                <li v-for="item in previewError.items" :key="item.index">
                                    <span class="imp-error-rule">{{ item.rule }}</span>: {{ item.message }}
                                </li>
                            </ul>
                            <p v-if="previewError && previewError.items.length > 0" class="imp-error-hint">
                                Rules are checked against the setting types {{ target.name }}'s servers report.
                            </p>
                        </b-alert>

                        <template v-if="preview">
                            <div :class="['imp-summary', { 'is-stale': previewLoading }]">
                                <span v-for="stat in stats" :key="stat.tone" :class="['imp-stat', `is-${stat.tone}`, { 'is-zero': stat.count === 0 }]">
                                    <span class="imp-stat-count">{{ stat.count }}</span> {{ stat.label }}
                                </span>
                            </div>
                            <p v-if="changeCount === 0" class="imp-nothing">
                                <i class="fas fa-circle-check text-success mr-1" aria-hidden="true"></i>
                                {{ target.name }}'s baseline already has these rules: nothing changes.
                            </p>
                            <div v-for="block in blocks" :key="block.tone" :class="['imp-block', `is-${block.tone}`]">
                                <h4 class="imp-block-title">{{ block.title }} <span class="imp-block-count">{{ block.items.length }}</span></h4>
                                <RuleList :items="block.items" :tone="block.tone"></RuleList>
                            </div>
                        </template>
                    </div>
                    <p v-else-if="fleetId === null" class="imp-hint">Pick the fleet to copy these rules into.</p>
                </template>
                <div v-else class="imp-state">Pick a baseline to see what it changes.</div>
            </section>
        </div>

        <template #modal-footer="{ cancel }">
            <span v-if="footerNote" class="imp-footer-note">{{ footerNote }}</span>
            <b-button variant="outline-secondary" @click="cancel()">Cancel</b-button>
            <b-button variant="primary" :disabled="!canApply" @click="apply">
                <b-spinner v-if="applying" small class="mr-1"></b-spinner>
                <i v-else class="fas fa-file-import mr-1" aria-hidden="true"></i>{{ applyLabel }}
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/baselines"
import RuleList from "./RuleList.vue"
import { SOURCE_KINDS, ruleChange, ruleCountText, ruleTitle, sourceKey, sourceParam, typeSummary } from "./baselineFormat"

// Copies a preset, a saved baseline or another fleet's baseline into a fleet, after showing what it changes.
// From a fleet's Baseline tab (`fleetId`), the source is picked here; from the library (`fixedSource`), the fleet is
export default {
    name: "ImportBaselineModal",
    components: { RuleList },
    props: {
        modalId: { type: String, default: "modal-baseline-import" },
        // The fleet the rules go to; null: picked in the dialog
        fleetId: { type: Number, default: null },
        // {kind, id}: the source, when it is already chosen
        fixedSource: { type: Object, default: null },
    },
    data() {
        return {
            library: null,
            libraryLoading: false,
            libraryError: null,
            search: "",
            selectedKey: "",
            targetId: null,
            mode: "replace",
            preview: null,
            previewLoading: false,
            previewError: null,
            previewToken: 0,
            applying: false,
            modeOptions: [
                { value: "replace", icon: "fas fa-arrow-right-arrow-left", title: "Replace", text: "The fleet's baseline becomes exactly this one" },
                { value: "merge", icon: "fas fa-code-merge", title: "Merge", text: "Keep the fleet's other rules; rules for the same thing are overwritten" },
            ],
        }
    },
    computed: {
        sources() {
            if (!this.library) {
                return []
            }
            const withKey = kind => item => ({ ...item, kind, key: sourceKey({ kind, id: item.id }) })
            return [
                ...this.library.presets.map(withKey("preset")),
                ...this.library.saved.map(withKey("saved")),
                ...this.library.fleets.filter(fleet => fleet.id !== this.targetId).map(withKey("fleet")),
            ]
        },
        sourceCount() {
            return this.sources.length
        },
        groups() {
            const search = this.search.trim().toLowerCase()
            const matches = item => search === "" || `${item.name} ${item.description || ""}`.toLowerCase().includes(search)
            const empty = {
                preset: "No preset matches.",
                saved: search === "" ? "None yet: use “Save as…” on a fleet's baseline to keep one." : "No saved baseline matches.",
                fleet: search === "" ? "No other fleet." : "No fleet matches.",
            }
            return ["preset", "saved", "fleet"].map(kind => ({
                kind,
                title: SOURCE_KINDS[kind].plural,
                icon: SOURCE_KINDS[kind].icon,
                empty: empty[kind],
                items: this.sources.filter(item => item.kind === kind && matches(item)),
            }))
        },
        selected() {
            return this.sources.find(item => item.key === this.selectedKey) || null
        },
        targetOptions() {
            if (!this.library) {
                return []
            }
            return this.library.fleets
                .filter(fleet => !(this.fixedSource && this.fixedSource.kind === "fleet" && fleet.id === this.fixedSource.id))
                .map(fleet => ({ value: fleet.id, text: fleet.rule_count > 0 ? `${fleet.name} (${ruleCountText(fleet.rule_count)})` : fleet.name }))
        },
        target() {
            if (!this.library || this.targetId === null) {
                return null
            }
            return this.library.fleets.find(fleet => fleet.id === this.targetId) || null
        },
        effectiveMode() {
            return this.target && this.target.rule_count > 0 ? this.mode : "replace"
        },
        stats() {
            if (!this.preview) {
                return []
            }
            const stats = [
                { tone: "added", label: "added", count: this.preview.added.length },
                { tone: "changed", label: "changed", count: this.preview.replaced.length },
            ]
            if (this.effectiveMode === "replace") {
                stats.push({ tone: "removed", label: "removed", count: this.preview.removed.length })
            }
            stats.push({ tone: "same", label: "unchanged", count: this.preview.unchanged })
            return stats
        },
        changeCount() {
            if (!this.preview) {
                return 0
            }
            return this.preview.added.length + this.preview.replaced.length + this.preview.removed.length
        },
        blocks() {
            if (!this.preview) {
                return []
            }
            const blocks = [
                {
                    tone: "added",
                    title: "Added",
                    items: this.preview.added.map(rule => ({ id: `${rule.type}|${rule.key}`, rule })),
                },
                {
                    tone: "changed",
                    title: "Changed",
                    items: this.preview.replaced.map(({ rule, current }) => ({
                        id: `${rule.type}|${rule.key}`, rule, change: ruleChange(current, rule),
                    })),
                },
                {
                    tone: "removed",
                    title: "Removed",
                    items: this.preview.removed.map(rule => ({ id: `${rule.type}|${rule.key}`, rule })),
                },
            ]
            return blocks.filter(block => block.items.length > 0)
        },
        title() {
            if (this.fixedSource && this.selected) {
                return `Apply “${this.selected.name}” to a fleet`
            }
            return "Import a baseline"
        },
        canApply() {
            return !!this.preview && !this.previewLoading && !this.previewError && this.changeCount > 0 && !this.applying
        },
        applyLabel() {
            if (!this.preview || this.changeCount === 0) {
                return "Import"
            }
            if (this.target.rule_count === 0) {
                return `Import ${ruleCountText(this.preview.added.length)}`
            }
            return this.effectiveMode === "replace" ? "Replace the baseline" : "Merge into the baseline"
        },
        footerNote() {
            if (!this.preview || !this.target || this.changeCount === 0) {
                return ""
            }
            const after = this.effectiveMode === "merge"
                ? this.target.rule_count + this.preview.added.length
                : this.preview.added.length + this.preview.replaced.length + this.preview.unchanged
            return `${this.target.name}: ${ruleCountText(this.target.rule_count)} → ${ruleCountText(after)}`
        },
    },
    watch: {
        selectedKey() {
            this.loadPreview()
        },
        targetId() {
            this.loadPreview()
        },
        mode() {
            this.loadPreview()
        },
    },
    methods: {
        kindMeta(source) {
            return SOURCE_KINDS[source.kind]
        },
        chips(item) {
            return typeSummary(item.types)
        },
        ruleCount(count) {
            return ruleCountText(count)
        },
        onShow() {
            this.search = ""
            this.mode = "replace"
            this.preview = null
            this.previewError = null
            this.targetId = this.fleetId
            this.selectedKey = this.fixedSource ? sourceKey(this.fixedSource) : ""
            this.loadLibrary()
        },
        onHidden() {
            this.previewToken += 1
            this.library = null
            this.applying = false
        },
        loadLibrary() {
            this.libraryLoading = true
            this.libraryError = null
            return api.library()
                .then((library) => {
                    this.library = library
                    if (this.selectedKey === "" || !this.selected) {
                        const first = this.sources.find(item => item.rule_count > 0)
                        this.selectedKey = this.fixedSource ? sourceKey(this.fixedSource) : (first ? first.key : "")
                    }
                    this.loadPreview()
                })
                .catch((error) => {
                    this.libraryError = error.message
                })
                .finally(() => {
                    this.libraryLoading = false
                })
        },
        select(item) {
            this.selectedKey = item.key
        },
        loadPreview() {
            const token = ++this.previewToken
            this.previewError = null
            if (!this.library || !this.selected || !this.target) {
                this.preview = null
                return
            }
            const source = this.selected
            const target = this.target
            this.previewLoading = true
            api.copyPreview(target.id, sourceParam(source), this.effectiveMode)
                .then((preview) => {
                    if (token === this.previewToken) {
                        this.preview = preview
                    }
                })
                .catch((error) => {
                    if (token !== this.previewToken) {
                        return
                    }
                    this.preview = null
                    this.previewError = { message: error.message, items: [] }
                    if (error.errors.length > 0) {
                        this.describeErrors(token, source, error.errors)
                    }
                })
                .finally(() => {
                    if (token === this.previewToken) {
                        this.previewLoading = false
                    }
                })
        },
        // Names the source's rules that the fleet refuses (errors only give their index)
        describeErrors(token, source, errors) {
            const items = errors.slice(0, 8).map(error => ({ index: error.index, rule: `Rule ${error.index + 1}`, message: error.message }))
            this.previewError = { ...this.previewError, items }
            const load = source.kind === "preset" ? api.preset(source.id)
                : source.kind === "saved" ? api.saved(source.id) : api.get(source.id)
            load.then((detail) => {
                if (token !== this.previewToken || !this.previewError) {
                    return
                }
                this.previewError = {
                    ...this.previewError,
                    items: items.map(item => ({ ...item, rule: detail.rules[item.index] ? ruleTitle(detail.rules[item.index]) : item.rule })),
                }
            }).catch(() => {})
        },
        apply() {
            const source = this.selected
            const target = this.target
            this.applying = true
            api.copy(target.id, sourceParam(source), this.effectiveMode)
                .then((baseline) => {
                    this.$emit("applied", { fleet: target, source, baseline })
                    this.$bvModal.hide(this.modalId)
                })
                .catch((error) => {
                    this.previewError = { message: error.message, items: [] }
                    if (error.errors.length > 0) {
                        this.describeErrors(this.previewToken, source, error.errors)
                    }
                })
                .finally(() => {
                    this.applying = false
                })
        },
    },
}
</script>

<style scoped>
::v-deep .imp-modal-body {
    padding: 0;
}

.imp {
    display: grid;
    grid-template-columns: minmax(15rem, 18rem) 1fr;
    min-height: 26rem;
}

.imp.is-single {
    grid-template-columns: 1fr;
}

.imp-state {
    padding: 1.25rem;
    color: #4a5260;
}

.imp-sources {
    padding: 0.75rem;
    background: #f8f9fb;
    border-right: 1px solid var(--health-rule);
    overflow-y: auto;
}

.imp-search {
    margin-bottom: 0.75rem;
}

.imp-group + .imp-group {
    margin-top: 1rem;
}

.imp-group-title {
    margin: 0 0 0.35rem;
    padding: 0 0.4rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.imp-group-title i {
    margin-right: 0.3rem;
}

.imp-group-empty {
    margin: 0;
    padding: 0.25rem 0.4rem;
    font-size: 0.82rem;
    color: #6c737d;
}

.imp-source {
    display: flex;
    flex-direction: column;
    width: 100%;
    padding: 0.45rem 0.6rem;
    margin-bottom: 2px;
    border: 1px solid transparent;
    border-radius: 6px;
    background: none;
    text-align: left;
    color: var(--var-color-yankeesblue);
}

.imp-source:hover:not(:disabled) {
    background: #eef1f5;
}

.imp-source.active {
    background: #fff;
    border-color: var(--var-color-lapislazuli);
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.08);
}

.imp-source:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.imp-source:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}

.imp-source-name {
    font-weight: 600;
    font-size: 0.9rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.imp-source-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.78rem;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

.imp-source-types {
    display: inline-flex;
    gap: 0.35rem;
    color: #8a919c;
    font-size: 0.72rem;
}

.imp-detail {
    padding: 1rem 1.25rem 1.25rem;
    min-width: 0;
}

.imp-head {
    margin-bottom: 1rem;
}

.imp-kind {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--var-color-lapislazuli);
}

.imp-name {
    margin: 0.15rem 0 0.35rem;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.imp-description {
    margin: 0 0 0.6rem;
    max-width: 48rem;
    color: #4a5260;
    font-size: 0.9rem;
}

.imp-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}

.imp-chip {
    display: inline-flex;
    align-items: center;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: #eef0f3;
    font-size: 0.78rem;
    color: #3b4250;
}

.imp-chip i {
    color: #6c737d;
}

.imp-target {
    max-width: 24rem;
}

.imp-mode {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.imp-mode-option {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.55rem 0.75rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #fff;
    text-align: left;
}

.imp-mode-option:hover {
    border-color: #c5cbd3;
}

.imp-mode-option.active {
    border-color: var(--var-color-lapislazuli);
    background: var(--health-focus-bg);
    box-shadow: inset 0 0 0 1px var(--var-color-lapislazuli);
}

.imp-mode-option:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.imp-mode-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--var-color-yankeesblue);
}

.imp-mode-text {
    font-size: 0.8rem;
    color: #5a6270;
}

.imp-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.75rem;
    transition: opacity 0.15s;
}

.imp-summary.is-stale {
    opacity: 0.5;
}

.imp-stat {
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 500;
    background: #eef0f3;
    color: #3b4250;
}

.imp-stat-count {
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}

.imp-stat.is-added {
    background: #eaf6ef;
    color: var(--health-ok-ink);
}

.imp-stat.is-changed {
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
}

.imp-stat.is-removed {
    background: var(--health-critical-tint);
    color: var(--health-critical-ink);
}

.imp-stat.is-zero {
    background: #f4f5f7;
    color: #8a919c;
}

.imp-nothing,
.imp-hint {
    color: #4a5260;
    font-size: 0.9rem;
}

.imp-block {
    margin-bottom: 0.75rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.imp-block-title {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0;
    padding: 0.4rem 0.75rem;
    background: #f6f7f9;
    border-bottom: 1px solid var(--health-rule);
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.imp-block-count {
    font-weight: 500;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

.imp-errors {
    margin: 0.4rem 0 0;
    padding-left: 1.1rem;
    font-size: 0.875rem;
}

.imp-error-rule {
    font-weight: 600;
}

.imp-error-hint {
    margin: 0.4rem 0 0;
    font-size: 0.82rem;
}

.imp-footer-note {
    margin-right: auto;
    font-size: 0.85rem;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 767.98px) {
    .imp {
        grid-template-columns: 1fr;
    }

    .imp-sources {
        border-right: none;
        border-bottom: 1px solid var(--health-rule);
        max-height: 16rem;
    }

    .imp-mode {
        grid-template-columns: 1fr;
    }
}
</style>
