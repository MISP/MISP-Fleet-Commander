<template>
    <b-modal
        id="modal-sharing-group-detail"
        size="lg"
        hide-footer
        scrollable
        :title="group ? group.name : 'Sharing group'"
        @show="loadUsage"
    >
        <template v-if="group" #modal-title>
            <span class="detail-title">{{ group.name }}</span>
            <span v-if="!group.active" class="title-badge badge-inactive">Inactive</span>
            <span v-if="group.roaming" class="title-badge badge-roaming">Roaming</span>
        </template>
        <div v-if="group" class="ra-detail">
            <div class="detail-actions">
                <b-button
                    size="sm"
                    variant="outline-primary"
                    :disabled="!group.editable"
                    :title="group.editable ? '' : 'MISP does not let the API user of this server change it'"
                    @click="act('edit', group)"
                >
                    <i class="fas fa-pen mr-1" aria-hidden="true"></i>Edit
                </b-button>
                <b-button
                    v-if="hasFleet"
                    size="sm"
                    variant="outline-primary"
                    :disabled="!row.standing || copyTargets === 0"
                    :title="copyTitle"
                    @click="act('copy', row)"
                >
                    <i class="fas fa-clone mr-1" aria-hidden="true"></i>Create or complete on other servers…<span v-if="row.standing && copyTargets > 0" class="action-count">{{ copyTargets }}</span>
                </b-button>
                <b-button size="sm" variant="outline-primary" title="Check that every server of the fleet has it, with at least these members" @click="act('baseline', group)">
                    <i class="fas fa-ruler-combined mr-1" aria-hidden="true"></i>Add to baseline…
                </b-button>
                <b-button
                    v-if="group.deletable"
                    size="sm"
                    variant="outline-danger"
                    :disabled="usage.events > 0"
                    :title="usage.events > 0 ? 'Events still use it: MISP refuses to delete it' : ''"
                    @click="act('delete', group)"
                >
                    <i class="fas fa-trash-alt mr-1" aria-hidden="true"></i>Delete…
                </b-button>
                <b-dropdown size="sm" variant="link" right toggle-class="misp-links" no-caret>
                    <template #button-content>
                        <i class="fas fa-external-link-alt" aria-hidden="true"></i><span class="sr-only">Open in MISP</span>
                    </template>
                    <b-dropdown-item :href="`${server.url}/sharing_groups/view/${group.id}`" target="_blank" rel="noopener">View in MISP</b-dropdown-item>
                    <b-dropdown-item v-if="group.editable" :href="`${server.url}/sharing_groups/edit/${group.id}`" target="_blank" rel="noopener">Edit in MISP</b-dropdown-item>
                </b-dropdown>
            </div>

            <section v-if="row.flags.length > 0" :class="['detail-section', 'attention', { 'attention-info': row.flags.every(flag => flag.tone === 'info') }]" aria-label="Needs attention">
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
                        <code>{{ group.uuid }}</code>
                        <button type="button" class="btn btn-link copy-button" :title="copied ? 'Copied' : 'Copy the UUID'" @click="copyUuid">
                            <i :class="['fas', copied ? 'fa-check' : 'fa-copy']" aria-hidden="true"></i>
                            <span class="sr-only">{{ copied ? "Copied" : "Copy the UUID" }}</span>
                        </button>
                    </dd>
                    <dt>Status</dt>
                    <dd>
                        <template v-if="group.active">Active</template>
                        <template v-else>Inactive <span class="muted">— cannot be chosen for new events or attributes; what is already shared with it still syncs</span></template>
                    </dd>
                    <dt>Used by</dt>
                    <dd>
                        <span v-if="usage.loading" class="muted"><i class="fas fa-circle-notch fa-spin" aria-hidden="true"></i> Counting…</span>
                        <span v-else-if="usage.error" class="muted" :title="usage.error">Could not count the events</span>
                        <span v-else-if="usage.events === null" class="muted">MISP did not say</span>
                        <template v-else>{{ usage.events }} event{{ usage.events === 1 ? "" : "s" }}<span class="muted"> shared with it</span></template>
                    </dd>
                    <template v-if="group.releasability">
                        <dt>Releasable to</dt>
                        <dd class="pre">{{ group.releasability }}</dd>
                    </template>
                    <template v-if="group.description">
                        <dt>Description</dt>
                        <dd class="pre">{{ group.description }}</dd>
                    </template>
                    <dt>Creator</dt>
                    <dd>{{ group.creator ? group.creator.name : "—" }}</dd>
                    <dt>Origin</dt>
                    <dd>{{ group.local ? "Created on this server" : "Received by sync, or created through the API" }}</dd>
                </dl>
            </section>

            <section class="detail-section">
                <h6 class="section-title">
                    <i class="fas fa-building" aria-hidden="true"></i> Members
                    <span class="section-note">{{ group.members.length }}<template v-if="extendCount > 0">, {{ extendCount }} may extend it</template></span>
                </h6>
                <p v-if="group.members.length === 0" class="muted">No organisation is a member: only the servers below with “all organisations” share it.</p>
                <ul v-else class="member-list">
                    <li v-for="member in group.members" :key="member.uuid" class="member-row">
                        <span class="member-name">{{ member.name }}</span>
                        <span v-if="member.extend" class="extend-badge" title="Its users with the sharing group permission may change the group">may extend</span>
                        <button type="button" class="btn btn-link member-link" :title="`Show ${member.name} in the Organisations tab`" @click="$emit('show-organisation', member)">
                            <i class="fas fa-arrow-right" aria-hidden="true"></i><span class="sr-only">Show {{ member.name }} in the Organisations tab</span>
                        </button>
                    </li>
                </ul>
            </section>

            <section class="detail-section">
                <h6 class="section-title"><i class="fas fa-server" aria-hidden="true"></i> Servers</h6>
                <p v-if="group.roaming" class="servers-note">
                    Roaming: its events go to any sync server whose organisation is a member, whatever the list below.
                </p>
                <p v-else-if="group.servers.length === 0" class="muted">No server: its events are pushed to sync servers whose organisation is a member.</p>
                <ul v-if="group.servers.length > 0" :class="['server-list', { faded: group.roaming }]">
                    <li v-for="item in group.servers" :key="item.server_id" class="server-row">
                        <span class="member-name">{{ item.name }}</span>
                        <span class="server-scope">{{ item.all_orgs ? "all its organisations" : "members only" }}</span>
                    </li>
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
                            {{ states[entry.state].label }}<template v-if="entry.details.length > 0">: {{ entry.details.join("; ") }}</template>
                            <code v-if="entry.state === 'other_uuid'" :title="entry.detail">{{ entry.detail }}</code>
                            <span v-else-if="entry.state === 'unknown'" class="unknown-reason" :title="entry.detail">{{ entry.detail }}</span>
                        </span>
                    </li>
                </ul>
            </section>
        </div>
    </b-modal>
</template>

<script>
import api from "@/api/sharingGroups"
import { extendCount, FLEET_STATES } from "@/helpers/sharingGroups"

export default {
    name: "SharingGroupDetailModal",
    props: {
        server: {
            type: Object,
            required: true,
        },
        // A row of the sharing group table: {group, standing, servers, extend, flags}
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
                other_uuid: " — for MISP they are two groups: events shared with one are not shared with the other. Keep one of them on every server.",
                differs: " — its events reach different organisations depending on the server they are read on. “Create or complete on other servers” adds the members a server lacks.",
                duplicate: " — probably one group created more than once, or copied under a new name because its name was taken (MISP adds “_4821”). Events shared with one are not shared with the others.",
                no_members: " — only site administrators and the organisations that own its events see them.",
                creator_not_member: " — it can still view and edit the group, but not the events others share with it.",
                inactive_syncs: " — it can no longer be chosen for new data, but what is already shared with it is still pushed to sync servers.",
            },
            usage: { uuid: null, loading: false, events: null, error: null },
        }
    },
    computed: {
        group() {
            return this.row ? this.row.group : null
        },
        extendCount() {
            return this.group ? extendCount(this.group) : 0
        },
        copyTargets() {
            return this.row && this.row.standing ? this.row.standing.copyIds.length : 0
        },
        copyTitle() {
            if (!this.row || !this.row.standing) {
                return "Comparing with the other servers…"
            }
            return this.copyTargets === 0
                ? "Every server of the fleet has it with these members, or one with the same name"
                : "Create it with the same UUID where it is missing, add the members it lacks elsewhere"
        },
    },
    watch: {
        "row.group.uuid"(uuid) {
            this.copied = false
            if (uuid && uuid !== this.usage.uuid) {
                this.loadUsage()
            }
        },
    },
    methods: {
        loadUsage() {
            const group = this.group
            if (!group) {
                return
            }
            this.usage = { uuid: group.uuid, loading: true, events: null, error: null }
            api.usage(this.server.id, group.id)
                .then((data) => {
                    if (this.usage.uuid === group.uuid) {
                        this.usage = { uuid: group.uuid, loading: false, events: data.events, error: null }
                    }
                })
                .catch((error) => {
                    if (this.usage.uuid === group.uuid) {
                        this.usage = { uuid: group.uuid, loading: false, events: null, error: error.message }
                    }
                })
        },
        act(action, value) {
            this.$bvModal.hide("modal-sharing-group-detail")
            this.$emit(action, value)
        },
        copyUuid() {
            const done = () => {
                this.copied = true
                setTimeout(() => { this.copied = false }, 1500)
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(this.group.uuid).then(done).catch(() => {})
            }
        },
    },
}
</script>

<style scoped src="../remoteAdminDetail.css"></style>

<style scoped>
.detail-title {
    margin-right: 0.5rem;
    overflow-wrap: anywhere;
}

.title-badge {
    display: inline-block;
    margin-right: 0.3rem;
    padding: 0 0.45em;
    border-radius: 0.2rem;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.6;
    vertical-align: middle;
}

.badge-inactive {
    background: #fdf3dc;
    color: #7a5600;
}

.badge-roaming {
    background: #e7f0f7;
    color: #1f5a7f;
}

.member-list,
.server-list {
    margin: 0;
    padding: 0;
    list-style: none;
    columns: 2 16rem;
    column-gap: 1.5rem;
}

.member-row,
.server-row {
    display: flex;
    align-items: center;
    gap: 0.45em;
    padding: 0.2rem 0;
    break-inside: avoid;
}

.member-name {
    min-width: 0;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.extend-badge {
    padding: 0 0.4em;
    border-radius: 0.2rem;
    background: #efeaf7;
    color: #553d82;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
    cursor: help;
}

.member-link {
    padding: 0 0.3rem;
    color: #9aa1a7;
    font-size: 0.8em;
    opacity: 0;
}

.member-row:hover .member-link,
.member-link:focus {
    color: var(--var-color-lapislazuli);
    opacity: 1;
}

@media (hover: none) {
    .member-link {
        opacity: 1;
    }
}

.server-scope {
    color: #6c757d;
    font-size: 0.82rem;
}

.servers-note {
    margin-bottom: 0.4rem;
    color: #3c4650;
}

.faded {
    opacity: 0.6;
}

.attention {
    padding: 0.55rem 0.75rem !important;
    border: 0 !important;
    border-left: 3px solid var(--health-warning) !important;
    border-radius: 0 0.25rem 0.25rem 0;
    background: var(--health-warning-tint);
}

/* Only notes, no warning */
.attention-info {
    border-left-color: var(--health-info) !important;
    background: var(--health-info-tint);
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
</style>
