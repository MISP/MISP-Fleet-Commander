<template>
    <b-modal
        id="modal-baseline-reference"
        :title="title"
        size="xl"
        scrollable
        cancel-variant="outline-secondary"
        @show="onShow"
        @hidden="onHidden"
    >
        <div class="ref-head">
            <b-form-group label="Server" label-for="ref-server" class="ref-server mb-0">
                <b-form-select
                    id="ref-server"
                    v-model="serverId"
                    :options="serverOptions"
                    @change="load"
                ></b-form-select>
            </b-form-group>
            <p class="ref-source" aria-live="polite">
                <template v-if="loading"><b-spinner small class="mr-1"></b-spinner>Listing its settings and content…</template>
                <template v-else-if="reference">{{ sourceText }}</template>
            </p>
        </div>

        <b-alert :show="!!error" variant="danger" class="mt-3 mb-0">
            Could not list from this server: {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load(true)">Try again</b-button>
        </b-alert>

        <template v-if="reference">
            <div class="ref-tabs" role="tablist" aria-label="What to take">
                <button
                    v-for="section in sections"
                    :id="`ref-tab-${section.type}`"
                    :key="section.type"
                    type="button"
                    role="tab"
                    :aria-selected="activeType === section.type ? 'true' : 'false'"
                    :aria-controls="`ref-panel-${section.type}`"
                    :class="['ref-tab', { active: activeType === section.type }]"
                    @click="activeType = section.type"
                >
                    <i :class="[section.icon, 'mr-1']" aria-hidden="true"></i>{{ section.label }}
                    <span v-if="selectedCount(section.type) > 0" class="ref-tab-count">{{ selectedCount(section.type) }}</span>
                </button>
            </div>

            <div
                :id="`ref-panel-${activeType}`"
                role="tabpanel"
                :aria-labelledby="`ref-tab-${activeType}`"
                class="ref-panel"
            >
                <div class="ref-tools">
                    <b-input-group size="sm" class="ref-search">
                        <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
                        <b-form-input
                            v-model="search"
                            type="search"
                            :placeholder="activeType === 'setting' ? 'Search settings or values' : 'Search by name'"
                            :aria-label="`Search ${activeSection.label.toLowerCase()}`"
                        ></b-form-input>
                    </b-input-group>
                    <template v-if="activeType === 'setting'">
                        <b-form-select v-model="settingTab" :options="settingTabs" size="sm" class="ref-select" aria-label="Section"></b-form-select>
                        <b-form-checkbox v-model="showServerSpecific" switch class="ref-switch">Server-specific settings</b-form-checkbox>
                    </template>
                    <b-form-checkbox v-else-if="isContent" v-model="onlyEnabled" switch class="ref-switch">Only {{ enabledWord }}</b-form-checkbox>
                </div>

                <p v-if="activeError" class="ref-empty">
                    <i class="fas fa-triangle-exclamation mr-1" aria-hidden="true"></i>{{ activeError }}
                </p>
                <template v-else>
                    <div class="ref-list-head">
                        <b-form-checkbox
                            :checked="allShownSelected"
                            :indeterminate="someShownSelected && !allShownSelected"
                            :disabled="shown.length === 0"
                            @change="selectShown"
                        >
                            {{ shownLabel }}
                        </b-form-checkbox>
                        <b-button v-if="selectedCount(activeType) > 0" variant="link" size="sm" class="p-0" @click="clearType(activeType)">
                            Clear {{ selectedCount(activeType) }} selected
                        </b-button>
                    </div>
                    <ul v-if="shown.length > 0" class="ref-list">
                        <li v-for="row in shown" :key="row.key" :class="['ref-row', { selected: isSelected(row.key) }]">
                            <b-form-checkbox
                                :checked="isSelected(row.key)"
                                :disabled="!!row.unavailable"
                                class="ref-check"
                                @change="toggle(row.key, $event)"
                            >
                                <span :class="['ref-name', { 'ref-mono': activeType === 'setting' }]">{{ row.label }}</span>
                            </b-form-checkbox>
                            <span class="ref-tags">
                                <span v-if="row.serverSpecific" class="ref-tag ref-tag-warn" title="Usually different on each server">Server-specific</span>
                                <span v-if="row.cliOnly" class="ref-tag" title="MISP only lets this setting change from its command line">CLI only</span>
                                <span v-if="row.rule" :class="['ref-tag', row.ruleDiffers ? 'ref-tag-warn' : 'ref-tag-ok']" :title="row.ruleTitle">
                                    {{ row.ruleDiffers ? 'Baseline differs' : 'In the baseline' }}
                                </span>
                            </span>
                            <span :class="['ref-value', { 'ref-mono': activeType === 'setting', off: row.off }]" :title="row.valueTitle">{{ row.value }}</span>
                        </li>
                    </ul>
                    <p v-else class="ref-empty">{{ emptyText }}</p>
                    <p v-if="hiddenCount > 0" class="ref-more">{{ hiddenCount }} more: search to narrow down.</p>
                </template>
            </div>
        </template>

        <b-alert :show="submitErrors.length > 0" variant="danger" class="mt-3 mb-0">
            <strong>{{ submitMessage }}</strong>
            <ul class="mb-0 mt-1 pl-3">
                <li v-for="item in submitErrors.slice(0, 8)" :key="item.index">{{ item.name }}: {{ item.message }}</li>
            </ul>
        </b-alert>

        <template #modal-footer="{ cancel }">
            <div class="ref-footer">
                <span class="ref-summary" aria-live="polite">{{ summary }}</span>
                <label class="ref-option">
                    <span>Severity</span>
                    <b-form-select v-model="severity" :options="severityOptions" size="sm"></b-form-select>
                </label>
                <label v-if="existingSelected > 0" class="ref-option">
                    <span>{{ existingSelected }} already in the baseline</span>
                    <b-form-select v-model="onConflict" :options="conflictOptions" size="sm"></b-form-select>
                </label>
                <b-button variant="outline-secondary" @click="cancel()">Cancel</b-button>
                <b-button variant="primary" :disabled="totalSelected === 0 || saving" @click="submit">
                    <b-spinner v-if="saving" small class="mr-1"></b-spinner>
                    {{ submitLabel }}
                </b-button>
            </div>
        </template>
    </b-modal>
</template>

<script>
import moment from "moment"
import api from "@/api/baselines"
import {
    CONTENT_TYPES, ITEM_TYPES, LISTED_TYPES, SEVERITY_OPTIONS, TYPE_META, expectedFromSetting, formatValue, itemExpectedText,
    sameItemExpected,
} from "./baselineFormat"

const SHOWN = 200
const SECTION_LABELS = {
    setting: "Settings",
    taxonomy_enabled: "Taxonomies",
    galaxy_enabled: "Galaxies",
    object_template_active: "Object templates",
    organisation: "Organisations",
    sharing_group: "Sharing groups",
    custom_galaxy: "Custom galaxies",
}

function emptySelection() {
    const selection = { setting: {} }
    LISTED_TYPES.forEach((type) => { selection[type] = {} })
    return selection
}

function plural(count, noun) {
    return `${count} ${noun}${count === 1 ? "" : "s"}`
}

// How a reference item reads in the list: organisation details, members, clusters
function itemRow(type, item) {
    if (type === "organisation") {
        return { value: [item.group, item.description].filter(Boolean).join(" · "), off: false }
    }
    if (type === "sharing_group") {
        return { value: `${plural(item.members || 0, "member")}${item.enabled ? "" : " · inactive"}`, off: !item.enabled }
    }
    if (item.unavailable) {
        return { value: item.unavailable, off: true }
    }
    return { value: `${plural(item.clusters || 0, "cluster")}${item.enabled ? "" : " · disabled"}`, off: !item.enabled }
}

function sameValue(a, b) {
    return String(a === null || a === undefined ? "" : a) === String(b === null || b === undefined ? "" : b)
}

export default {
    name: "ReferenceImportModal",
    props: {
        fleetId: { type: Number, required: true },
        servers: { type: Array, default: () => [] },
        rules: { type: Array, default: () => [] },
    },
    data() {
        return {
            serverId: null,
            reference: null,
            loading: false,
            error: null,
            activeType: "setting",
            search: "",
            settingTab: "",
            showServerSpecific: false,
            onlyEnabled: true,
            selected: emptySelection(),
            severity: "warning",
            onConflict: "skip",
            saving: false,
            submitErrors: [],
            submitMessage: "",
            severityOptions: SEVERITY_OPTIONS,
            conflictOptions: [
                { value: "skip", text: "Keep their rules" },
                { value: "replace", text: "Replace their rules" },
            ],
        }
    },
    computed: {
        title() {
            return this.rules.length === 0 ? "Start from a reference server" : "Add rules from a server"
        },
        serverOptions() {
            return this.servers.map(server => ({
                value: server.id,
                text: server.unavailable ? `${server.name} (${server.unavailable.toLowerCase()})` : server.name,
            }))
        },
        sections() {
            return ["setting"].concat(LISTED_TYPES).map(type => ({ type, label: SECTION_LABELS[type], icon: TYPE_META[type].icon }))
        },
        isContent() {
            return CONTENT_TYPES.includes(this.activeType)
        },
        activeSection() {
            return this.sections.find(section => section.type === this.activeType)
        },
        sourceText() {
            const parts = []
            if (this.reference.refreshed_at) {
                parts.push(`Settings from its refresh ${moment.unix(this.reference.refreshed_at).fromNow()}`)
            }
            const listedAt = LISTED_TYPES.map(type => this.reference.content[type]).find(section => section && section.source)
            if (listedAt && listedAt.source === "live") {
                parts.push("content listed just now")
            } else if (listedAt && listedAt.listed_at) {
                const why = this.reference.unavailable ? ` (${this.reference.unavailable.toLowerCase()})` : ""
                parts.push(`content as listed ${moment.unix(listedAt.listed_at).fromNow()}${why}`)
            }
            return parts.join(", ")
        },
        rulesByKey() {
            const byKey = {}
            this.rules.forEach((rule) => { byKey[`${rule.type}|${rule.key}`] = rule })
            return byKey
        },
        settingTabs() {
            const tabs = new Set((this.reference ? this.reference.settings : []).map(setting => setting.tab))
            return [{ value: "", text: "All sections" }].concat([...tabs].sort().map(tab => ({ value: tab, text: tab })))
        },
        enabledWord() {
            return this.activeType === "object_template_active" ? "active" : "enabled"
        },
        // Every row of every type, in the list's words
        rowsByType() {
            const rows = { setting: [] }
            LISTED_TYPES.forEach((type) => { rows[type] = [] })
            if (!this.reference) {
                return rows
            }
            rows.setting = this.reference.settings.map((setting) => {
                const expected = expectedFromSetting(setting)
                const rule = this.rulesByKey[`setting|${setting.name}`]
                return {
                    key: setting.name,
                    label: setting.name,
                    tab: setting.tab,
                    value: formatValue(expected),
                    valueTitle: formatValue(expected),
                    expected,
                    serverSpecific: setting.server_specific,
                    cliOnly: setting.cli_only,
                    rule,
                    ruleDiffers: rule ? !(rule.comparator === "eq" && sameValue(rule.expected, expected)) : false,
                    ruleTitle: rule ? `The baseline expects ${rule.comparator === "eq" ? "" : rule.comparator + " "}${formatValue(rule.expected)}` : "",
                    search: `${setting.name} ${formatValue(expected)}`.toLowerCase(),
                }
            })
            CONTENT_TYPES.forEach((type) => {
                const section = this.reference.content[type]
                if (!section || !section.items) {
                    return
                }
                const on = type === "object_template_active" ? "active" : "enabled"
                const off = type === "object_template_active" ? "inactive" : "disabled"
                rows[type] = section.items.map((item) => {
                    const rule = this.rulesByKey[`${type}|${item.key}`]
                    return {
                        key: item.key,
                        label: item.label,
                        value: item.enabled ? on : off,
                        valueTitle: item.description || item.key,
                        off: !item.enabled,
                        expected: item.enabled,
                        rule,
                        ruleDiffers: rule ? rule.expected !== item.enabled : false,
                        ruleTitle: rule ? `The baseline expects it ${rule.expected ? on : off}` : "",
                        search: `${item.label} ${item.key} ${item.description} ${item.group}`.toLowerCase(),
                    }
                })
            })
            ITEM_TYPES.forEach((type) => {
                const section = this.reference.content[type]
                if (!section || !section.items) {
                    return
                }
                rows[type] = section.items.map((item) => {
                    const rule = this.rulesByKey[`${type}|${item.key}`]
                    const { value, off } = itemRow(type, item)
                    return {
                        key: item.key,
                        label: item.label,
                        value,
                        valueTitle: item.unavailable || item.key,
                        off,
                        expected: item.expected,
                        unavailable: item.unavailable || (item.expected ? null : "Cannot be taken from this server"),
                        rule,
                        ruleDiffers: rule ? !sameItemExpected(type, rule.expected, item.expected) : false,
                        ruleTitle: rule ? `The baseline expects: ${itemExpectedText(type, rule.expected)}` : "",
                        search: `${item.label} ${item.key} ${item.description} ${item.group}`.toLowerCase(),
                    }
                })
            })
            return rows
        },
        activeError() {
            if (this.activeType === "setting") {
                return this.reference.settings_error
            }
            const section = this.reference.content[this.activeType]
            return section && section.error ? section.error : null
        },
        filtered() {
            const search = this.search.trim().toLowerCase()
            return this.rowsByType[this.activeType].filter((row) => {
                if (this.activeType === "setting") {
                    if (row.serverSpecific && !this.showServerSpecific) {
                        return false
                    }
                    if (this.settingTab && row.tab !== this.settingTab) {
                        return false
                    }
                } else if (this.isContent && this.onlyEnabled && !row.expected) {
                    return false
                }
                return search === "" || row.search.includes(search)
            })
        },
        shown() {
            return this.filtered.slice(0, SHOWN)
        },
        hiddenCount() {
            return Math.max(this.filtered.length - SHOWN, 0)
        },
        shownLabel() {
            const noun = this.activeSection.label.toLowerCase()
            if (this.filtered.length === 0) {
                return `No ${noun}`
            }
            if (this.hiddenCount > 0) {
                return `Select the ${SHOWN} shown (${this.filtered.length} match)`
            }
            return `Select all ${this.filtered.length} ${this.filtered.length === 1 ? noun.replace(/s$/, "").replace(/ie$/, "y") : noun}`
        },
        allShownSelected() {
            const selectable = this.shown.filter(row => !row.unavailable)
            return selectable.length > 0 && selectable.every(row => this.isSelected(row.key))
        },
        someShownSelected() {
            return this.shown.some(row => this.isSelected(row.key))
        },
        emptyText() {
            if (this.search.trim() !== "") {
                return "Nothing matches this search."
            }
            if (this.isContent && this.onlyEnabled) {
                return `Nothing is ${this.enabledWord} on this server.`
            }
            return "Nothing to list."
        },
        selectedRows() {
            const rows = []
            Object.keys(this.selected).forEach((type) => {
                const byKey = {}
                this.rowsByType[type].forEach((row) => { byKey[row.key] = row })
                Object.keys(this.selected[type]).forEach((key) => {
                    if (byKey[key]) {
                        rows.push({ type, row: byKey[key] })
                    }
                })
            })
            return rows
        },
        totalSelected() {
            return this.selectedRows.length
        },
        existingSelected() {
            return this.selectedRows.filter(entry => entry.row.rule).length
        },
        summary() {
            if (this.totalSelected === 0) {
                return "Select what every server of the fleet should have."
            }
            const parts = this.sections
                .map(section => [section.label.toLowerCase(), this.selectedCount(section.type)])
                .filter(([, count]) => count > 0)
                .map(([label, count]) => `${count} ${count === 1 ? label.replace(/s$/, "").replace(/ie$/, "y") : label}`)
            return `${parts.join(", ")} selected`
        },
        submitLabel() {
            const adding = this.onConflict === "skip" ? this.totalSelected - this.existingSelected : this.totalSelected
            if (this.totalSelected > 0 && adding === 0) {
                return "Nothing new to add"
            }
            return adding > 0 ? `Add ${adding} rule${adding === 1 ? "" : "s"}` : "Add rules"
        },
    },
    watch: {
        activeType() {
            this.search = ""
        },
    },
    methods: {
        onShow() {
            this.submitErrors = []
            this.saving = false
            if (this.serverId === null || !this.servers.some(server => server.id === this.serverId)) {
                const reachable = this.servers.find(server => !server.unavailable)
                this.serverId = (reachable || this.servers[0] || {}).id || null
            }
            this.load()
        },
        onHidden() {
            this.selected = emptySelection()
            this.search = ""
        },
        load(fresh = false) {
            if (this.serverId === null) {
                return
            }
            const server_id = this.serverId
            this.loading = true
            this.error = null
            this.selected = emptySelection()
            api.reference(server_id, { fresh: fresh === true })
                .then((reference) => {
                    if (server_id === this.serverId) {
                        this.reference = reference
                    }
                })
                .catch((error) => {
                    if (server_id === this.serverId) {
                        this.reference = null
                        this.error = error.message
                    }
                })
                .finally(() => {
                    if (server_id === this.serverId) {
                        this.loading = false
                    }
                })
        },
        selectedCount(type) {
            return Object.keys(this.selected[type]).length
        },
        isSelected(key) {
            return this.selected[this.activeType][key] === true
        },
        toggle(key, checked) {
            if (checked) {
                this.$set(this.selected[this.activeType], key, true)
            } else {
                this.$delete(this.selected[this.activeType], key)
            }
        },
        selectShown(checked) {
            const selection = { ...this.selected[this.activeType] }
            this.shown.forEach((row) => {
                if (checked && row.unavailable) {
                    return
                }
                if (checked) {
                    selection[row.key] = true
                } else {
                    delete selection[row.key]
                }
            })
            this.selected = { ...this.selected, [this.activeType]: selection }
        },
        clearType(type) {
            this.selected = { ...this.selected, [type]: {} }
        },
        submit() {
            const entries = this.selectedRows
            const rules = entries.map(({ type, row }) => {
                const rule = { type, key: row.key, expected: row.expected, severity: this.severity }
                if (type === "setting") {
                    rule.force = row.serverSpecific === true
                } else if (ITEM_TYPES.includes(type)) {
                    // Named after the item by the server
                } else if (row.label !== row.key) {
                    rule.label = row.label
                }
                return rule
            })
            this.saving = true
            this.submitErrors = []
            api.addRules(this.fleetId, rules, this.onConflict)
                .then((baseline) => {
                    this.$emit("saved", baseline)
                    this.$bvModal.hide("modal-baseline-reference")
                })
                .catch((error) => {
                    this.submitMessage = error.message
                    const errors = error.errors.length > 0 ? error.errors : [{ index: -1, message: error.message }]
                    this.submitErrors = errors.map(item => ({
                        index: item.index,
                        name: entries[item.index] ? entries[item.index].row.label : "Rules",
                        message: item.message,
                    }))
                })
                .finally(() => {
                    this.saving = false
                })
        },
    },
}
</script>

<style scoped>
.ref-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.5rem 1rem;
}

.ref-server {
    flex: 0 1 20rem;
}

.ref-source {
    flex: 1 1 16rem;
    margin: 0 0 0.45rem;
    font-size: 0.85rem;
    color: #5a6270;
}

.ref-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin: 1rem 0 0;
    border-bottom: 1px solid var(--health-rule);
}

.ref-tab {
    display: inline-flex;
    align-items: center;
    border: none;
    background: none;
    padding: 0.4rem 0.8rem;
    margin-bottom: -1px;
    border-bottom: 2px solid transparent;
    font-size: 0.9rem;
    font-weight: 600;
    color: #5a6270;
}

.ref-tab:hover {
    color: var(--var-color-yankeesblue);
}

.ref-tab.active {
    color: var(--var-color-yankeesblue);
    border-bottom-color: var(--var-color-lapislazuli);
}

.ref-tab:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

.ref-tab-count {
    margin-left: 0.4rem;
    min-width: 1.4em;
    padding: 0 0.35rem;
    border-radius: 0.7rem;
    background: var(--var-color-lapislazuli);
    color: #fff;
    font-size: 0.72rem;
    line-height: 1.4;
    font-variant-numeric: tabular-nums;
}

.ref-panel {
    padding-top: 0.75rem;
}

.ref-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    margin-bottom: 0.5rem;
}

.ref-search {
    flex: 1 1 16rem;
    max-width: 24rem;
}

.ref-select {
    width: auto;
    max-width: 12rem;
}

.ref-switch {
    font-size: 0.875rem;
}

.ref-list-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--health-rule);
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    background: #f6f7f9;
    font-size: 0.85rem;
    font-weight: 600;
    color: #4a5260;
}

.ref-list {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--health-rule);
    border-radius: 0 0 6px 6px;
}

.ref-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.3rem 0.75rem;
    border-top: 1px solid var(--health-rule);
    font-size: 0.875rem;
}

.ref-row:first-child {
    border-top: none;
}

.ref-row:hover {
    background: #fafbfc;
}

.ref-row.selected {
    background: var(--health-focus-bg);
}

.ref-check {
    flex: 1 1 auto;
    min-width: 0;
}

.ref-check >>> .custom-control-label {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ref-name {
    color: var(--var-color-yankeesblue);
}

.ref-mono {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.82rem;
}

.ref-tags {
    display: inline-flex;
    gap: 0.3rem;
    flex: 0 0 auto;
}

.ref-tag {
    padding: 0 0.4rem;
    border-radius: 3px;
    background: #eef0f3;
    color: #4a5260;
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1.6;
    white-space: nowrap;
}

.ref-tag-warn {
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
}

.ref-tag-ok {
    background: #eaf6ef;
    color: var(--health-ok-ink);
}

.ref-value {
    flex: 0 1 16rem;
    min-width: 4rem;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #364156;
}

.ref-value.off {
    color: #8a919c;
}

.ref-empty {
    margin: 0;
    padding: 1.5rem 0.75rem;
    text-align: center;
    color: #5a6270;
    border: 1px dashed var(--health-rule);
    border-radius: 6px;
}

.ref-more {
    margin: 0.4rem 0 0;
    font-size: 0.8rem;
    color: #5a6270;
}

.ref-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.75rem;
    width: 100%;
}

.ref-summary {
    flex: 1 1 14rem;
    font-size: 0.875rem;
    color: #4a5260;
}

.ref-option {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0;
    font-size: 0.85rem;
    color: #4a5260;
    white-space: nowrap;
}

.ref-option .custom-select {
    width: auto;
}
</style>
