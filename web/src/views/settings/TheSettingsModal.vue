<template>
    <b-modal
        id="modal-settings"
        ref="modal"
        size="xl"
        modal-class="mfc-settings-modal"
        body-class="settings-body"
        aria-label="Settings"
        @show="onShow"
        @shown="onShown"
        @hide="onHide"
        @hidden="shown = false"
    >
        <template #modal-header="{ close }">
            <div class="settings-header">
                <div class="settings-heading">
                    <h5 class="settings-title">
                        <i class="fas fa-gear" aria-hidden="true"></i>Settings
                    </h5>
                    <p class="settings-subtitle">For the whole instance: every user works with the same values.</p>
                </div>
                <div class="settings-search">
                    <i class="fas fa-magnifying-glass search-icon" aria-hidden="true"></i>
                    <b-form-input
                        ref="search"
                        v-model="query"
                        type="search"
                        size="sm"
                        placeholder="Search settings"
                        aria-label="Search settings"
                        autocomplete="off"
                        @keydown.esc.stop.prevent="query ? query = '' : close()"
                    ></b-form-input>
                </div>
                <button type="button" class="close settings-close" aria-label="Close" @click="close()">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        </template>

        <settingView
            ref="view"
            :groups="groups"
            :values="settingValues"
            :drafts="drafts"
            :errors="errors"
            :active-panel.sync="activePanel"
            :query="query"
            :read-only="!isAdmin"
            :highlight-key="highlightKey"
            :loading="loading"
            :load-error="loadError"
            @change="setDraft"
            @revert="revert"
            @reset-default="resetToDefault"
            @clear-query="query = ''"
            @retry="refreshSettings"
        ></settingView>

        <template #modal-footer="{ close }">
            <div class="settings-footer">
                <div class="footer-status" aria-live="polite">
                    <template v-if="!isAdmin">
                        <i class="fas fa-lock" aria-hidden="true"></i>
                        <span class="status-sentence">Only administrators can change these settings.</span>
                    </template>
                    <template v-else-if="pendingCount > 0">
                        <span class="status-dot" aria-hidden="true"></span>
                        <span>{{ pendingCount }} unsaved {{ pendingCount === 1 ? "change" : "changes" }}</span>
                        <span v-if="invalidCount > 0" class="status-invalid">
                            · {{ invalidCount }} to fix
                        </span>
                    </template>
                    <template v-else-if="savedCount > 0">
                        <i class="fas fa-circle-check status-saved" aria-hidden="true"></i>
                        <span>{{ savedCount === 1 ? "Change saved" : `${savedCount} changes saved` }}</span>
                    </template>
                    <template v-else>
                        <span class="text-muted">Changes apply once saved.</span>
                    </template>
                </div>
                <div class="footer-actions">
                    <template v-if="isAdmin && pendingCount > 0">
                        <b-button variant="link" class="discard-button" :disabled="saving" @click="discardAll">Discard</b-button>
                        <b-button
                            variant="primary"
                            :disabled="saving || invalidCount > 0"
                            :title="invalidCount > 0 ? 'Fix the highlighted values first' : null"
                            @click="saveAll"
                        >
                            <b-spinner v-if="saving" small class="mr-1"></b-spinner>
                            {{ saving ? "Saving…" : pendingCount === 1 ? "Save change" : `Save ${pendingCount} changes` }}
                        </b-button>
                    </template>
                    <b-button v-else variant="outline-secondary" @click="close()">Close</b-button>
                </div>
            </div>
        </template>
    </b-modal>
</template>

<script>
import { mapGetters } from "vuex"
import settingView from "@/components/ui/SettingsView.vue"
import { OPEN_SETTINGS_EVENT, groupSettings, isSameValue, saveInOrder, toSaved, validateValue } from "./settingsModel"

export default {
    name: "TheSettingsModal",
    components: {
        settingView,
    },
    data: function () {
        return {
            loading: false,
            loadError: null,
            query: "",
            activePanel: null,
            // Unsaved changes by setting name, as the fields hold them
            drafts: {},
            // What the server answered for the changes it refused, by setting name
            serverErrors: {},
            saving: false,
            savedCount: 0,
            // Setting to show and highlight when the modal opens
            focusKey: null,
            highlightKey: null,
            confirmingClose: false,
            // Scrolling to a setting only works once the modal is displayed
            shown: false,
        }
    },
    computed: {
        ...mapGetters({
            getSettings: "settings/getSettings",
            settingValues: "settings/settingValues",
            isAdmin: "auth/isAdmin",
        }),
        groups() {
            return groupSettings(this.getSettings)
        },
        pendingKeys() {
            return Object.keys(this.drafts).filter(key => this.getSettings[key] !== undefined)
        },
        pendingCount() {
            return this.pendingKeys.length
        },
        clientErrors() {
            const errors = {}
            this.pendingKeys.forEach(key => {
                const error = validateValue(this.getSettings[key], this.drafts[key])
                if (error) {
                    errors[key] = error
                }
            })
            return errors
        },
        errors() {
            return { ...this.serverErrors, ...this.clientErrors }
        },
        invalidCount() {
            return Object.keys(this.clientErrors).length
        },
    },
    methods: {
        refreshSettings() {
            this.loading = true
            this.loadError = null
            return this.$store.dispatch("settings/refreshSettings")
                .then(() => {
                    // A change someone else saved meanwhile is not pending anymore
                    Object.keys(this.drafts).forEach(key => {
                        const setting = this.getSettings[key]
                        if (setting === undefined || isSameValue(setting, this.drafts[key], this.settingValues[key])) {
                            this.$delete(this.drafts, key)
                        }
                    })
                })
                .catch((error) => {
                    this.loadError = typeof error === "string" ? error : "the server did not answer"
                })
                .finally(() => {
                    this.loading = false
                })
        },
        setDraft(key, value) {
            const setting = this.getSettings[key]
            if (setting === undefined) {
                return
            }
            this.$delete(this.serverErrors, key)
            this.savedCount = 0
            if (isSameValue(setting, value, this.settingValues[key])) {
                this.$delete(this.drafts, key)
            } else {
                this.$set(this.drafts, key, value)
            }
        },
        revert(key) {
            this.$delete(this.drafts, key)
            this.$delete(this.serverErrors, key)
        },
        resetToDefault(key) {
            const setting = this.getSettings[key]
            if (setting !== undefined) {
                this.setDraft(key, setting.default)
            }
        },
        discardAll() {
            this.drafts = {}
            this.serverErrors = {}
        },
        async saveAll() {
            if (this.saving || this.pendingCount === 0 || this.invalidCount > 0) {
                return
            }
            this.saving = true
            const changes = this.pendingKeys.map(key => ({ key, value: toSaved(this.getSettings[key], this.drafts[key]) }))
            const { saved, failed } = await saveInOrder(changes, (name, value) => this.$store.dispatch("settings/saveSetting", { name, value }))
            saved.forEach(key => this.$delete(this.drafts, key))
            this.serverErrors = failed
            await this.refreshSettings()
            this.saving = false
            this.savedCount = Object.keys(failed).length === 0 ? saved.length : 0
            const failedKeys = Object.keys(failed)
            if (failedKeys.length > 0) {
                const count = failedKeys.length
                this.$bvToast.toast(`${count === 1 ? "One change was" : `${count} changes were`} refused: the reason is under the field.`, {
                    title: saved.length > 0 ? `${saved.length} saved, ${count} not saved` : "Settings not saved",
                    variant: "danger",
                })
                this.$refs.view.revealSetting(failedKeys[0])
            }
        },
        onShow() {
            this.query = ""
            this.savedCount = 0
            this.serverErrors = {}
            this.refreshSettings().then(() => {
                if (this.activePanel === null || !this.groups.some(panel => panel.panel === this.activePanel)) {
                    this.activePanel = this.groups.length > 0 ? this.groups[0].panel : null
                }
                this.revealFocus()
            })
        },
        onShown() {
            this.shown = true
            this.revealFocus()
        },
        revealFocus() {
            const key = this.focusKey
            if (!this.shown || !key || this.getSettings[key] === undefined || !this.$refs.view) {
                return
            }
            this.focusKey = null
            this.$refs.view.revealSetting(key)
            this.highlightKey = null
            this.$nextTick(() => {
                this.highlightKey = key
                setTimeout(() => {
                    if (this.highlightKey === key) {
                        this.highlightKey = null
                    }
                }, 2600)
            })
        },
        onHide(bvEvent) {
            if (this.pendingCount === 0 || this.saving) {
                if (this.saving) {
                    bvEvent.preventDefault()
                }
                return
            }
            bvEvent.preventDefault()
            if (this.confirmingClose) {
                return
            }
            this.confirmingClose = true
            const count = this.pendingCount
            this.$bvModal.msgBoxConfirm(`${count === 1 ? "One change has" : `${count} changes have`} not been saved and will be lost.`, {
                title: "Discard unsaved changes?",
                okTitle: "Discard",
                okVariant: "danger",
                cancelTitle: "Keep editing",
                cancelVariant: "outline-secondary",
                centered: true,
                size: "sm",
                footerClass: "p-2",
            }).then((discard) => {
                if (discard) {
                    this.discardAll()
                    this.$bvModal.hide("modal-settings")
                }
            }).finally(() => {
                this.confirmingClose = false
            })
        },
        // Others open the modal on one setting with this.$root.$emit(OPEN_SETTINGS_EVENT, { focus: "<setting name>" })
        open({ focus } = {}) {
            this.focusKey = focus || null
            if (this.$refs.modal && this.$refs.modal.isVisible) {
                this.revealFocus()
            } else {
                this.$bvModal.show("modal-settings")
            }
        },
    },
    mounted() {
        this.refreshSettings()
        this.$root.$on(OPEN_SETTINGS_EVENT, this.open)
    },
    beforeDestroy() {
        this.$root.$off(OPEN_SETTINGS_EVENT, this.open)
    },
}
</script>

<style>
/* The modal's frame is rendered outside this component: the rules are scoped by the modal's class instead */
@media (min-width: 768px) {
    .mfc-settings-modal .modal-xl {
        max-width: min(1140px, calc(100vw - 3rem));
    }
}

.mfc-settings-modal .modal-content {
    overflow: hidden;
    border: none;
    border-radius: 0.6rem;
    box-shadow: 0 1.25rem 3rem rgba(33, 45, 64, 0.22);
}

.mfc-settings-modal .modal-header {
    padding: 0;
    border-bottom: 1px solid var(--health-rule);
}

.mfc-settings-modal .settings-body {
    display: flex;
    height: min(72vh, 46rem);
    padding: 0;
}

.mfc-settings-modal .modal-footer {
    padding: 0;
    border-top: 1px solid var(--health-rule);
}

.mfc-settings-modal .settings-header {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    width: 100%;
    padding: 0.9rem 1rem 0.9rem 1.4rem;
}

.mfc-settings-modal .settings-heading {
    flex: 1 1 auto;
    min-width: 0;
}

.mfc-settings-modal .settings-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 0;
    color: var(--var-color-yankeesblue);
    font-size: 1.2rem;
    font-weight: 600;
}

.mfc-settings-modal .settings-title i {
    color: var(--var-color-lapislazuli);
    font-size: 1.05rem;
}

.mfc-settings-modal .settings-subtitle {
    margin: 0.1rem 0 0;
    color: #6c757d;
    font-size: 0.82rem;
}

.mfc-settings-modal .settings-search {
    position: relative;
    flex: 0 1 17rem;
}

.mfc-settings-modal .settings-search .search-icon {
    position: absolute;
    top: 50%;
    left: 0.7rem;
    color: #9aa1a7;
    font-size: 0.8rem;
    transform: translateY(-50%);
    pointer-events: none;
}

.mfc-settings-modal .settings-search .form-control {
    padding-left: 2rem;
    border-radius: 999px;
    background: #f4f6f8;
    border-color: transparent;
}

.mfc-settings-modal .settings-search .form-control:focus {
    background: #fff;
    border-color: #80bdff;
}

.mfc-settings-modal .modal-header .settings-close {
    float: none;
    margin: 0;
    padding: 0.25rem 0.5rem;
    line-height: 1;
}

.mfc-settings-modal .settings-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    width: 100%;
    min-height: 3.6rem;
    margin: 0;
    padding: 0.6rem 1rem 0.6rem 1.4rem;
}

.mfc-settings-modal .footer-status {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.1rem 0.45rem;
    min-width: 0;
    color: #495057;
    font-size: 0.88rem;
}

.mfc-settings-modal .footer-status > span {
    white-space: nowrap;
}

.mfc-settings-modal .footer-status > .status-sentence {
    white-space: normal;
}

.mfc-settings-modal .footer-status .fa-lock {
    color: #9aa1a7;
}

.mfc-settings-modal .status-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: var(--var-color-lapislazuli);
}

.mfc-settings-modal .status-invalid {
    color: var(--health-critical-ink);
    font-weight: 600;
}

.mfc-settings-modal .status-saved {
    color: var(--health-ok);
}

.mfc-settings-modal .footer-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 0 0 auto;
}

.mfc-settings-modal .discard-button {
    color: #5b636b;
}

@media (max-width: 767.98px) {
    .mfc-settings-modal .settings-header {
        flex-wrap: wrap;
        gap: 0.6rem 1rem;
        padding: 0.75rem 0.75rem 0.75rem 1rem;
    }

    .mfc-settings-modal .settings-search {
        order: 3;
        flex: 1 1 100%;
    }

    .mfc-settings-modal .settings-subtitle {
        display: none;
    }

    .mfc-settings-modal .settings-body {
        height: calc(100vh - 13rem);
    }

    .mfc-settings-modal .settings-footer {
        padding: 0.5rem 0.75rem 0.5rem 1rem;
    }
}
</style>
