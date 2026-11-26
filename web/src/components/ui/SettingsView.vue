<template>
<div :class="['settings-layout', { 'is-searching': searching }]">
    <nav class="settings-nav" aria-label="Setting sections">
        <button
            v-for="panel in navPanels" :key="panel.panel"
            type="button"
            :class="['nav-item', { 'is-active': !searching && panel.panel === activePanel, 'is-empty': searching && panel.matches === 0 }]"
            :disabled="searching && panel.matches === 0"
            :aria-current="!searching && panel.panel === activePanel ? 'page' : null"
            @click="selectPanel(panel.panel)"
        >
            <i :class="[panel.icon, 'nav-icon']" aria-hidden="true"></i>
            <span class="nav-label">{{ panel.panel }}</span>
            <span v-if="searching" class="nav-count">{{ panel.matches }}</span>
            <span v-else-if="panel.pending" class="nav-pending" :title="`${panel.pending} unsaved`">
                <span class="sr-only">{{ panel.pending }} unsaved</span>
            </span>
        </button>
    </nav>

    <div ref="content" class="settings-content">
        <div v-if="loading && groups.length === 0" class="settings-state">
            <b-spinner small variant="secondary"></b-spinner>
            <span>Loading the settings…</span>
        </div>
        <div v-else-if="loadError && groups.length === 0" class="settings-state is-error">
            <i class="fas fa-triangle-exclamation" aria-hidden="true"></i>
            <span>Could not load the settings: {{ loadError }}</span>
            <b-button size="sm" variant="outline-secondary" @click="$emit('retry')">Try again</b-button>
        </div>
        <div v-else-if="searching && shownPanels.length === 0" class="settings-state">
            <i class="fas fa-magnifying-glass" aria-hidden="true"></i>
            <span>No setting matches “{{ query.trim() }}”.</span>
            <b-button size="sm" variant="outline-secondary" @click="$emit('clear-query')">Clear the search</b-button>
        </div>

        <section
            v-for="panel in shownPanels" :key="panel.panel"
            :id="panelId(panel.panel)"
            class="settings-panel"
        >
            <header class="panel-head">
                <h5 class="panel-title">
                    <i :class="[panelIcon(panel.panel), 'panel-icon']" aria-hidden="true"></i>{{ panel.panel }}
                </h5>
            </header>
            <div
                v-for="scope in panel.scopes" :key="`${panel.panel}-${scope.scope}`"
                class="settings-group"
            >
                <h6 v-if="scope.scope" class="group-title">{{ scope.scope }}</h6>
                <div class="group-card">
                    <SettingRow
                        v-for="setting in scope.settings" :key="setting.key"
                        :setting="setting"
                        :value="shownValue(setting.key)"
                        :pending="isPending(setting.key)"
                        :error="errors[setting.key] || null"
                        :read-only="readOnly"
                        :depends-on-name="inactiveSwitchName(setting)"
                        :highlighted="highlightKey === setting.key"
                        @change="(value) => $emit('change', setting.key, value)"
                        @revert="$emit('revert', setting.key)"
                        @reset-default="$emit('reset-default', setting.key)"
                    ></SettingRow>
                </div>
            </div>
        </section>
    </div>
</div>
</template>

<script>
import SettingRow from "@/views/settings/SettingRow.vue"
import { asBoolean, countSettings, filterGroups, panelIcon, settingLabel } from "@/views/settings/settingsModel"

export default {
    name: "SettingsView",
    components: {
        SettingRow,
    },
    props: {
        // From groupSettings(): every panel, unfiltered
        groups: { type: Array, required: true },
        // Saved values by setting name
        values: { type: Object, required: true },
        // Unsaved changes by setting name
        drafts: { type: Object, required: true },
        // Why a change cannot be saved, by setting name
        errors: { type: Object, required: true },
        activePanel: { type: String, default: null },
        query: { type: String, default: "" },
        readOnly: { type: Boolean, default: false },
        highlightKey: { type: String, default: null },
        loading: { type: Boolean, default: false },
        loadError: { type: String, default: null },
    },
    computed: {
        searching() {
            return this.query.trim() !== ""
        },
        filteredGroups() {
            return this.searching ? filterGroups(this.groups, this.query) : this.groups
        },
        shownPanels() {
            if (this.searching) {
                return this.filteredGroups
            }
            const active = this.groups.find(panel => panel.panel === this.activePanel)
            return active ? [active] : this.groups.slice(0, 1)
        },
        navPanels() {
            return this.groups.map(panel => {
                const filtered = this.filteredGroups.find(p => p.panel === panel.panel)
                const keys = panel.scopes.flatMap(scope => scope.settings.map(setting => setting.key))
                return {
                    panel: panel.panel,
                    icon: panelIcon(panel.panel),
                    matches: filtered ? countSettings(filtered) : 0,
                    pending: keys.filter(key => this.isPending(key)).length,
                }
            })
        },
        settingsByKey() {
            const byKey = {}
            this.groups.forEach(panel => panel.scopes.forEach(scope => scope.settings.forEach(setting => {
                byKey[setting.key] = setting
            })))
            return byKey
        },
    },
    methods: {
        panelIcon,
        panelId(panel) {
            return `settings-panel-${panel.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
        },
        isPending(key) {
            return Object.prototype.hasOwnProperty.call(this.drafts, key)
        },
        shownValue(key) {
            return this.isPending(key) ? this.drafts[key] : this.values[key]
        },
        inactiveSwitchName(setting) {
            const switchSetting = setting.depends_on && this.settingsByKey[setting.depends_on]
            if (!switchSetting || asBoolean(this.shownValue(switchSetting.key))) {
                return null
            }
            return settingLabel(switchSetting)
        },
        selectPanel(panel) {
            if (this.searching) {
                const section = this.$el.querySelector(`#${this.panelId(panel)}`)
                if (section) {
                    section.scrollIntoView({ block: "start", behavior: "smooth" })
                }
                return
            }
            this.$emit("update:activePanel", panel)
            this.$refs.content.scrollTop = 0
        },
        // Shows the panel of a setting and scrolls the setting into view
        revealSetting(key) {
            const setting = this.settingsByKey[key]
            if (!setting) {
                return
            }
            if (!this.searching) {
                this.$emit("update:activePanel", setting.panel || "Other")
            }
            // The modal renders its content through a portal, a tick after the panel changed: wait for the row
            let attempts = 0
            const scrollToRow = () => {
                const row = this.$el.querySelector(`#setting-${key}`)
                if (row) {
                    row.scrollIntoView({ block: "center" })
                } else if (attempts < 10) {
                    attempts += 1
                    window.requestAnimationFrame(scrollToRow)
                }
            }
            this.$nextTick(scrollToRow)
        },
    },
}
</script>

<style scoped>
.settings-layout {
    display: grid;
    grid-template-columns: 13.5rem minmax(0, 1fr);
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
}

.settings-nav {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    padding: 1rem 0.75rem;
    border-right: 1px solid var(--health-rule);
    background: #fff;
    overflow-y: auto;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    width: 100%;
    padding: 0.5rem 0.7rem;
    border: none;
    border-radius: 0.4rem;
    background: none;
    color: #495057;
    font-size: 0.92rem;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-item:hover:not(:disabled) {
    background: #f1f3f6;
    color: var(--var-color-yankeesblue);
}

.nav-item:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: -2px;
}

.nav-item.is-active {
    background: var(--health-selected-bg);
    color: var(--var-color-yankeesblue);
    font-weight: 600;
}

.nav-item.is-empty {
    color: #adb5bd;
    cursor: default;
}

.nav-icon {
    width: 1.1rem;
    color: #8a939b;
    text-align: center;
}

.nav-item.is-active .nav-icon {
    color: var(--var-color-lapislazuli);
}

.nav-item.is-empty .nav-icon {
    color: #ced4da;
}

.nav-label {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.nav-count {
    min-width: 1.4rem;
    padding: 0 0.4rem;
    border-radius: 999px;
    background: #e9ecef;
    color: #495057;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.35rem;
    text-align: center;
    font-variant-numeric: tabular-nums;
}

.nav-item.is-empty .nav-count {
    background: #f4f5f7;
    color: #adb5bd;
}

.nav-pending {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--var-color-lapislazuli);
}

.settings-content {
    min-height: 0;
    padding: 1.25rem 1.5rem 1.75rem;
    background: var(--var-color-background);
    overflow-y: auto;
    scroll-padding-top: 1rem;
}

.settings-panel + .settings-panel {
    margin-top: 2rem;
}

.panel-head {
    margin-bottom: 0.9rem;
}

.panel-title {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: 0;
    color: var(--var-color-yankeesblue);
    font-size: 1.15rem;
    font-weight: 600;
}

.panel-icon {
    color: var(--var-color-lapislazuli);
    font-size: 0.95rem;
}

.settings-group + .settings-group {
    margin-top: 1.4rem;
}

.group-title {
    margin: 0 0 0.45rem 0.15rem;
    color: #6c757d;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.group-card {
    border: 1px solid var(--health-rule);
    border-radius: 0.5rem;
    background: #fff;
    box-shadow: 0 1px 2px rgba(33, 45, 64, 0.04);
    overflow: hidden;
}

.settings-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    min-height: 14rem;
    color: #6c757d;
    text-align: center;
}

.settings-state > i {
    color: #adb5bd;
    font-size: 1.4rem;
}

.settings-state.is-error > i {
    color: var(--health-critical);
}

@media (max-width: 767.98px) {
    .settings-layout {
        grid-template-columns: minmax(0, 1fr);
        grid-template-rows: auto minmax(0, 1fr);
    }

    .settings-nav {
        flex-direction: row;
        gap: 0.25rem;
        padding: 0.5rem 0.75rem;
        border-right: none;
        border-bottom: 1px solid var(--health-rule);
        overflow-x: auto;
        overflow-y: hidden;
    }

    .nav-item {
        flex: 0 0 auto;
        width: auto;
        padding: 0.4rem 0.65rem;
    }

    .settings-content {
        padding: 1rem 0.75rem 1.5rem;
    }

    /* The nav above names the panel already; search results keep their panel titles */
    .settings-layout:not(.is-searching) .panel-head {
        display: none;
    }
}
</style>
