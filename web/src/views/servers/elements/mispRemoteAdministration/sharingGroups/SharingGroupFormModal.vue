<template>
    <b-modal
        id="modal-sharing-group-form"
        size="lg"
        scrollable
        :title="isEdit ? `Edit ${group.name}` : `Add a sharing group to ${server.name}`"
        @show="reset"
    >
        <b-form class="sg-form" novalidate @submit.prevent="save">
            <b-alert :show="error !== null" variant="danger" class="form-alert">
                <div v-for="(line, index) in errorLines" :key="index">{{ line }}</div>
            </b-alert>

            <b-form-group label="Name" label-for="sg-form-name" :state="nameState" :invalid-feedback="nameFeedback">
                <b-form-input id="sg-form-name" v-model="form.name" :state="nameState" autocomplete="off" maxlength="255" required></b-form-input>
            </b-form-group>

            <div class="switch-row">
                <b-form-checkbox v-model="form.active" switch class="switch">
                    <span class="switch-label">Active</span>
                    <span class="switch-help">{{ form.active ? "Can be chosen for new events and attributes." : "Cannot be chosen for new data; what is already shared with it still syncs." }}</span>
                </b-form-checkbox>
                <b-form-checkbox v-model="form.roaming" switch class="switch">
                    <span class="switch-label">Roaming</span>
                    <span class="switch-help">{{ form.roaming ? "Its events go to any sync server whose organisation is a member." : "Its events go only to the servers listed below." }}</span>
                </b-form-checkbox>
            </div>

            <div class="field-row">
                <b-form-group label="Releasable to" label-for="sg-form-releasability" class="field-half">
                    <b-form-input id="sg-form-releasability" v-model="form.releasability" autocomplete="off" placeholder="Who it may be shared with"></b-form-input>
                </b-form-group>
                <b-form-group label="Description" label-for="sg-form-description" class="field-half">
                    <b-form-textarea id="sg-form-description" v-model="form.description" rows="1" max-rows="5"></b-form-textarea>
                </b-form-group>
            </div>

            <fieldset class="list-field">
                <legend class="list-legend">
                    Members <span class="legend-count">{{ form.members.length }}</span>
                </legend>
                <ul v-if="form.members.length > 0" class="edit-list">
                    <li v-for="member in form.members" :key="member.uuid" :class="['edit-row', { 'is-new': isEdit && !originalMembers.has(member.uuid) }]">
                        <span class="row-name">{{ member.name }}</span>
                        <b-form-checkbox v-model="member.extend" class="row-option" :title="'Its users with the sharing group permission may change the group'">may extend</b-form-checkbox>
                        <button type="button" class="btn btn-link row-remove" :aria-label="`Remove ${member.name}`" :title="`Remove ${member.name}`" @click="removeMember(member)">
                            <i class="fas fa-times" aria-hidden="true"></i>
                        </button>
                    </li>
                </ul>
                <p v-else class="list-empty">No member: only servers with “all organisations” would share it.</p>
                <div class="picker">
                    <i class="fas fa-plus picker-icon" aria-hidden="true"></i>
                    <b-form-input
                        v-model="orgQuery"
                        size="sm"
                        class="picker-input"
                        autocomplete="off"
                        :placeholder="organisations === null ? 'Listing the organisations of this server…' : 'Add an organisation of this server…'"
                        :disabled="organisations === null"
                        aria-label="Add an organisation"
                        @keydown.enter.prevent="addFirstMatch"
                        @keydown.down.prevent="focusOption(0)"
                    ></b-form-input>
                    <ul v-if="orgQuery.trim() !== ''" class="picker-options" role="listbox">
                        <li v-for="(org, index) in orgMatches" :key="org.uuid" role="option">
                            <button :ref="`option-${index}`" type="button" class="picker-option" @click="addMember(org)" @keydown.down.prevent="focusOption(index + 1)" @keydown.up.prevent="focusOption(index - 1)">
                                <span class="option-name">{{ org.name }}</span>
                                <span class="option-kind">{{ org.local ? "local" : "external" }}</span>
                            </button>
                        </li>
                        <li v-if="orgMatches.length === 0" class="picker-none">No other organisation of this server matches. Add it in the Organisations tab first.</li>
                    </ul>
                </div>
                <p v-if="organisationsError" class="picker-error">Could not list the organisations: {{ organisationsError }}</p>
            </fieldset>

            <fieldset v-if="!form.roaming" class="list-field">
                <legend class="list-legend">
                    Servers <span class="legend-count">{{ form.servers.length }}</span>
                </legend>
                <ul class="edit-list">
                    <li v-for="item in form.servers" :key="item.server_id" :class="['edit-row', { 'is-new': isEdit && !originalServers.has(item.server_id) }]">
                        <span class="row-name">{{ item.name }}</span>
                        <b-form-checkbox v-model="item.all_orgs" class="row-option" :title="item.server_id === 0 ? 'Every organisation of this server sees the group, members or not' : 'Every organisation of that server may receive its events'">all its organisations</b-form-checkbox>
                        <button
                            v-if="item.server_id !== 0"
                            type="button"
                            class="btn btn-link row-remove"
                            :aria-label="`Remove ${item.name}`"
                            :title="`Remove ${item.name}`"
                            @click="removeServer(item)"
                        >
                            <i class="fas fa-times" aria-hidden="true"></i>
                        </button>
                        <span v-else class="row-fixed" title="MISP only lets its own interface remove the Local instance">
                            <i class="fas fa-lock" aria-hidden="true"></i>
                        </span>
                    </li>
                </ul>
                <div v-if="serverOptions.length > 0" class="picker">
                    <i class="fas fa-plus picker-icon" aria-hidden="true"></i>
                    <b-form-select v-model="serverToAdd" size="sm" class="picker-input" :options="serverOptions" aria-label="Add a sync server" @change="addServer"></b-form-select>
                </div>
                <p v-else class="list-empty">{{ syncServers.length === 0 ? "This server has no sync connection to add." : "Every sync server of this server is listed." }}</p>
            </fieldset>
            <p v-else class="roaming-note">
                <i class="fas fa-info-circle" aria-hidden="true"></i>
                A roaming group ignores its server list: it is left as it is.
            </p>

            <b-alert v-if="!isEdit" show variant="light" class="api-note">
                <i class="fas fa-info-circle mr-1" aria-hidden="true"></i>
                Created through MISP's API: MISP will list it as received by sync rather than created on this server. It works the same.
            </b-alert>
            <button type="submit" class="d-none" aria-hidden="true" tabindex="-1"></button>
        </b-form>

        <template #modal-footer="{ cancel }">
            <span v-if="isEdit" class="footer-note">{{ changes === 0 ? "No change yet" : `${changes} change${changes === 1 ? "" : "s"}` }}</span>
            <b-button variant="secondary" @click="cancel()">Cancel</b-button>
            <b-button variant="primary" :disabled="saving || !canSave" @click="save">
                <b-spinner v-if="saving" small class="mr-1"></b-spinner>{{ isEdit ? "Save changes" : "Add sharing group" }}
            </b-button>
        </template>
    </b-modal>
</template>

<script>
import api from "@/api/sharingGroups"
import organisationsApi from "@/api/organisations"
import { addPayload, changeCount, editPayload, formFrom, LOCAL_INSTANCE, nameTaken } from "@/helpers/sharingGroups"

const MAX_MATCHES = 8

export default {
    name: "SharingGroupFormModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        // The group to edit; null to add one
        group: {
            type: Object,
            default: null,
        },
        // The server's groups: names already taken
        groups: {
            type: Array,
            default: () => [],
        },
    },
    data() {
        return {
            form: formFrom(null),
            organisations: null,
            organisationsError: null,
            orgQuery: "",
            serverToAdd: null,
            saving: false,
            error: null,
            errorField: null,
        }
    },
    computed: {
        isEdit() {
            return this.group !== null
        },
        originalMembers() {
            return new Set(this.isEdit ? this.group.members.map(member => member.uuid) : [])
        },
        originalServers() {
            return new Set(this.isEdit ? this.group.servers.map(item => item.server_id) : [])
        },
        takenBy() {
            return nameTaken(this.groups, this.form.name, this.isEdit ? this.group.uuid : null)
        },
        nameState() {
            return this.errorField === "name" || this.takenBy ? false : null
        },
        nameFeedback() {
            if (this.takenBy) {
                return `“${this.takenBy.name}” already exists on this server`
            }
            return this.errorField === "name" ? this.error : ""
        },
        payload() {
            return this.isEdit ? editPayload(this.group, this.form) : addPayload(this.form)
        },
        changes() {
            return this.isEdit ? changeCount(this.group, this.payload) : 0
        },
        canSave() {
            if (this.form.name.trim() === "" || this.takenBy) {
                return false
            }
            return !this.isEdit || this.changes > 0
        },
        errorLines() {
            // A partial failure lists what was done, then what failed
            return String(this.error || "").split(/\. (?=Failed:)/)
        },
        orgMatches() {
            const needle = this.orgQuery.trim().toLowerCase()
            if (!this.organisations || needle === "") {
                return []
            }
            const taken = new Set(this.form.members.map(member => member.uuid))
            const matches = this.organisations.filter(org => !taken.has(org.uuid) &&
                (org.name.toLowerCase().includes(needle) || org.uuid.startsWith(needle)))
            matches.sort((a, b) => Number(!a.name.toLowerCase().startsWith(needle)) - Number(!b.name.toLowerCase().startsWith(needle)) ||
                a.name.localeCompare(b.name))
            return matches.slice(0, MAX_MATCHES)
        },
        // The server's sync connections: their IDs there are what MISP lists in a group
        syncServers() {
            const links = this.$store.getters["connections/linksOfServer"](this.server.id).outgoing
            const servers = new Map()
            links.forEach((link) => {
                const remote = link.destination && link.destination.Server
                if (remote && remote.id !== undefined) {
                    servers.set(Number(remote.id), remote.name || remote.url || `Server #${remote.id}`)
                }
            })
            return [...servers.entries()].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
        },
        serverOptions() {
            const listed = new Set(this.form.servers.map(item => item.server_id))
            const options = this.syncServers.filter(item => !listed.has(item.id)).map(item => ({ value: item.id, text: item.name }))
            if (!listed.has(LOCAL_INSTANCE)) {
                options.unshift({ value: LOCAL_INSTANCE, text: "Local instance" })
            }
            return options.length === 0 ? [] : [{ value: null, text: "Add a sync server of this server…" }].concat(options)
        },
    },
    watch: {
        form: {
            handler() {
                if (this.errorField !== null) {
                    this.errorField = null
                }
            },
            deep: true,
        },
    },
    methods: {
        reset() {
            this.error = null
            this.errorField = null
            this.saving = false
            this.orgQuery = ""
            this.serverToAdd = null
            const user = this.$store.state.servers.server_user[this.server.id]
            this.form = formFrom(this.group, user && user.Organisation ? user.Organisation : null)
            this.loadOrganisations()
        },
        loadOrganisations() {
            this.organisationsError = null
            organisationsApi.index(this.server.id)
                .then((listed) => { this.organisations = Object.freeze(listed.organisations) })
                .catch((error) => {
                    this.organisations = []
                    this.organisationsError = error.message
                })
        },
        addMember(org) {
            this.form.members.push({ uuid: org.uuid, name: org.name, extend: false })
            this.orgQuery = ""
        },
        addFirstMatch() {
            if (this.orgMatches.length > 0) {
                this.addMember(this.orgMatches[0])
            }
        },
        focusOption(index) {
            const option = this.$refs[`option-${index}`]
            if (option && option[0]) {
                option[0].focus()
            }
        },
        removeMember(member) {
            this.form.members = this.form.members.filter(other => other.uuid !== member.uuid)
        },
        addServer(id) {
            if (id === null) {
                return
            }
            const found = this.syncServers.find(item => item.id === id)
            const name = id === LOCAL_INSTANCE ? "Local instance" : (found ? found.name : `Server #${id}`)
            const added = { server_id: id, name, all_orgs: false }
            // The Local instance first, as MISP lists it
            this.form.servers = id === LOCAL_INSTANCE ? [added].concat(this.form.servers) : this.form.servers.concat([added])
            this.$nextTick(() => { this.serverToAdd = null })
        },
        removeServer(item) {
            if (item.server_id !== LOCAL_INSTANCE) {
                this.form.servers = this.form.servers.filter(other => other.server_id !== item.server_id)
            }
        },
        save() {
            if (!this.canSave || this.saving) {
                return
            }
            this.saving = true
            this.error = null
            const name = this.form.name.trim()
            const request = this.isEdit
                ? api.edit(this.server.id, this.group.uuid, this.payload)
                : api.add(this.server.id, this.payload)
            request
                .then((data) => {
                    const saved = (data && data.SharingGroup) || (this.isEdit ? { uuid: this.group.uuid } : null)
                    this.$bvToast.toast(this.isEdit ? `${name} was saved on ${this.server.name}` : `${name} was added to ${this.server.name}`, {
                        title: this.isEdit ? "Sharing group saved" : "Sharing group added",
                        variant: "success",
                        solid: true,
                    })
                    this.$emit("saved", saved)
                    this.$bvModal.hide("modal-sharing-group-form")
                })
                .catch((error) => {
                    this.error = error.message
                    this.errorField = error.field || null
                    if (error.status === 502) {
                        // MISP may have taken part of it: list again behind the form
                        this.$emit("changed")
                    }
                })
                .finally(() => { this.saving = false })
        },
    },
}
</script>

<style scoped>
.sg-form {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.form-alert {
    font-size: 0.85rem;
}

.sg-form ::v-deep legend,
.sg-form ::v-deep label {
    font-weight: 600;
    color: #3c4650;
}

.switch-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem 1.5rem;
    margin-bottom: 1rem;
}

.switch ::v-deep label {
    font-weight: 400;
}

.switch-label {
    display: block;
    font-weight: 600;
    color: #3c4650;
}

.switch-help {
    display: block;
    color: #6c757d;
    font-size: 0.8rem;
    line-height: 1.35;
}

.field-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1rem;
}

.field-half {
    flex: 1 1 14rem;
    min-width: 0;
}

.list-field {
    margin-bottom: 1rem;
}

.list-legend {
    display: flex;
    align-items: baseline;
    gap: 0.4em;
    width: auto;
    margin-bottom: 0.35rem;
    font-size: 0.875rem;
}

.legend-count {
    padding: 0 0.4em;
    border-radius: 0.6em;
    background: rgba(0, 0, 0, 0.07);
    color: #5f6873;
    font-size: 0.8rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.edit-list {
    max-height: 15rem;
    margin: 0 0 0.4rem;
    padding: 0;
    overflow-y: auto;
    border: 1px solid var(--health-rule);
    border-radius: 0.25rem;
    list-style: none;
}

.edit-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.3rem 0.4rem 0.3rem 0.75rem;
}

.edit-row + .edit-row {
    border-top: 1px solid var(--health-rule);
}

.edit-row.is-new {
    box-shadow: inset 3px 0 0 var(--health-ok);
}

.row-name {
    flex: 1 1 auto;
    min-width: 0;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.row-option {
    flex: none;
    color: #495057;
    font-size: 0.82rem;
}

.row-option ::v-deep label {
    font-weight: 400;
}

.row-remove,
.row-fixed {
    flex: none;
    width: 1.8rem;
    padding: 0.1rem 0;
    color: #9aa1a7;
    text-align: center;
}

.row-remove:hover,
.row-remove:focus {
    color: var(--health-critical-ink);
}

.row-fixed {
    font-size: 0.75rem;
    cursor: help;
}

.list-empty {
    margin: 0 0 0.4rem;
    color: #6c757d;
}

.picker {
    position: relative;
}

.picker-icon {
    position: absolute;
    top: 0.55rem;
    left: 0.6rem;
    color: #9aa1a7;
    font-size: 0.75em;
    pointer-events: none;
    z-index: 1;
}

.picker-input {
    padding-left: 1.7rem;
}

.picker-options {
    margin: 0.2rem 0 0;
    padding: 0.2rem 0;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    background: #fff;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.08);
    list-style: none;
}

.picker-option {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    width: 100%;
    padding: 0.3rem 0.75rem;
    border: 0;
    background: none;
    color: inherit;
    text-align: left;
}

.picker-option:hover,
.picker-option:focus {
    background: var(--health-focus-bg);
    outline: none;
}

.option-name {
    font-weight: 600;
    overflow-wrap: anywhere;
}

.option-kind {
    color: #6c757d;
    font-size: 0.78rem;
}

.picker-none,
.picker-error {
    padding: 0.3rem 0.75rem;
    color: #6c757d;
}

.picker-error {
    margin: 0.3rem 0 0;
    padding: 0;
    color: var(--health-critical-ink);
}

.roaming-note {
    margin: 0 0 1rem;
    color: #5a6270;
}

.api-note {
    margin: 0;
    border-color: var(--health-rule);
    color: #5a6270;
    font-size: 0.82rem;
}

.footer-note {
    margin-right: auto;
    color: #6c757d;
    font-size: 0.85rem;
}

@media (max-width: 575.98px) {
    .switch-row {
        grid-template-columns: minmax(0, 1fr);
    }

    .edit-row {
        gap: 0.5rem;
    }
}
</style>
