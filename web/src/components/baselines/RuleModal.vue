<template>
    <b-modal
        id="modal-baseline-rule"
        :title="editing ? 'Edit rule' : 'Add a rule'"
        size="lg"
        :ok-title="editing ? 'Save' : 'Add rule'"
        ok-variant="primary"
        cancel-variant="outline-secondary"
        :ok-disabled="saving || !canSubmit"
        :busy="saving"
        @show="onShow"
        @shown="focusFirst"
        @ok="submit"
    >
        <b-form class="rule-form" novalidate @submit.prevent="submit">
            <div class="rule-form-row">
                <b-form-group label="Checks" label-for="rule-type" class="rule-type-group">
                    <b-form-select
                        id="rule-type"
                        ref="type"
                        v-model="form.type"
                        :options="typeOptions"
                        :disabled="editing"
                        @change="onTypeChange"
                    ></b-form-select>
                </b-form-group>
                <b-form-group
                    v-if="!editing && servers.length > 0"
                    label="Values from"
                    label-for="rule-reference"
                    class="rule-reference-group"
                    :description="referenceDescription"
                >
                    <b-form-select
                        id="rule-reference"
                        v-model="referenceId"
                        :options="serverOptions"
                        @change="loadReference"
                    ></b-form-select>
                </b-form-group>
                <b-form-group
                    v-else-if="editing && isItem && servers.length > 0"
                    label="Take it again from"
                    label-for="rule-reference"
                    class="rule-reference-group"
                    :description="takeAgainMessage"
                >
                    <div class="rule-take-again">
                        <b-form-select id="rule-reference" v-model="referenceId" :options="serverOptions"></b-form-select>
                        <b-button variant="outline-primary" :disabled="referenceLoading || referenceId === null" @click="takeAgain">
                            <b-spinner v-if="referenceLoading" small class="mr-1"></b-spinner>Take again
                        </b-button>
                    </div>
                </b-form-group>
            </div>

            <b-form-group
                v-if="keyLabel"
                :label="keyLabel"
                label-for="rule-key"
                :invalid-feedback="errors.key"
                :state="errors.key ? false : null"
                :description="keyDescription"
            >
                <template v-if="editing">
                    <div class="rule-fixed-key">
                        <span :class="{ 'key-mono': form.type === 'setting' }">{{ form.label || form.key }}</span>
                        <span v-if="form.label && form.label !== form.key" class="text-muted key-mono small ml-2">{{ form.key }}</span>
                    </div>
                </template>
                <KeyPicker
                    v-else
                    ref="key"
                    v-model="form.key"
                    input-id="rule-key"
                    :items="keyItems"
                    :loading="referenceLoading && keyItems.length === 0"
                    :loading-text="`Listing from ${referenceName}…`"
                    :placeholder="keyPlaceholder"
                    :mono="form.type === 'setting'"
                    :state="errors.key ? false : null"
                    @select="onKeySelected"
                    @input="onKeyTyped"
                ></KeyPicker>
            </b-form-group>

            <b-alert :show="serverSpecific" variant="warning" class="rule-specific">
                <div><strong>{{ form.key }}</strong> is usually different on each server: its URL, organisation or own keys.
                    One value for the whole fleet is rarely right.</div>
                <b-form-checkbox v-model="form.force" class="mt-2">Keep this rule anyway</b-form-checkbox>
            </b-alert>
            <b-alert :show="isSecret" variant="danger">
                <strong>{{ form.key }}</strong> holds a secret. Baselines do not manage secrets.
            </b-alert>

            <b-form-group
                v-if="form.type === 'organisation'"
                label="Must have"
                class="rule-item-group"
                :invalid-feedback="errors.expected"
                :state="errors.expected ? false : null"
                description="Empty fields are not checked. An organisation is usually local on its own server only."
            >
                <div class="rule-form-row">
                    <b-form-group label="Name" label-for="rule-org-name" label-size="sm" class="rule-org-field">
                        <b-form-input id="rule-org-name" v-model="form.expected.name" size="sm"></b-form-input>
                    </b-form-group>
                    <b-form-group label="Local or external" label-for="rule-org-local" label-size="sm" class="rule-org-field">
                        <b-form-select id="rule-org-local" v-model="form.expected.local" :options="localOptions" size="sm"></b-form-select>
                    </b-form-group>
                </div>
                <div class="rule-form-row">
                    <b-form-group
                        v-for="field in orgFields"
                        :key="field.name"
                        :label="field.label"
                        :label-for="`rule-org-${field.name}`"
                        label-size="sm"
                        class="rule-org-field mb-0"
                    >
                        <b-form-input
                            :id="`rule-org-${field.name}`"
                            v-model="form.expected[field.name]"
                            size="sm"
                            placeholder="Not checked"
                        ></b-form-input>
                    </b-form-group>
                </div>
            </b-form-group>

            <b-form-group
                v-else-if="isItem"
                label="Must have"
                class="rule-item-group"
                :invalid-feedback="errors.expected"
                :state="errors.expected ? false : null"
            >
                <div v-if="form.expected" class="rule-item">
                    <div class="rule-item-head">
                        <strong>{{ form.expected.name }}</strong>
                        <span class="rule-item-summary">{{ itemSummary }}</span>
                    </div>
                    <template v-if="form.type === 'sharing_group'">
                        <p v-if="form.expected.releasability" class="rule-item-line">Releasability: {{ form.expected.releasability }}</p>
                        <p v-if="form.expected.description" class="rule-item-line">Description: {{ form.expected.description }}</p>
                        <ul class="rule-item-members" aria-label="Members">
                            <li v-for="member in shownMembers" :key="member.uuid">{{ member.name }}</li>
                            <li v-if="hiddenMembers > 0" class="text-muted">and {{ hiddenMembers }} more</li>
                        </ul>
                        <p class="rule-item-hint">
                            Servers must have at least these members: others stay. A missing group is created; missing
                            members are added (and created as external organisations).
                        </p>
                    </template>
                    <p v-else class="rule-item-hint">
                        Servers must have it enabled, with these clusters at their version or newer. Missing clusters
                        are copied from {{ sourceName }}.
                    </p>
                </div>
                <p v-else class="rule-item-empty">{{ itemEmptyText }}</p>
            </b-form-group>

            <div v-if="!isItem" class="rule-form-row">
                <b-form-group
                    v-if="comparatorOptions.length > 1"
                    label="Must be"
                    label-for="rule-comparator"
                    class="rule-comparator-group"
                    :invalid-feedback="errors.comparator"
                    :state="errors.comparator ? false : null"
                >
                    <b-form-select
                        id="rule-comparator"
                        v-model="form.comparator"
                        :options="comparatorOptions"
                    ></b-form-select>
                </b-form-group>

                <b-form-group
                    :label="expectedLabel"
                    :label-for="valueKind === 'boolean' || valueKind === 'content' ? null : 'rule-expected'"
                    class="rule-expected-group"
                    :invalid-feedback="errors.expected"
                    :state="errors.expected ? false : null"
                >
                    <b-form-radio-group
                        v-if="valueKind === 'boolean' || valueKind === 'content'"
                        v-model="form.expected"
                        :options="booleanOptions"
                        buttons
                        button-variant="outline-primary"
                        size="sm"
                        name="rule-expected"
                        class="rule-boolean"
                        @change="expectedTouched = true"
                    ></b-form-radio-group>
                    <b-form-select
                        v-else-if="valueKind === 'options'"
                        id="rule-expected"
                        v-model="optionValue"
                        :options="optionChoices"
                        @change="expectedTouched = true"
                    ></b-form-select>
                    <b-form-input
                        v-else
                        id="rule-expected"
                        v-model="textValue"
                        :type="valueKind === 'number' ? 'number' : 'text'"
                        :step="settingType === 'float' ? 'any' : '1'"
                        :placeholder="valueKind === 'version' ? 'e.g. 2.5.20' : ''"
                        :state="errors.expected ? false : null"
                        :class="{ 'key-mono': valueKind !== 'number' }"
                        @input="expectedTouched = true"
                    ></b-form-input>
                    <small v-if="referenceHint" class="form-text text-muted rule-reference-hint">
                        On {{ referenceName }}: <span class="key-mono">{{ referenceHint.text }}</span>
                        <b-button
                            v-if="referenceHint.differs"
                            variant="link"
                            size="sm"
                            class="p-0 ml-1 align-baseline"
                            @click="useReferenceValue"
                        >Use it</b-button>
                    </small>
                </b-form-group>
            </div>

            <b-form-group label="When a server drifts" class="mb-2">
                <div class="rule-severity" role="radiogroup" aria-label="Severity">
                    <button
                        v-for="option in severityOptions"
                        :key="option.value"
                        type="button"
                        role="radio"
                        :aria-checked="form.severity === option.value ? 'true' : 'false'"
                        :class="['rule-severity-option', `sev-${option.value}`, { active: form.severity === option.value }]"
                        @click="form.severity = option.value"
                    >
                        <i :class="option.icon" aria-hidden="true"></i> {{ option.text }}
                    </button>
                </div>
                <small class="form-text text-muted">The issue raised on that server, in Needs attention and the fleet table.</small>
            </b-form-group>

            <b-form-group
                label="Note"
                label-for="rule-note"
                description="Optional. Shown with the issue, e.g. why the fleet needs this value."
                :invalid-feedback="errors.note"
                :state="errors.note ? false : null"
                class="mb-0"
            >
                <b-form-textarea id="rule-note" v-model="form.note" rows="2" maxlength="500"></b-form-textarea>
            </b-form-group>

            <b-alert :show="!!conflict" variant="info" class="mt-3 mb-0 rule-conflict">
                <span>The baseline already has a rule for this {{ typeNoun }}.</span>
                <b-button size="sm" variant="primary" :disabled="saving" @click="submit(null, 'replace')">Replace it</b-button>
            </b-alert>
            <b-alert :show="!!generalError" variant="danger" class="mt-3 mb-0">{{ generalError }}</b-alert>
            <button type="submit" class="d-none" tabindex="-1" aria-hidden="true"></button>
        </b-form>
    </b-modal>
</template>

<script>
import api from "@/api/baselines"
import KeyPicker from "./KeyPicker.vue"
import { SEVERITY_META } from "@/views/attention/healthLabels"
import {
    COMPARATOR_META, SEVERITY_OPTIONS, TYPE_META, expectedFromSetting, formatValue, isContentType, isItemType,
    isServerSpecific, itemExpectedText, settingOptions,
} from "./baselineFormat"

const SECRET_WORDS = /(password|passwd|authkey|apikey|token|secret|accesskey|salt|encryptionkey|privatekey)$/

const SHOWN_MEMBERS = 12

// An organisation rule's fields, all present for the form: empty ones are not checked
function organisationForm(expected) {
    const value = expected || {}
    return {
        name: value.name || "",
        type: value.type || "",
        nationality: value.nationality || "",
        sector: value.sector || "",
        local: value.local === true || value.local === false ? value.local : null,
    }
}

function emptyExpected(type) {
    if (type === "setting") {
        return ""
    }
    if (type === "organisation") {
        return organisationForm()
    }
    return isItemType(type) ? null : true
}

function emptyForm(type = "setting") {
    return { type, key: "", label: "", expected: emptyExpected(type), comparator: "eq", severity: "warning", note: "", force: false }
}

export default {
    name: "RuleModal",
    components: { KeyPicker },
    props: {
        // Where a new rule goes: a fleet's baseline, or a saved baseline (`savedId`)
        fleetId: { type: Number, default: null },
        savedId: { type: Number, default: null },
        types: { type: Object, default: null },
        // Servers to take values from: the fleet's, or all the user's for a saved baseline. [{ id, name, unavailable }]
        servers: { type: Array, default: () => [] },
        rules: { type: Array, default: () => [] },
        // The rule to edit, or null to add one
        rule: { type: Object, default: null },
    },
    data() {
        return {
            form: emptyForm(),
            referenceId: null,
            reference: null,
            referenceLoading: false,
            referenceError: null,
            errors: {},
            generalError: null,
            conflict: false,
            saving: false,
            // Once the value was typed or chosen, picking another key no longer overwrites it
            expectedTouched: false,
            // Why the item picked cannot make a rule (a custom galaxy whose clusters were not listed)
            unavailableItem: null,
            takeAgainMessage: null,
            orgFields: [
                { name: "type", label: "Type" },
                { name: "nationality", label: "Nationality" },
                { name: "sector", label: "Sector" },
            ],
            localOptions: [
                { value: null, text: "Not checked" },
                { value: true, text: "Local" },
                { value: false, text: "External" },
            ],
        }
    },
    computed: {
        editing() {
            return this.rule !== null
        },
        typeOptions() {
            const types = this.types ? this.types.types : []
            return types.map(type => ({ value: type.type, text: type.label }))
        },
        typeMeta() {
            return (this.types ? this.types.types : []).find(type => type.type === this.form.type) || null
        },
        typeNoun() {
            return (TYPE_META[this.form.type] || {}).keyLabel ? TYPE_META[this.form.type].keyLabel.toLowerCase() : "version"
        },
        keyLabel() {
            return (TYPE_META[this.form.type] || {}).keyLabel
        },
        isItem() {
            return isItemType(this.form.type)
        },
        itemSummary() {
            return this.form.expected ? itemExpectedText(this.form.type, this.form.expected) : ""
        },
        itemEmptyText() {
            if (this.unavailableItem) {
                return this.unavailableItem
            }
            const what = this.form.type === "sharing_group" ? "its members are" : "its clusters are"
            return `Pick it on a server above: ${what} taken from there.`
        },
        shownMembers() {
            return ((this.form.expected && this.form.expected.members) || []).slice(0, SHOWN_MEMBERS)
        },
        hiddenMembers() {
            return Math.max(((this.form.expected && this.form.expected.members) || []).length - SHOWN_MEMBERS, 0)
        },
        sourceName() {
            const id = this.form.expected ? this.form.expected.source_server_id : null
            const server = this.servers.find(entry => entry.id === id)
            return server ? server.name : `server #${id}`
        },
        keyPlaceholder() {
            if (this.form.type === "setting") {
                return "e.g. MISP.live or Security.password_policy_length"
            }
            if (this.form.type === "taxonomy_enabled") {
                return "Namespace, e.g. tlp"
            }
            return "Search by name, or paste its UUID"
        },
        keyDescription() {
            if (this.editing) {
                return "To check something else, add another rule."
            }
            if (this.referenceError) {
                return `Could not list from ${this.referenceName}: ${this.referenceError}`
            }
            const section = this.contentSection
            if (section && section.error) {
                if (this.isItem) {
                    return `${section.error}.`
                }
                return `${section.error}. You can still type the ${this.form.type === "taxonomy_enabled" ? "namespace" : "UUID"}.`
            }
            return null
        },
        serverOptions() {
            return this.servers.map(server => ({
                value: server.id,
                text: server.unavailable ? `${server.name} (${server.unavailable.toLowerCase()})` : server.name,
            }))
        },
        referenceName() {
            const server = this.servers.find(entry => entry.id === this.referenceId)
            return server ? server.name : "the server"
        },
        referenceDescription() {
            if (this.referenceLoading) {
                return "Listing its settings and content…"
            }
            if (this.reference && this.reference.unavailable && this.form.type !== "setting") {
                return "Unreachable: showing what it listed last."
            }
            return null
        },
        takenKeys() {
            return new Set(this.rules.filter(rule => rule.type === this.form.type).map(rule => rule.key))
        },
        settingsByName() {
            const byName = {}
            if (this.reference) {
                this.reference.settings.forEach((setting) => { byName[setting.name] = setting })
            }
            return byName
        },
        contentSection() {
            return this.reference && (isContentType(this.form.type) || this.isItem) ? this.reference.content[this.form.type] : null
        },
        keyItems() {
            if (!this.reference) {
                return []
            }
            if (this.form.type === "setting") {
                return this.reference.settings.map(setting => ({
                    value: setting.name,
                    label: setting.name,
                    hint: formatValue(setting.value),
                    search: setting.name.toLowerCase(),
                    taken: this.takenKeys.has(setting.name),
                }))
            }
            const section = this.contentSection
            if (!section || !section.items) {
                return []
            }
            const on = this.form.type === "object_template_active" ? "active" : "enabled"
            const off = this.form.type === "object_template_active" ? "inactive" : "disabled"
            return section.items.map(item => ({
                value: item.key,
                label: item.label,
                hint: this.isItem ? this.itemHint(item) : (item.enabled ? on : off),
                search: `${item.key} ${item.label} ${item.description}`.toLowerCase(),
                taken: this.takenKeys.has(item.key),
                item,
            }))
        },
        selectedSetting() {
            return this.form.type === "setting" ? this.settingsByName[this.form.key.trim()] || null : null
        },
        settingType() {
            if (this.selectedSetting) {
                return this.selectedSetting.type
            }
            if (this.editing && this.form.type === "setting") {
                const value = this.rule.expected
                if (typeof value === "boolean") {
                    return "boolean"
                }
                return typeof value === "number" ? "numeric" : "string"
            }
            return null
        },
        valueKind() {
            if (this.isItem) {
                return "item"
            }
            if (isContentType(this.form.type)) {
                return "content"
            }
            if (this.form.type === "version_min") {
                return "version"
            }
            if (this.settingType === "boolean") {
                return "boolean"
            }
            if (this.settingType === "numeric" || this.settingType === "float") {
                return "number"
            }
            if (this.optionChoices && this.form.comparator === "eq") {
                return "options"
            }
            return "text"
        },
        optionChoices() {
            return settingOptions(this.selectedSetting)
        },
        comparatorOptions() {
            if (!this.typeMeta) {
                return []
            }
            let comparators = this.typeMeta.comparators
            if (this.form.type === "setting" && this.settingType && !["numeric", "float"].includes(this.settingType)) {
                comparators = ["eq"]
            }
            return comparators.map(value => ({ value, text: COMPARATOR_META[value].text }))
        },
        expectedLabel() {
            if (this.valueKind === "content") {
                return "Should be"
            }
            if (this.valueKind === "version") {
                return "At least"
            }
            return this.comparatorOptions.length > 1 ? "Value" : "Must be"
        },
        booleanOptions() {
            if (this.valueKind === "content") {
                const on = this.form.type === "object_template_active" ? "Active" : "Enabled"
                const off = this.form.type === "object_template_active" ? "Inactive" : "Disabled"
                return [{ value: true, text: on }, { value: false, text: off }]
            }
            return [{ value: true, text: "true" }, { value: false, text: "false" }]
        },
        textValue: {
            get() {
                return this.form.expected === null || this.form.expected === undefined ? "" : String(this.form.expected)
            },
            set(text) {
                this.form.expected = text
            },
        },
        optionValue: {
            get() {
                return this.form.expected === null || this.form.expected === undefined ? "" : String(this.form.expected)
            },
            set(value) {
                this.form.expected = value
            },
        },
        serverSpecific() {
            return this.form.type === "setting" && isServerSpecific(this.form.key.trim(), this.types)
        },
        isSecret() {
            const name = this.form.key.trim()
            if (this.form.type !== "setting" || name === "") {
                return false
            }
            const last = name.split(".").pop()
            return SECRET_WORDS.test(last.toLowerCase().replace(/[^a-z0-9]/g, "")) || /[_-]key$/i.test(last)
        },
        referenceHint() {
            if (this.editing && !this.reference) {
                return null
            }
            let value
            if (this.form.type === "setting") {
                if (!this.selectedSetting) {
                    return null
                }
                value = expectedFromSetting(this.selectedSetting)
            } else if (this.form.type === "version_min") {
                if (!this.reference || !this.reference.version) {
                    return null
                }
                value = this.reference.version
            } else {
                return null
            }
            return { text: formatValue(value), differs: String(value) !== String(this.form.expected), value }
        },
        severityOptions() {
            return SEVERITY_OPTIONS.map(option => ({ ...option, icon: SEVERITY_META[option.value].icon }))
        },
        canSubmit() {
            if (this.isSecret || (this.serverSpecific && !this.form.force)) {
                return false
            }
            if (this.isItem && !(this.form.expected && String(this.form.expected.name || "").trim() !== "")) {
                return false
            }
            if (this.keyLabel && this.form.key.trim() === "") {
                return false
            }
            return !(this.form.type === "version_min" && String(this.form.expected || "").trim() === "")
        },
    },
    methods: {
        onShow() {
            this.errors = {}
            this.generalError = null
            this.conflict = false
            this.saving = false
            this.expectedTouched = false
            this.unavailableItem = null
            this.takeAgainMessage = null
            if (this.editing) {
                this.form = {
                    type: this.rule.type,
                    key: this.rule.key,
                    label: this.rule.label,
                    expected: this.rule.type === "organisation" ? organisationForm(this.rule.expected) : this.rule.expected,
                    comparator: this.rule.comparator,
                    severity: this.rule.severity,
                    note: this.rule.note,
                    force: this.rule.forced,
                }
                this.reference = null
                this.pickDefaultReference()
                return
            }
            this.form = emptyForm(this.form.type || "setting")
            this.pickDefaultReference()
            this.loadReference()
        },
        pickDefaultReference() {
            if (this.referenceId === null || !this.servers.some(server => server.id === this.referenceId)) {
                const reachable = this.servers.find(server => !server.unavailable)
                this.referenceId = (reachable || this.servers[0] || {}).id || null
            }
        },
        itemHint(item) {
            if (this.form.type === "organisation") {
                return item.group
            }
            if (this.form.type === "sharing_group") {
                return `${item.members || 0} member${item.members === 1 ? "" : "s"}`
            }
            return item.unavailable ? "clusters not listed" : `${item.clusters || 0} cluster${item.clusters === 1 ? "" : "s"}`
        },
        // An item rule's expected value from what a reference server lists, or null
        itemExpected(item) {
            if (!item.expected) {
                return null
            }
            const expected = JSON.parse(JSON.stringify(item.expected))
            return this.form.type === "organisation" ? organisationForm(expected) : expected
        },
        takeAgain() {
            const server_id = this.referenceId
            const name = this.referenceName
            this.referenceLoading = true
            this.takeAgainMessage = null
            api.reference(server_id, { fresh: true })
                .then((reference) => {
                    const section = reference.content[this.form.type] || {}
                    const item = (section.items || []).find(entry => entry.key === this.form.key)
                    if (section.error) {
                        this.takeAgainMessage = `Could not list it on ${name}: ${section.error}`
                    } else if (!item) {
                        this.takeAgainMessage = `${name} does not have it.`
                    } else if (!this.itemExpected(item)) {
                        this.takeAgainMessage = item.unavailable || `It cannot be taken from ${name}.`
                    } else {
                        this.form.expected = this.itemExpected(item)
                        this.takeAgainMessage = `Taken from ${name}: save to keep it.`
                    }
                })
                .catch((error) => {
                    this.takeAgainMessage = `Could not list from ${name}: ${error.message}`
                })
                .finally(() => {
                    this.referenceLoading = false
                })
        },
        focusFirst() {
            const target = this.editing ? null : this.$refs.key
            if (target) {
                target.focus()
            }
        },
        loadReference() {
            if (this.referenceId === null) {
                this.reference = null
                return
            }
            const server_id = this.referenceId
            this.referenceLoading = true
            this.referenceError = null
            api.reference(server_id)
                .then((reference) => {
                    if (server_id === this.referenceId) {
                        this.reference = reference
                        if (this.form.type === "version_min" && !this.form.expected && reference.version) {
                            this.form.expected = reference.version
                        }
                    }
                })
                .catch((error) => {
                    if (server_id === this.referenceId) {
                        this.reference = null
                        this.referenceError = error.message
                    }
                })
                .finally(() => {
                    if (server_id === this.referenceId) {
                        this.referenceLoading = false
                    }
                })
        },
        onTypeChange(type) {
            const severity = this.form.severity
            const note = this.form.note
            this.form = { ...emptyForm(type), severity, note }
            this.expectedTouched = false
            if (type === "version_min" && this.reference && this.reference.version) {
                this.form.expected = this.reference.version
            }
            this.errors = {}
            this.conflict = false
        },
        onKeyTyped(text) {
            this.conflict = false
            this.errors = { ...this.errors, key: undefined }
            // A name typed in full counts as picked
            const known = this.keyItems.find(item => item.value === text.trim())
            if (known) {
                this.onKeySelected(known)
            }
        },
        onKeySelected(item) {
            if (this.expectedTouched) {
                return
            }
            if (this.form.type === "setting") {
                const setting = this.settingsByName[item.value]
                this.form.comparator = "eq"
                this.form.expected = expectedFromSetting(setting)
                this.form.force = false
            } else if (item.item && this.isItem) {
                this.form.label = item.item.label
                this.form.expected = this.itemExpected(item.item) || emptyExpected(this.form.type)
                this.unavailableItem = this.itemExpected(item.item) ? null : item.item.unavailable || "It cannot be taken from this server."
            } else if (item.item) {
                this.form.label = item.item.label !== item.item.key ? item.item.label : ""
                this.form.expected = item.item.enabled
            }
        },
        useReferenceValue() {
            if (this.referenceHint) {
                this.form.expected = this.referenceHint.value
                this.expectedTouched = false
            }
        },
        payload() {
            const payload = {
                expected: this.form.expected,
                comparator: this.comparatorOptions.length > 0 ? this.form.comparator : undefined,
                severity: this.form.severity,
                note: this.form.note,
                force: this.form.force,
            }
            if (this.valueKind === "number" && payload.expected !== "" && !Number.isNaN(Number(payload.expected))) {
                payload.expected = Number(payload.expected)
            }
            if (this.form.type === "organisation") {
                // Empty fields are left out: not checked
                const expected = {}
                Object.entries(this.form.expected).forEach(([field, value]) => {
                    if (value !== null && String(value).trim() !== "") {
                        expected[field] = typeof value === "string" ? value.trim() : value
                    }
                })
                payload.expected = expected
            }
            if (!this.editing) {
                payload.type = this.form.type
                payload.key = this.form.key.trim()
                const known = this.keyItems.find(item => item.value === payload.key && item.item)
                payload.label = known && known.item.label !== known.item.key ? known.item.label : this.form.label
            }
            return payload
        },
        submit(event, onConflict = "error") {
            if (event) {
                event.preventDefault()
            }
            if (this.saving || !this.canSubmit) {
                return
            }
            this.saving = true
            this.errors = {}
            this.generalError = null
            const request = this.editing
                ? api.updateRule(this.rule.id, this.payload())
                : this.savedId !== null
                    ? api.addSavedRules(this.savedId, [this.payload()], onConflict)
                    : api.addRules(this.fleetId, [this.payload()], onConflict)
            request
                .then((result) => {
                    this.conflict = false
                    this.$emit("saved", result)
                    this.$bvModal.hide("modal-baseline-rule")
                })
                .catch((error) => {
                    const detail = error.errors[0] || error
                    if (error.status === 409) {
                        this.conflict = true
                    } else if (detail.field && ["key", "expected", "comparator", "note"].includes(detail.field)) {
                        this.errors = { [detail.field]: detail.message }
                    } else {
                        this.generalError = detail.message || error.message
                    }
                })
                .finally(() => {
                    this.saving = false
                })
        },
    },
}
</script>

<style scoped>
.rule-form-row {
    display: flex;
    flex-wrap: wrap;
    column-gap: 1rem;
}

.rule-type-group {
    flex: 1 1 14rem;
}

.rule-reference-group {
    flex: 1 1 14rem;
}

.rule-comparator-group {
    flex: 0 0 9rem;
}

.rule-expected-group {
    flex: 1 1 14rem;
}

.rule-fixed-key {
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--health-rule);
    border-radius: 0.25rem;
    background: #f6f7f9;
    color: var(--var-color-yankeesblue);
}

.key-mono {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.85rem;
}

.rule-specific {
    font-size: 0.9rem;
}

.rule-boolean {
    display: flex;
}

.rule-reference-hint {
    margin-top: 0.35rem;
}

.rule-severity {
    display: inline-flex;
    padding: 2px;
    border-radius: 6px;
    background: #eef0f3;
}

.rule-severity-option {
    border: none;
    background: none;
    padding: 0.25rem 0.8rem;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #4a5260;
}

.rule-severity-option i {
    margin-right: 0.2rem;
}

.rule-severity-option.active {
    background: #fff;
    box-shadow: 0 1px 2px rgba(16, 24, 40, 0.12);
}

.rule-severity-option.sev-critical.active,
.rule-severity-option.sev-critical:hover i {
    color: var(--health-critical-ink);
}

.rule-severity-option.sev-warning.active,
.rule-severity-option.sev-warning:hover i {
    color: var(--health-warning-ink);
}

.rule-severity-option.sev-info.active,
.rule-severity-option.sev-info:hover i {
    color: var(--health-info-ink);
}

.rule-severity-option:focus-visible {
    outline: 2px solid var(--var-color-lapislazuli);
    outline-offset: 1px;
}

.rule-take-again {
    display: flex;
    gap: 0.5rem;
}

.rule-org-field {
    flex: 1 1 10rem;
}

.rule-item {
    padding: 0.6rem 0.75rem;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    background: #f6f7f9;
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.rule-item-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.75rem;
}

.rule-item-summary,
.rule-item-hint,
.rule-item-empty {
    color: #5a6270;
}

.rule-item-line {
    margin: 0.35rem 0 0;
}

.rule-item-members {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
}

.rule-item-members li {
    padding: 0 0.45rem;
    border-radius: 3px;
    background: #fff;
    border: 1px solid var(--health-rule);
    font-size: 0.78rem;
}

.rule-item-hint {
    margin: 0.5rem 0 0;
    font-size: 0.8rem;
}

.rule-item-empty {
    margin: 0;
    font-size: 0.875rem;
}

.rule-conflict {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}
</style>
