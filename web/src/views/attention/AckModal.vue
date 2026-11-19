<template>
    <b-modal
        id="modal-ack-issue"
        :title="title"
        ok-variant="primary"
        cancel-variant="outline-secondary"
        :ok-disabled="saving"
        :cancel-disabled="saving"
        :no-close-on-backdrop="saving"
        :no-close-on-esc="saving"
        @ok="submit"
        @hidden="reset"
        @shown="focusFirstOption"
    >
        <template v-if="single">
            <p class="mb-3">
                <strong>{{ single.title }}</strong>
                <span class="text-muted"> on {{ single.server_name }}</span>
            </p>
        </template>
        <div v-else-if="issues.length > 1" class="ack-scope mb-3">
            <p class="mb-2">
                <strong>{{ issues.length }} issues</strong>
                <span class="text-muted"> on {{ serverCount }} {{ serverCount === 1 ? "server" : "servers" }}</span>
            </p>
            <ul class="ack-types" aria-label="Issue types">
                <li v-for="type in shownTypes" :key="type.rule">
                    <span class="ack-type-label">{{ type.label }}</span>
                    <span class="ack-type-count">{{ type.count }}</span>
                </li>
                <li v-if="otherTypes.count > 0" class="ack-types-more">
                    <span class="ack-type-label">{{ otherTypes.types }} other {{ otherTypes.types === 1 ? "type" : "types" }}</span>
                    <span class="ack-type-count">{{ otherTypes.count }}</span>
                </li>
            </ul>
        </div>
        <template v-if="issues.length > 0">
            <b-form-group label-class="font-weight-bold" class="mb-3">
                <template #label>{{ single ? "Hide it" : "Hide them" }}</template>
                <b-form-radio-group
                    v-model="duration"
                    :options="durations"
                    stacked
                    name="ack-duration"
                    :disabled="saving"
                ></b-form-radio-group>
                <small class="form-text text-muted">
                    {{ single ? "It shows again sooner if it clears and then comes back." : "Each one shows again sooner if it clears and then comes back." }}
                </small>
            </b-form-group>
            <b-form-group label="Note" label-for="ack-note" label-class="font-weight-bold" class="mb-0"
                :description="single ? 'Optional. For example, why this is expected.' : 'Optional, the same for all of them. For example, why this is expected.'">
                <b-form-textarea
                    id="ack-note"
                    v-model="note"
                    rows="2"
                    maxlength="500"
                    :disabled="saving"
                ></b-form-textarea>
            </b-form-group>
        </template>
        <template #modal-ok>
            <b-spinner v-if="saving" small class="mr-1" label="Saving"></b-spinner>
            {{ okTitle }}
        </template>
    </b-modal>
</template>

<script>
import { RULE_LABELS } from "./healthLabels"

const HOUR = 3600
// Issue types listed by name in the modal; the rest are summed up on one line
const SHOWN_TYPES = 3

export default {
    name: "AckModal",
    props: {
        // The issues to acknowledge: one, or many with the same duration and note
        issues: { type: Array, default: () => [] },
    },
    data() {
        return {
            duration: 24 * HOUR,
            note: "",
            saving: false,
            durations: [
                { value: HOUR, text: "For 1 hour" },
                { value: 24 * HOUR, text: "For 1 day" },
                { value: 7 * 24 * HOUR, text: "For 1 week" },
                { value: 0, text: "Until it clears" },
            ],
        }
    },
    computed: {
        single() {
            return this.issues.length === 1 ? this.issues[0] : null
        },
        title() {
            return this.issues.length > 1 ? `Acknowledge ${this.issues.length} issues` : "Acknowledge issue"
        },
        okTitle() {
            return this.issues.length > 1 ? `Acknowledge ${this.issues.length}` : "Acknowledge"
        },
        serverCount() {
            return new Set(this.issues.map(issue => issue.server_id)).size
        },
        // Issue types, the most frequent first
        types() {
            const types = {}
            this.issues.forEach((issue) => {
                if (types[issue.rule] === undefined) {
                    types[issue.rule] = { rule: issue.rule, label: RULE_LABELS[issue.rule] || issue.title, count: 0 }
                }
                types[issue.rule].count += 1
            })
            return Object.values(types).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
        },
        shownTypes() {
            // Listing a fourth type takes no more room than summing it up
            return this.types.length <= SHOWN_TYPES + 1 ? this.types : this.types.slice(0, SHOWN_TYPES)
        },
        otherTypes() {
            const others = this.types.slice(this.shownTypes.length)
            return { types: others.length, count: others.reduce((total, type) => total + type.count, 0) }
        },
    },
    methods: {
        focusFirstOption() {
            const checked = document.querySelector("#modal-ack-issue input[name='ack-duration']:checked")
            if (checked) {
                checked.focus()
            }
        },
        reset() {
            this.duration = 24 * HOUR
            this.note = ""
            this.saving = false
        },
        durationText() {
            const option = this.durations.find(item => item.value === this.duration)
            return this.duration > 0 ? `Hidden ${option.text.toLowerCase()}.` : "Hidden until they clear."
        },
        submit(event) {
            event.preventDefault()
            if (this.issues.length === 0 || this.saving) {
                return
            }
            this.saving = true
            const fields = { note: this.note.trim() }
            if (this.duration > 0) {
                fields.until = Math.floor(Date.now() / 1000) + this.duration
            }
            const request = this.single ? this.acknowledgeOne(fields) : this.acknowledgeMany(fields)
            request
                .then(() => {
                    this.$emit("acknowledged")
                    this.$bvModal.hide("modal-ack-issue")
                })
                .catch((error) => {
                    this.$bvToast.toast(error, {
                        title: this.single ? "Could not acknowledge the issue" : "Could not acknowledge the issues",
                        variant: "danger",
                    })
                })
                .finally(() => {
                    this.saving = false
                })
        },
        acknowledgeOne(fields) {
            const issue = this.single
            return this.$store.dispatch("health/acknowledge", Object.assign({ issue_id: issue.id }, fields))
                .then(() => {
                    this.$bvToast.toast(`${issue.title} on ${issue.server_name}`, {
                        title: "Issue acknowledged",
                        variant: "success",
                    })
                })
        },
        acknowledgeMany(fields) {
            const payload = Object.assign({ issue_ids: this.issues.map(issue => issue.id) }, fields)
            return this.$store.dispatch("health/acknowledgeMany", payload)
                .then(({ acknowledged, skipped }) => {
                    const count = acknowledged.length
                    if (count === 0) {
                        this.$bvToast.toast("They all cleared in the meantime.", {
                            title: "No issue to acknowledge",
                            variant: "warning",
                        })
                        return
                    }
                    const cleared = skipped.length > 0
                        ? ` ${skipped.length} ${skipped.length === 1 ? "other one" : "others"} cleared in the meantime.`
                        : ""
                    this.$bvToast.toast(`${this.durationText()}${cleared}`, {
                        title: `${count} ${count === 1 ? "issue" : "issues"} acknowledged`,
                        variant: "success",
                    })
                })
        },
    },
}
</script>

<style scoped>
.ack-types {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid var(--health-rule);
    border-radius: 6px;
    font-size: 0.875rem;
}

.ack-types li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.35rem 0.75rem;
}

.ack-types li + li {
    border-top: 1px solid var(--health-rule);
}

.ack-type-label {
    color: var(--var-color-yankeesblue);
    overflow-wrap: anywhere;
}

.ack-type-count {
    color: #5a6270;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.ack-types-more .ack-type-label {
    color: #5a6270;
}
</style>
