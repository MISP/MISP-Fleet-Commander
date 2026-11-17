<template>
    <b-modal
        id="modal-organisation-detail"
        size="lg"
        hide-footer
        scrollable
        :title="org ? org.name : 'Organisation'"
        body-class="org-detail-body"
    >
        <template v-if="org" #modal-title>
            <span class="detail-title">{{ org.name }}</span>
            <span :class="['kind-badge', org.local ? 'kind-local' : 'kind-external']">{{ org.local ? "Local" : "External" }}</span>
        </template>
        <div v-if="org" class="org-detail">
            <div class="detail-actions">
                <b-button size="sm" variant="outline-primary" :disabled="row.users === 0" @click="$emit('show-users', org)">
                    <i class="fas fa-users mr-1" aria-hidden="true"></i>Show users<span v-if="row.users !== null" class="action-count">{{ row.users }}</span>
                </b-button>
                <b-button size="sm" variant="outline-primary" @click="edit">
                    <i class="fas fa-pen mr-1" aria-hidden="true"></i>Edit
                </b-button>
                <b-button
                    v-if="hasFleet"
                    size="sm"
                    variant="outline-primary"
                    :disabled="!row.standing || copyTargets === 0"
                    :title="copyTitle"
                    @click="copy"
                >
                    <i class="fas fa-clone mr-1" aria-hidden="true"></i>Create on other servers…<span v-if="row.standing && copyTargets > 0" class="action-count">{{ copyTargets }}</span>
                </b-button>
                <b-button size="sm" variant="outline-primary" title="Check that every server of the fleet has it" @click="baseline">
                    <i class="fas fa-ruler-combined mr-1" aria-hidden="true"></i>Add to baseline…
                </b-button>
                <b-dropdown size="sm" variant="link" right toggle-class="misp-links" no-caret>
                    <template #button-content>
                        <i class="fas fa-external-link-alt" aria-hidden="true"></i><span class="sr-only">Open in MISP</span>
                    </template>
                    <b-dropdown-item :href="`${server.url}/organisations/view/${org.id}`" target="_blank" rel="noopener">View in MISP</b-dropdown-item>
                    <b-dropdown-item :href="`${server.url}/admin/organisations/edit/${org.id}`" target="_blank" rel="noopener">Edit in MISP</b-dropdown-item>
                </b-dropdown>
            </div>

            <section v-if="row.flags.length > 0" class="detail-section attention" aria-label="Needs attention">
                <ul class="flag-list">
                    <li v-for="(flag, index) in row.flags" :key="flag.code + index" :class="['flag', `flag-${flag.tone}`]">
                        <i :class="['fas', flag.tone === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle']" aria-hidden="true"></i>
                        <span>{{ flag.text }}<span class="flag-help">{{ flagHelp[flag.code] }}</span></span>
                    </li>
                </ul>
            </section>

            <section class="detail-section">
                <dl class="detail-grid">
                    <dt>UUID</dt>
                    <dd class="uuid-cell">
                        <code>{{ org.uuid }}</code>
                        <button type="button" class="btn btn-link copy-button" :title="copied ? 'Copied' : 'Copy the UUID'" @click="copyUuid">
                            <i :class="['fas', copied ? 'fa-check' : 'fa-copy']" aria-hidden="true"></i>
                            <span class="sr-only">{{ copied ? "Copied" : "Copy the UUID" }}</span>
                        </button>
                    </dd>
                    <dt>Type</dt>
                    <dd>{{ org.type || "—" }}</dd>
                    <dt>Sector</dt>
                    <dd>{{ org.sector || "—" }}</dd>
                    <dt>Nationality</dt>
                    <dd>{{ org.nationality || "—" }}</dd>
                    <dt>Users</dt>
                    <dd>{{ row.users === null ? "—" : row.users }}</dd>
                    <template v-if="org.restricted_to_domain.length > 0">
                        <dt>Restricted to</dt>
                        <dd>{{ org.restricted_to_domain.join(", ") }}</dd>
                    </template>
                    <template v-if="org.contacts">
                        <dt>Contacts</dt>
                        <dd class="pre">{{ org.contacts }}</dd>
                    </template>
                    <template v-if="org.description">
                        <dt>Description</dt>
                        <dd class="pre">{{ org.description }}</dd>
                    </template>
                    <template v-if="org.date_created">
                        <dt>Created</dt>
                        <dd>{{ org.date_created }}<span v-if="org.created_by_email && org.created_by_email !== 'Unknown'" class="muted"> by {{ org.created_by_email }}</span></dd>
                    </template>
                    <template v-if="org.date_modified">
                        <dt>Modified</dt>
                        <dd>{{ org.date_modified }}</dd>
                    </template>
                </dl>
            </section>

            <section v-if="row.sync.length > 0" class="detail-section">
                <h6 class="section-title"><i class="fas fa-sync-alt" aria-hidden="true"></i> Used by sync</h6>
                <ul class="plain-list">
                    <li v-for="reason in row.sync" :key="reason.code + reason.text">{{ reason.text }}</li>
                </ul>
            </section>

            <section v-if="hasFleet" class="detail-section">
                <h6 class="section-title">
                    <i class="fas fa-network-wired" aria-hidden="true"></i> In the fleet
                    <span v-if="row.standing" class="section-note">on {{ row.standing.present }} of {{ row.standing.known }} servers, this one included</span>
                </h6>
                <p v-if="!row.standing && comparing" class="muted"><i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Comparing with the other servers…</p>
                <p v-else-if="!row.standing" class="muted">The other servers of the fleet could not be compared.</p>
                <ul v-else class="fleet-list">
                    <li v-for="entry in row.standing.rows" :key="entry.id" :class="['fleet-row', `state-${entry.state}`]">
                        <span class="state-mark" aria-hidden="true"><i :class="['fas', states[entry.state].icon]"></i></span>
                        <span class="fleet-server">{{ entry.name }}</span>
                        <span class="fleet-state">
                            {{ states[entry.state].label }}<template v-if="entry.state === 'renamed'">: “{{ entry.detail }}”</template>
                            <code v-else-if="entry.state === 'other_uuid'" :title="entry.detail">{{ entry.detail }}</code>
                            <span v-else-if="entry.state === 'unknown'" class="unknown-reason" :title="entry.detail">{{ entry.detail }}</span>
                        </span>
                    </li>
                </ul>
            </section>
        </div>
    </b-modal>
</template>

<script>
import { FLEET_STATES } from "@/helpers/organisations"

export default {
    name: "OrganisationDetailModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        // A row of the organisation table: {org, standing, users, sync, flags}
        row: {
            type: Object,
            default: null,
        },
        hasFleet: {
            type: Boolean,
            default: false,
        },
        comparing: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            copied: false,
            states: FLEET_STATES,
            flagHelp: {
                renamed: " — the servers agree on the UUID, not on the name.",
                other_uuid: " — events and sharing groups from that server name a different organisation. Edit one of them so that the UUIDs match.",
                no_users: " — nobody can log in for it here. Make it external, or remove it in MISP if it is not needed.",
                duplicate: " — the same organisation may have been created twice.",
            },
        }
    },
    computed: {
        org() {
            return this.row ? this.row.org : null
        },
        copyTargets() {
            return this.row && this.row.standing ? this.row.standing.missingIds.length + this.row.standing.unknown : 0
        },
        copyTitle() {
            if (!this.row || !this.row.standing) {
                return "Comparing with the other servers…"
            }
            return this.copyTargets === 0 ? "Every server of the fleet already has it, or one with the same name" : "Create it with the same UUID where it is missing"
        },
    },
    watch: {
        "row.org.uuid"() {
            this.copied = false
        },
    },
    methods: {
        edit() {
            this.$bvModal.hide("modal-organisation-detail")
            this.$emit("edit", this.org)
        },
        copy() {
            this.$bvModal.hide("modal-organisation-detail")
            this.$emit("copy", this.row)
        },
        baseline() {
            this.$bvModal.hide("modal-organisation-detail")
            this.$emit("baseline", this.org)
        },
        copyUuid() {
            const done = () => {
                this.copied = true
                setTimeout(() => { this.copied = false }, 1500)
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(this.org.uuid).then(done).catch(() => {})
            }
        },
    },
}
</script>

<style scoped>
.detail-title {
    margin-right: 0.5rem;
    overflow-wrap: anywhere;
}

.kind-badge {
    display: inline-block;
    padding: 0 0.45em;
    border-radius: 0.2rem;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.6;
    vertical-align: middle;
}

.kind-local {
    background: #e7f0f7;
    color: #1f5a7f;
}

.kind-external {
    background: #f1f3f5;
    color: #5f6873;
}

.org-detail {
    font-size: 0.875rem;
    color: var(--var-color-yankeesblue);
}

.detail-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 1rem;
}

.action-count {
    margin-left: 0.4em;
    padding: 0 0.4em;
    border-radius: 0.6em;
    background: rgba(0, 0, 0, 0.08);
    font-size: 0.85em;
    font-variant-numeric: tabular-nums;
}

.detail-actions ::v-deep .misp-links {
    padding: 0.25rem 0.5rem;
    color: #6c757d;
}

.detail-section + .detail-section {
    margin-top: 1rem;
    padding-top: 0.85rem;
    border-top: 1px solid var(--health-rule);
}

.attention {
    padding: 0.55rem 0.75rem !important;
    border: 0 !important;
    border-left: 3px solid var(--health-warning) !important;
    border-radius: 0 0.25rem 0.25rem 0;
    background: var(--health-warning-tint);
}

.attention + .detail-section {
    border-top: 0;
}

.flag-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.flag {
    display: flex;
    gap: 0.45em;
    line-height: 1.45;
}

.flag + .flag {
    margin-top: 0.25rem;
}

.flag i {
    margin-top: 0.2em;
}

.flag-warning i {
    color: var(--health-warning-ink);
}

.flag-info i {
    color: var(--health-info-ink);
}

.flag-help {
    color: #5a6270;
}

.detail-grid {
    display: grid;
    grid-template-columns: max-content minmax(0, 1fr);
    gap: 0.3rem 1.25rem;
    margin: 0;
}

.detail-grid dt {
    color: #6c757d;
    font-weight: 500;
}

.detail-grid dd {
    margin: 0;
    overflow-wrap: anywhere;
}

.pre {
    white-space: pre-line;
}

.uuid-cell {
    display: flex;
    align-items: center;
    gap: 0.3rem;
}

.uuid-cell code {
    color: #3c4650;
}

.copy-button {
    padding: 0 0.3rem;
    color: #6c757d;
    font-size: 0.9em;
}

.section-title {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.45em;
    margin: 0 0 0.45rem;
    font-size: 0.95em;
    font-weight: 700;
}

.section-title i {
    color: #6c757d;
}

.section-note {
    color: #6c757d;
    font-weight: 400;
}

.plain-list {
    margin: 0;
    padding-left: 1.2rem;
}

.fleet-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.fleet-row {
    display: grid;
    grid-template-columns: 1.6em minmax(8rem, 0.8fr) minmax(0, 1.4fr);
    align-items: center;
    column-gap: 0.5em;
    padding: 0.3rem 0;
    border-top: 1px solid var(--health-rule);
}

.fleet-row:first-child {
    border-top: 0;
}

.state-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.5em;
    height: 1.5em;
    border: 2px solid #ced4da;
    border-radius: 50%;
    font-size: 0.75em;
    color: #6c757d;
}

.state-same .state-mark {
    border-color: var(--health-ok);
    color: var(--health-ok-ink);
}

.state-renamed .state-mark,
.state-other_uuid .state-mark {
    border-color: var(--health-warning);
    background: var(--health-warning-tint);
    color: var(--health-warning-ink);
}

.state-unknown .state-mark {
    border-style: dashed;
}

.fleet-server {
    font-weight: 600;
    overflow-wrap: anywhere;
}

.fleet-state {
    min-width: 0;
    overflow-wrap: anywhere;
}

.state-renamed .fleet-state,
.state-other_uuid .fleet-state {
    color: var(--health-warning-ink);
}

.state-missing .fleet-state,
.state-unknown .fleet-state {
    color: #6c757d;
}

.unknown-reason {
    display: block;
    overflow: hidden;
    color: #8a9199;
    font-size: 0.85em;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.fleet-state code {
    margin-left: 0.3em;
    color: inherit;
    font-size: 0.85em;
}

.muted {
    color: #6c757d;
}

@media (max-width: 575.98px) {
    .detail-grid {
        grid-template-columns: minmax(0, 1fr);
        gap: 0.1rem;
    }

    .detail-grid dd {
        margin-bottom: 0.4rem;
    }

    .fleet-row {
        grid-template-columns: 1.6em minmax(0, 1fr);
    }

    .fleet-state {
        grid-column: 2;
    }
}
</style>
