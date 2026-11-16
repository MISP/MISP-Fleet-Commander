<template>
<Layout name="LayoutDefault">
    <div class="page-container lib-page">
        <header class="lib-header">
            <div>
                <h1 class="lib-title">Baselines</h1>
                <p class="lib-lede">
                    Your saved baselines and the presets that come with Fleet Commander. Importing one copies its
                    rules into a fleet's baseline: later changes here do not reach the fleet.
                </p>
            </div>
            <b-dropdown split right variant="primary" :disabled="!library" @click="openCreate">
                <template #button-content>
                    <i class="fas fa-plus mr-1" aria-hidden="true"></i>New saved baseline
                </template>
                <b-dropdown-item-button @click="openCreate">
                    <i class="fas fa-file fa-fw mr-1" aria-hidden="true"></i>Empty, to fill rule by rule
                </b-dropdown-item-button>
                <b-dropdown-item-button :disabled="!library || library.servers.length === 0" @click="openReference">
                    <i class="fas fa-server fa-fw mr-1" aria-hidden="true"></i>From a reference server…
                </b-dropdown-item-button>
            </b-dropdown>
        </header>

        <b-alert :show="!!error" variant="danger">
            Could not load the baselines: {{ error }}
            <b-button size="sm" variant="outline-danger" class="ml-2" @click="load">Try again</b-button>
        </b-alert>

        <div v-if="!library && !error" class="lib-loading" role="status">
            <b-spinner small class="mr-2"></b-spinner>Loading the baselines…
        </div>

        <div v-if="library" class="lib-layout">
            <nav class="lib-list" aria-label="Baselines">
                <b-input-group size="sm" class="lib-search">
                    <b-input-group-prepend is-text><i class="fas fa-search" aria-hidden="true"></i></b-input-group-prepend>
                    <b-form-input v-model="search" type="search" placeholder="Search baselines" aria-label="Search baselines"></b-form-input>
                </b-input-group>

                <section v-for="group in groups" :key="group.kind" class="lib-group" :aria-labelledby="`lib-group-${group.kind}`">
                    <h2 :id="`lib-group-${group.kind}`" class="lib-group-title">
                        <i :class="[group.icon, 'fa-fw']" aria-hidden="true"></i>{{ group.title }}
                        <span class="lib-group-count">{{ group.total }}</span>
                    </h2>
                    <p v-if="group.items.length === 0" class="lib-group-empty">{{ group.empty }}</p>
                    <router-link
                        v-for="item in group.items"
                        :key="item.key"
                        :to="{ query: { item: item.key } }"
                        :class="['lib-item', { active: item.key === selectedKey }]"
                        :aria-current="item.key === selectedKey ? 'true' : null"
                    >
                        <span class="lib-item-name">{{ item.name }}</span>
                        <span v-if="item.description" class="lib-item-description">{{ item.description }}</span>
                        <span class="lib-item-meta">
                            {{ ruleCount(item.rule_count) }}
                            <span class="lib-item-types" aria-hidden="true">
                                <i v-for="chip in chips(item)" :key="chip.type" :class="chip.icon" :title="chip.text"></i>
                            </span>
                            <span v-if="item.updated" class="lib-item-when">· {{ fromNow(item.updated) }}</span>
                        </span>
                    </router-link>
                </section>
            </nav>

            <section ref="detail" class="lib-detail" :aria-busy="detailLoading ? 'true' : 'false'">
                <div v-if="!selected" class="lib-none">
                    <i class="fas fa-ruler-combined lib-none-icon" aria-hidden="true"></i>
                    <p>Pick a baseline to see its rules.</p>
                </div>
                <template v-else>
                    <header class="lib-detail-head">
                        <div class="lib-detail-titles">
                            <span class="lib-kind"><i :class="[kindMeta.icon, 'mr-1']" aria-hidden="true"></i>{{ kindMeta.label }}</span>
                            <h2 class="lib-detail-name">{{ selected.name }}</h2>
                            <p v-if="selected.description" class="lib-detail-description">{{ selected.description }}</p>
                            <p class="lib-detail-meta">
                                {{ ruleCount(selected.rule_count) }}
                                <template v-if="selected.kind === 'saved'"> · saved {{ dateText(selected.created) }}<template v-if="selected.updated !== selected.created">, updated {{ dateText(selected.updated) }}</template></template>
                                <template v-else> · ships with Fleet Commander, read-only: save a copy to change it</template>
                            </p>
                        </div>
                        <div class="lib-detail-actions">
                            <b-button variant="primary" :disabled="library.fleets.length === 0 || selected.rule_count === 0" @click="openApply">
                                <i class="fas fa-file-import mr-1" aria-hidden="true"></i>Import into a fleet…
                            </b-button>
                            <template v-if="selected.kind === 'saved'">
                                <b-button variant="outline-secondary" @click="openEdit">
                                    <i class="fas fa-pen mr-1" aria-hidden="true"></i>Rename
                                </b-button>
                                <b-button variant="outline-danger" :disabled="deleting" @click="remove">
                                    <i class="fas fa-trash-can mr-1" aria-hidden="true"></i>Delete
                                </b-button>
                            </template>
                            <b-button v-else variant="outline-secondary" :disabled="!detail" @click="openCopy">
                                <i class="fas fa-copy mr-1" aria-hidden="true"></i>Save a copy…
                            </b-button>
                        </div>
                    </header>

                    <b-alert :show="!!detailError" variant="danger">
                        {{ detailError }}
                        <b-button size="sm" variant="outline-danger" class="ml-2" @click="loadDetail">Try again</b-button>
                    </b-alert>
                    <div v-if="detailLoading && !detail" class="lib-loading" role="status">
                        <b-spinner small class="mr-2"></b-spinner>Loading its rules…
                    </div>

                    <template v-if="detail">
                        <div v-if="editable" class="lib-rules-head">
                            <h3 class="lib-rules-title">Rules</h3>
                            <b-dropdown split right size="sm" variant="outline-primary" @click="openAddRule">
                                <template #button-content>
                                    <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add rule
                                </template>
                                <b-dropdown-item-button :disabled="library.servers.length === 0" @click="openReferenceAdd">
                                    <i class="fas fa-server fa-fw mr-1" aria-hidden="true"></i>From a reference server…
                                </b-dropdown-item-button>
                            </b-dropdown>
                        </div>

                        <div v-if="detail.rules.length === 0" class="lib-empty">
                            <i class="fas fa-ruler-combined lib-none-icon" aria-hidden="true"></i>
                            <p class="lib-empty-text">No rules yet. Add them one by one, or pick them on one of your servers.</p>
                            <div class="lib-empty-actions">
                                <b-button variant="primary" @click="openAddRule">
                                    <i class="fas fa-plus mr-1" aria-hidden="true"></i>Add a rule
                                </b-button>
                                <b-button variant="outline-primary" :disabled="library.servers.length === 0" @click="openReferenceAdd">
                                    <i class="fas fa-server mr-1" aria-hidden="true"></i>From a reference server
                                </b-button>
                            </div>
                        </div>

                        <div v-for="section in sections" :key="section.type" class="lib-section">
                            <h3 class="lib-section-title">
                                <i :class="[section.icon, 'fa-fw mr-1']" aria-hidden="true"></i>{{ section.label }}
                                <span class="lib-section-count">{{ section.items.length }}</span>
                            </h3>
                            <RuleList :items="section.items" :editable="editable" @edit="openEditRule" @delete="deleteRule"></RuleList>
                        </div>
                    </template>
                </template>
            </section>
        </div>

        <ImportBaselineModal
            v-if="selected"
            modal-id="modal-library-apply"
            :fixed-source="{ kind: selected.kind, id: selected.id }"
            @applied="onApplied"
        ></ImportBaselineModal>
        <ReferenceImportModal
            modal-id="modal-library-reference"
            save-as
            :servers="referenceServers"
            @saved="onCreated"
        ></ReferenceImportModal>
        <template v-if="editable && detail">
            <ReferenceImportModal
                modal-id="modal-library-reference-add"
                :saved-id="selected.id"
                :servers="referenceServers"
                :rules="detail.rules"
                @saved="onRulesChanged"
            ></ReferenceImportModal>
            <RuleModal
                :saved-id="selected.id"
                :types="types"
                :servers="referenceServers"
                :rules="detail.rules"
                :rule="editingRule"
                @saved="onRulesChanged"
            ></RuleModal>
        </template>

        <b-modal
            id="modal-library-edit"
            :title="editTitle"
            cancel-variant="outline-secondary"
            @shown="$refs.editName && $refs.editName.select()"
        >
            <b-form-group label="Name" label-for="lib-edit-name" :state="edit.nameError ? false : null" :invalid-feedback="edit.nameError">
                <b-form-input
                    id="lib-edit-name"
                    ref="editName"
                    v-model="edit.name"
                    maxlength="120"
                    :state="edit.nameError ? false : null"
                    @input="edit.nameError = null"
                    @keydown.enter.prevent="saveEdit"
                ></b-form-input>
            </b-form-group>
            <b-form-group label="Description" label-for="lib-edit-description" :description="`${edit.description.length} / 500`" class="mb-0">
                <b-form-textarea id="lib-edit-description" v-model="edit.description" rows="2" max-rows="5" maxlength="500"></b-form-textarea>
            </b-form-group>
            <b-alert :show="!!edit.error" variant="danger" class="mt-3 mb-0">{{ edit.error }}</b-alert>
            <template #modal-footer="{ cancel }">
                <b-button variant="outline-secondary" @click="cancel()">Cancel</b-button>
                <b-button variant="primary" :disabled="edit.saving || edit.name.trim() === ''" @click="saveEdit">
                    <b-spinner v-if="edit.saving" small class="mr-1"></b-spinner>{{ edit.mode === 'rename' ? 'Save' : 'Create' }}
                </b-button>
            </template>
        </b-modal>
    </div>
</Layout>
</template>

<script>
import moment from "moment"
import Layout from "@/components/layout/Layout.vue"
import api from "@/api/baselines"
import ImportBaselineModal from "@/components/baselines/ImportBaselineModal.vue"
import ReferenceImportModal from "@/components/baselines/ReferenceImportModal.vue"
import RuleList from "@/components/baselines/RuleList.vue"
import RuleModal from "@/components/baselines/RuleModal.vue"
import { SOURCE_KINDS, TYPE_META, expectedText, ruleCountText, ruleTitle, sourceKey, typeSummary } from "@/components/baselines/baselineFormat"

const SECTION_LABELS = {
    version_min: "MISP version",
    setting: "Settings",
    taxonomy_enabled: "Taxonomies",
    galaxy_enabled: "Galaxies",
    object_template_active: "Object templates",
    organisation: "Organisations",
    sharing_group: "Sharing groups",
    custom_galaxy: "Custom galaxies",
}

export default {
    name: "BaselineLibrary",
    components: { ImportBaselineModal, Layout, ReferenceImportModal, RuleList, RuleModal },
    data() {
        return {
            library: null,
            error: null,
            search: "",
            detail: null,
            detailLoading: false,
            detailError: null,
            detailToken: 0,
            deleting: false,
            types: null,
            editingRule: null,
            // `mode`: create (empty), copy (of a preset) or rename
            edit: { mode: "rename", name: "", description: "", nameError: null, error: null, saving: false },
        }
    },
    computed: {
        items() {
            if (!this.library) {
                return []
            }
            const withKey = kind => item => ({ ...item, kind, key: sourceKey({ kind, id: item.id }) })
            return this.library.saved.map(withKey("saved")).concat(this.library.presets.map(withKey("preset")))
        },
        groups() {
            const search = this.search.trim().toLowerCase()
            const matches = item => search === "" || `${item.name} ${item.description || ""}`.toLowerCase().includes(search)
            return ["saved", "preset"].map((kind) => {
                const all = this.items.filter(item => item.kind === kind)
                return {
                    kind,
                    title: SOURCE_KINDS[kind].plural,
                    icon: SOURCE_KINDS[kind].icon,
                    total: all.length,
                    items: all.filter(matches),
                    empty: kind === "saved" && all.length === 0
                        ? "None yet. Create one here, save one from a fleet's Baseline tab, or copy a preset."
                        : "Nothing matches.",
                }
            })
        },
        selectedKey() {
            const key = this.$route.query.item
            if (typeof key === "string" && this.items.some(item => item.key === key)) {
                return key
            }
            return this.items.length > 0 ? this.items[0].key : ""
        },
        selected() {
            return this.items.find(item => item.key === this.selectedKey) || null
        },
        editable() {
            return !!this.selected && this.selected.kind === "saved"
        },
        editTitle() {
            return { create: "New saved baseline", copy: "Save a copy of the preset", rename: "Rename the saved baseline" }[this.edit.mode]
        },
        kindMeta() {
            return this.selected ? SOURCE_KINDS[this.selected.kind] : null
        },
        sections() {
            if (!this.detail) {
                return []
            }
            return Object.keys(SECTION_LABELS)
                .map(type => ({
                    type,
                    label: SECTION_LABELS[type],
                    icon: TYPE_META[type].icon,
                    items: this.detail.rules
                        .filter(rule => rule.type === type)
                        .map((rule, index) => ({ id: `${rule.type}|${rule.key}|${index}`, rule })),
                }))
                .filter(section => section.items.length > 0)
        },
        referenceServers() {
            if (!this.library) {
                return []
            }
            return this.library.servers.map(server => ({
                id: server.id,
                name: server.fleet_name ? `${server.name} — ${server.fleet_name}` : server.name,
            }))
        },
    },
    watch: {
        selectedKey(key, previous) {
            this.loadDetail()
            // Stacked under the list on narrow screens: show what was picked
            if (previous && window.innerWidth < 992) {
                this.$nextTick(() => {
                    if (this.$refs.detail) {
                        this.$refs.detail.scrollIntoView({ block: "start", behavior: "smooth" })
                    }
                })
            }
        },
    },
    created() {
        this.load()
        api.types().then((types) => { this.types = types }).catch(() => {})
    },
    methods: {
        load() {
            this.error = null
            return api.library()
                .then((library) => {
                    this.library = library
                    this.loadDetail()
                })
                .catch((error) => {
                    this.error = error.message
                })
        },
        loadDetail() {
            const token = ++this.detailToken
            const item = this.selected
            this.detailError = null
            if (!item) {
                this.detail = null
                return
            }
            if (this.detail && sourceKey(this.detail) !== item.key) {
                this.detail = null
            }
            this.detailLoading = true
            const request = item.kind === "preset" ? api.preset(item.id) : api.saved(item.id)
            request
                .then((detail) => {
                    if (token === this.detailToken) {
                        this.detail = detail
                    }
                })
                .catch((error) => {
                    if (token === this.detailToken) {
                        this.detailError = error.message
                    }
                })
                .finally(() => {
                    if (token === this.detailToken) {
                        this.detailLoading = false
                    }
                })
        },
        chips(item) {
            return typeSummary(item.types)
        },
        ruleCount(count) {
            return ruleCountText(count)
        },
        fromNow(timestamp) {
            return moment.unix(timestamp).fromNow()
        },
        dateText(timestamp) {
            return moment.unix(timestamp).format("D MMM YYYY")
        },
        select(key) {
            if (this.$route.query.item !== key) {
                this.$router.replace({ query: { ...this.$route.query, item: key } }).catch(() => {})
            }
        },
        openApply() {
            this.$bvModal.show("modal-library-apply")
        },
        openReference() {
            this.$bvModal.show("modal-library-reference")
        },
        openEditModal(mode, name, description) {
            this.edit = { mode, name, description, nameError: null, error: null, saving: false }
            this.$bvModal.show("modal-library-edit")
        },
        openEdit() {
            this.openEditModal("rename", this.selected.name, this.selected.description || "")
        },
        openCreate() {
            this.openEditModal("create", "", "")
        },
        openCopy() {
            this.openEditModal("copy", `${this.selected.name} (copy)`, this.selected.description || "")
        },
        saveEdit() {
            if (this.edit.saving || this.edit.name.trim() === "") {
                return
            }
            this.edit.saving = true
            const body = { name: this.edit.name, description: this.edit.description }
            let request
            if (this.edit.mode === "rename") {
                request = api.updateSaved(this.selected.id, body)
            } else if (this.edit.mode === "copy") {
                // The preset's rules as it ships them, now the user's to change
                const rules = this.detail.rules.map(rule => ({
                    type: rule.type, key: rule.key, label: rule.label, expected: rule.expected,
                    comparator: rule.comparator, severity: rule.severity, note: rule.note,
                }))
                request = api.createSaved({ ...body, rules })
            } else {
                request = api.createSaved(body)
            }
            request
                .then((saved) => {
                    this.$bvModal.hide("modal-library-edit")
                    return this.load().then(() => this.select(sourceKey({ kind: "saved", id: saved.id })))
                })
                .catch((error) => {
                    if (error.field === "name") {
                        this.edit.nameError = error.message
                    } else {
                        this.edit.error = error.message
                    }
                })
                .finally(() => {
                    this.edit.saving = false
                })
        },
        remove() {
            const item = this.selected
            this.$bvModal.msgBoxConfirm(`“${item.name}” and its ${ruleCountText(item.rule_count)} will be deleted. Fleets it was imported into keep their rules.`, {
                title: "Delete this saved baseline?",
                okTitle: "Delete",
                okVariant: "danger",
                cancelVariant: "outline-secondary",
                centered: true,
            }).then((confirmed) => {
                if (!confirmed) {
                    return
                }
                this.deleting = true
                api.deleteSaved(item.id)
                    .then(() => {
                        this.$router.replace({ query: {} }).catch(() => {})
                        return this.load()
                    })
                    .catch((error) => {
                        this.$bvToast.toast(error.message, { title: "Could not delete the saved baseline", variant: "danger" })
                    })
                    .finally(() => {
                        this.deleting = false
                    })
            })
        },
        onApplied({ fleet, source, baseline }) {
            this.$bvToast.toast(`${fleet.name} now has ${ruleCountText(baseline.rules.length)}, from “${source.name}”. Open its baseline to see the drift.`, {
                title: "Baseline imported",
                variant: "success",
                to: { name: "fleet.view", params: { fleet_id: fleet.id }, query: { tab: "baseline" } },
            })
            this.load()
        },
        openAddRule() {
            this.editingRule = null
            this.$nextTick(() => this.$bvModal.show("modal-baseline-rule"))
        },
        openEditRule(rule) {
            this.editingRule = rule
            this.$nextTick(() => this.$bvModal.show("modal-baseline-rule"))
        },
        openReferenceAdd() {
            this.$bvModal.show("modal-library-reference-add")
        },
        // Counts and dates change in the list too
        onRulesChanged() {
            this.load()
        },
        deleteRule(rule) {
            this.$bvModal.msgBoxConfirm(`${ruleTitle(rule)} (${expectedText(rule)}) will be removed from “${this.selected.name}”. Fleets it was imported into keep their rules.`, {
                title: "Remove this rule?",
                okTitle: "Remove",
                okVariant: "danger",
                cancelVariant: "outline-secondary",
                centered: true,
            }).then((confirmed) => {
                if (!confirmed) {
                    return
                }
                api.deleteRule(rule.id)
                    .then(() => this.load())
                    .catch((error) => {
                        this.$bvToast.toast(error.message, { title: "Could not remove the rule", variant: "danger" })
                    })
            })
        },
        onCreated(saved) {
            this.load().then(() => this.select(sourceKey({ kind: "saved", id: saved.id })))
        },
    },
}
</script>

<style scoped>
.lib-page {
    max-width: 1280px;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
}

.lib-header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    margin-bottom: 1.25rem;
}

.lib-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    margin: 0;
}

.lib-lede {
    color: #5a6270;
    margin: 0.25rem 0 0;
    max-width: 720px;
    font-size: 0.92rem;
}

.lib-loading {
    padding: 1.5rem 0;
    color: #4a5260;
}

.lib-layout {
    display: grid;
    grid-template-columns: minmax(16rem, 21rem) 1fr;
    gap: 1.25rem;
    align-items: start;
}

.lib-list {
    position: sticky;
    top: 1rem;
}

.lib-search {
    margin-bottom: 0.9rem;
}

.lib-group + .lib-group {
    margin-top: 1.25rem;
}

.lib-group-title {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin: 0 0 0.4rem;
    padding: 0 0.25rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.lib-group-count {
    margin-left: auto;
    font-weight: 600;
    color: #8a919c;
    font-variant-numeric: tabular-nums;
}

.lib-group-empty {
    margin: 0;
    padding: 0.6rem 0.75rem;
    font-size: 0.85rem;
    color: #5a6270;
    background: #fff;
    border: 1px dashed var(--health-rule);
    border-radius: 6px;
}

.lib-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.35rem;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    color: var(--var-color-yankeesblue);
    text-decoration: none;
}

.lib-item:hover {
    border-color: #c5cbd3;
    text-decoration: none;
    color: var(--var-color-yankeesblue);
}

.lib-item.active {
    border-color: var(--var-color-lapislazuli);
    box-shadow: inset 3px 0 0 var(--var-color-lapislazuli);
    background: var(--health-focus-bg);
}

.lib-item:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.lib-item-name {
    font-weight: 600;
    font-size: 0.92rem;
}

.lib-item-description {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 0.8rem;
    color: #5a6270;
}

.lib-item-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.76rem;
    color: #6c737d;
    font-variant-numeric: tabular-nums;
}

.lib-item-types {
    display: inline-flex;
    gap: 0.35rem;
    color: #8a919c;
}

.lib-detail {
    min-width: 0;
    padding: 1.25rem 1.5rem 1.5rem;
    background: #fff;
    border: 1px solid var(--health-rule);
    border-radius: 8px;
}

.lib-none {
    padding: 3rem 1rem;
    text-align: center;
    color: #5a6270;
}

.lib-none-icon {
    font-size: 1.6rem;
    color: #a0a6ae;
    margin-bottom: 0.5rem;
}

.lib-detail-head {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    margin-bottom: 1.25rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--health-rule);
}

.lib-detail-titles {
    flex: 1 1 22rem;
    min-width: 0;
}

.lib-kind {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--var-color-lapislazuli);
}

.lib-detail-name {
    margin: 0.15rem 0 0.35rem;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--var-color-yankeesblue);
    overflow-wrap: anywhere;
}

.lib-detail-description {
    margin: 0 0 0.4rem;
    color: #3b4250;
    max-width: 52rem;
}

.lib-detail-meta {
    margin: 0;
    font-size: 0.85rem;
    color: #5a6270;
}

.lib-detail-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.lib-rules-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.lib-rules-title {
    margin: 0;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #5a6270;
}

.lib-empty {
    padding: 2rem 1rem;
    text-align: center;
    border: 1px dashed var(--health-rule);
    border-radius: 6px;
}

.lib-empty-text {
    margin: 0 auto 1rem;
    max-width: 28rem;
    color: #4a5260;
}

.lib-empty-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
}

.lib-section {
    margin-bottom: 1rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    overflow: hidden;
}

.lib-section-title {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    margin: 0;
    padding: 0.45rem 0.75rem;
    background: #f6f7f9;
    border-bottom: 1px solid var(--health-rule);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--var-color-yankeesblue);
}

.lib-section-title i {
    color: #6c737d;
}

.lib-section-count {
    font-weight: 500;
    color: #5a6270;
    font-variant-numeric: tabular-nums;
}

@media (max-width: 991.98px) {
    .lib-layout {
        grid-template-columns: 1fr;
    }

    .lib-list {
        position: static;
    }
}

@media (max-width: 575.98px) {
    .lib-page {
        padding: 1rem 0.75rem 2rem;
    }

    .lib-detail {
        padding: 1rem;
    }

    .lib-header .btn,
    .lib-detail-actions .btn {
        flex: 1 1 auto;
    }
}
</style>
